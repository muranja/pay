# WiFi Payment System

A Flask-based web application for managing WiFi access through a payment system.

## Features

- User authentication
- Multiple WiFi access plans
- Secure payment processing with Stripe
- User dashboard
- Automatic access management

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a .env file with the following variables:
```
SECRET_KEY=your-secret-key
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key
```

4. Initialize the database:
```bash
flask shell
>>> from app import db
>>> db.create_all()
>>> exit()
```

5. Run the application:
```bash
python app.py
```

## Configuration

1. Update the Stripe publishable key in `templates/dashboard.html`
2. Configure WiFi plans in `app.py`
3. Set up your WiFi access point to integrate with the system

## Security Considerations

- Use proper password hashing in production
- Keep your .env file secure
- Regular security updates
- Monitor system access and usage

## License

MIT License
