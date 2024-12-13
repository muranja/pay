import requests
import base64
from datetime import datetime
import json

class MpesaAPI:
    def __init__(self):
        self.auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate"
        self.stk_push_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        
        # Your credentials from the Safaricom developer portal
        self.consumer_key = "Y5AfZkyPL6qK6xLQ5ozzMVuAZ23Rp2WuXreK"
        self.consumer_secret = "3wPUmNkAzDhLBgAWwLxlKjzqVVUcvsk9dNgF5urf"
        self.business_shortcode = "174379"  # Your Paybill/Till number
        self.passkey = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
        
        # Create base64 encoded auth string
        auth_string = f"{self.consumer_key}:{self.consumer_secret}"
        self.auth_header = {
            "Authorization": f"Basic {base64.b64encode(auth_string.encode()).decode()}"
        }
        self.access_token = self._get_access_token()

    def _get_access_token(self):
        """Get OAuth access token from Safaricom"""
        try:
            response = requests.get(
                self.auth_url,
                headers=self.auth_header,
                params={"grant_type": "client_credentials"}
            )
            response.raise_for_status()
            return response.json()["access_token"]
        except requests.exceptions.RequestException as e:
            print(f"Error getting access token: {e}")
            return None

    def initiate_stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate STK push payment"""
        if not self.access_token:
            return {"error": "Could not get access token"}

        # Format phone number (remove leading 0 or +254)
        phone_number = phone_number.replace("+", "").replace(" ", "")
        if phone_number.startswith("0"):
            phone_number = "254" + phone_number[1:]
        elif not phone_number.startswith("254"):
            phone_number = "254" + phone_number

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{self.business_shortcode}{self.passkey}{timestamp}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.business_shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": "https://mydomain.com/mpesa-callback",  # Update with your callback URL
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }

        try:
            response = requests.post(
                self.stk_push_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error initiating STK push: {e}")
            return {"error": str(e)}

    def verify_transaction(self, checkout_request_id):
        """Verify transaction status using the query API"""
        if not self.access_token:
            return {"error": "Could not get access token"}

        query_url = "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query"
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{self.business_shortcode}{self.passkey}{timestamp}".encode()
        ).decode()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }

        try:
            response = requests.post(
                query_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error verifying transaction: {e}")
            return {"error": str(e)}
