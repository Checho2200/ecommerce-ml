import mercadopago
from fastapi import HTTPException
from pydantic_settings import BaseSettings
import os
from typing import List, Dict, Any

# We use a dummy test token if not provided. In production, this should come from .env
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "***TOKEN-RETIRADO***")

class PaymentService:
    def __init__(self):
        self.sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)

    def create_preference(self, order_id: str, items: List[Dict[str, Any]], payer_email: str) -> str:
        """
        Creates a MercadoPago preference and returns the init_point (URL to redirect the user).
        """
        # Convert our items format to MP format
        mp_items = []
        for item in items:
            mp_items.append({
                "title": item.get("title", "Producto"),
                "quantity": int(item.get("quantity", 1)),
                "unit_price": float(item.get("unit_price", 0.0)),
                "currency_id": "PEN"  # Assuming Peruvian Soles
            })

        # FRONTEND_URL is used for the return URLs. Should be dynamic, but hardcoded for now for local dev
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
        
        # Webhook URL for IPN notifications (must be publicly accessible in prod, like ngrok for local)
        # We will point it to our backend endpoint
        BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
        notification_url = f"{BACKEND_URL}/api/v1/orders/webhook/mercadopago"

        preference_data = {
            "items": mp_items,
            "payer": {
                "email": payer_email
            },
            "back_urls": {
                "success": f"{FRONTEND_URL}/checkout/success?order_id={order_id}",
                "failure": f"{FRONTEND_URL}/checkout/failure?order_id={order_id}",
                "pending": f"{FRONTEND_URL}/checkout/failure?order_id={order_id}"
            },
            "auto_return": "approved",
            "external_reference": str(order_id),
            # Important: Set the webhook URL
            "notification_url": notification_url,
            # Force HTTPS for notification url? MP requires it, but in test mode it might accept http if using some tunneling, 
            # though actually MP strictly requires HTTPS. If testing locally, we'll need ngrok.
        }

        try:
            preference_response = self.sdk.preference().create(preference_data)
            preference = preference_response["response"]
            
            # The init_point is the URL where the user should be redirected to pay
            init_point = preference.get("init_point")
            
            # Use sandbox_init_point if in test mode (depends on the token used, but usually init_point works fine for both)
            sandbox_init_point = preference.get("sandbox_init_point")
            
            return sandbox_init_point if "TEST" in MERCADOPAGO_ACCESS_TOKEN else init_point
            
        except Exception as e:
            print(f"Error creating MP preference: {str(e)}")
            # Fallback or raise error
            raise HTTPException(status_code=500, detail="Error creating payment preference")

    def verify_payment(self, payment_id: str) -> dict:
        """
        Verify a payment status in MercadoPago API.
        Used by the webhook.
        """
        try:
            payment_info = self.sdk.payment().get(payment_id)
            return payment_info["response"]
        except Exception as e:
            print(f"Error verifying payment {payment_id}: {str(e)}")
            raise

payment_service = PaymentService()
