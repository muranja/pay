from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re
from datetime import datetime

# Create instance directory if it doesn't exist
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "wifi_payment.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add this context processor to make now() available in all templates
@app.context_processor
def utility_processor():
    return {'now': datetime.utcnow}

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active_until = db.Column(db.DateTime, nullable=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    mpesa_receipt_number = db.Column(db.String(50), nullable=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False)
    plan = db.relationship('Plan', backref='transactions')

class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration_hours = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        try:
            phone = request.form.get('phone')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if not phone or not password or not confirm_password:
                flash('All fields are required', 'danger')
                return render_template('register.html')
            
            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return render_template('register.html')
                
            is_valid_phone, formatted_phone = validate_phone(phone)
            if not is_valid_phone:
                flash('Invalid phone number format. Please use format: 07XXXXXXXX', 'danger')
                return render_template('register.html')
            
            # Check if user already exists
            existing_user = User.query.filter_by(phone=formatted_phone).first()
            if existing_user:
                flash('An account with this phone number already exists', 'danger')
                return render_template('register.html')
            
            # Validate password
            is_valid_pass, pass_error = validate_password(password)
            if not is_valid_pass:
                flash(pass_error, 'danger')
                return render_template('register.html')
                
            # Create new user
            user = User(phone=formatted_phone)
            user.set_password(password)
            db.session.add(user)
            
            try:
                db.session.commit()
                # Log in the user after successful registration
                login_user(user)
                flash('Account created successfully!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Database error: {str(e)}")
                flash('Error creating account. Please try again.', 'danger')
                return render_template('register.html')
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Registration error: {str(e)}")
            flash('An error occurred while processing your request. Please try again.', 'danger')
            return render_template('register.html')
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        try:
            phone = request.form.get('phone')
            password = request.form.get('password')

            if not phone or not password:
                flash('Both phone number and password are required', 'danger')
                return render_template('login.html')
                
            is_valid_phone, formatted_phone = validate_phone(phone)
            if not is_valid_phone:
                flash('Invalid phone number format. Please use format: 07XXXXXXXX', 'danger')
                return render_template('login.html')
            
            # Find user
            user = User.query.filter_by(phone=formatted_phone).first()
            
            if not user or not user.check_password(password):
                flash('Invalid phone number or password', 'danger')
                return render_template('login.html')
            
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard')
            return redirect(next_page)
            
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred while processing your request. Please try again.', 'danger')
            return render_template('login.html')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        plans = Plan.query.all()
        transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.created_at.desc()).all()
        return render_template('dashboard.html', plans=plans, transactions=transactions)
    except Exception as e:
        app.logger.error(f"Error in dashboard route: {str(e)}")
        flash('An error occurred while loading the dashboard', 'danger')
        return redirect(url_for('index'))

@app.route('/check-payment-status/<int:transaction_id>')
@login_required
def check_payment_status(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({
        'status': transaction.status.lower(),
        'receipt_number': transaction.mpesa_receipt_number
    })

@app.route('/initiate_payment', methods=['POST'])
@login_required
def initiate_payment():
    plan_id = request.form.get('plan_id')
    if not plan_id:
        flash('Invalid plan selected', 'danger')
        return redirect(url_for('dashboard'))
    
    plan = Plan.query.get_or_404(plan_id)
    
    # Create a new transaction
    transaction = Transaction(
        user_id=current_user.id,
        amount=plan.price,
        transaction_type='MPESA',
        status='PENDING',
        plan_id=plan.id
    )
    db.session.add(transaction)
    db.session.commit()
    
    flash('Payment initiated. Please complete the M-PESA payment.', 'info')
    return redirect(url_for('dashboard'))

def validate_phone(phone):
    # Remove any spaces or special characters
    phone = re.sub(r'[^0-9]', '', phone)
    
    # Check if it starts with 07 and has exactly 10 digits
    if re.match(r'^07\d{8}$', phone):
        return True, phone
    return False, None

def validate_password(password):
    if len(password) < 7:
        return False, "Password must be at least 7 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

# Initialize some default plans
with app.app_context():
    db.drop_all()
    db.create_all()
    
    # Add default plans if they don't exist
    if not Plan.query.first():
        default_plans = [
            Plan(name='1 Hour Access', duration_hours=1, price=50.0),
            Plan(name='12 Hour Access', duration_hours=12, price=200.0),
            Plan(name='24 Hour Access', duration_hours=24, price=300.0)
        ]
        for plan in default_plans:
            db.session.add(plan)
        db.session.commit()
    
    app.logger.info("Database reset and initialized successfully")

if __name__ == '__main__':
    app.run(debug=True)
