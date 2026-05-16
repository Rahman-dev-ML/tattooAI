"""
GoPayFast Hosted Checkout integration.
Uses redirect-based flow: user pays on PayFast's secure page, then returns to our app.
"""
import hashlib
import os
import time
import uuid
from typing import Optional
import httpx

PAYFAST_MERCHANT_ID = os.environ.get("PAYFAST_MERCHANT_ID", "")
PAYFAST_SECURED_KEY = os.environ.get("PAYFAST_SECURED_KEY", "")
PAYFAST_BASE_URL = os.environ.get("PAYFAST_BASE_URL", "https://ipg1.apps.net.pk/Ecommerce/api/Transaction")

TRANSACTION_AMOUNT = 280  # PKR ≈ $1 USD


def generate_basket_id() -> str:
    return f"TATTOO-{uuid.uuid4().hex[:12].upper()}"


async def get_access_token(basket_id: str) -> Optional[str]:
    if not PAYFAST_MERCHANT_ID or not PAYFAST_SECURED_KEY:
        print("[PayFast] Missing merchant credentials")
        return None

    async with httpx.AsyncClient(timeout=30.0) as client:
        standard_data = {
            "merchant_id": PAYFAST_MERCHANT_ID,
            "secured_key": PAYFAST_SECURED_KEY,
            "grant_type": "client_credentials",
            "customer_ip": "127.0.0.1",
        }
        print(f"[PayFast] Trying /token at {PAYFAST_BASE_URL}/token")
        resp = await client.post(
            f"{PAYFAST_BASE_URL}/token",
            data=standard_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        result = resp.json()
        token = result.get("token") or result.get("ACCESS_TOKEN")
        if token:
            print(f"[PayFast] Access token obtained for basket {basket_id}")
            return token

        print(f"[PayFast] /token failed ({result}), trying GetAccessToken")
        resp2 = await client.post(
            f"{PAYFAST_BASE_URL}/GetAccessToken",
            data={
                "MERCHANT_ID": PAYFAST_MERCHANT_ID,
                "SECURED_KEY": PAYFAST_SECURED_KEY,
                "TXNAMT": str(TRANSACTION_AMOUNT),
                "BASKET_ID": basket_id,
                "CURRENCY_CODE": "PKR",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        result2 = resp2.json()
        token2 = result2.get("ACCESS_TOKEN")
        if token2:
            print(f"[PayFast] Access token obtained via GetAccessToken for basket {basket_id}")
            return token2
        print(f"[PayFast] Token error: {result2}")
        return None


def build_checkout_form(
    token: str,
    basket_id: str,
    success_url: str,
    failure_url: str,
    ipn_url: str,
) -> dict:
    return {
        "MERCHANT_ID": PAYFAST_MERCHANT_ID,
        "TOKEN": token,
        "TXNAMT": str(TRANSACTION_AMOUNT),
        "BASKET_ID": basket_id,
        "ORDER_DATE": time.strftime("%Y-%m-%d %H:%M:%S"),
        "TXNDESC": "TattooAI - 5 Design Concepts",
        "SUCCESS_URL": success_url,
        "FAILURE_URL": failure_url,
        "CHECKOUT_URL": ipn_url,
        "CURRENCY_CODE": "PKR",
        "VERSION": "MERCHANT-CART-0.1",
        "PROCCODE": "00",
        "PAYMENT_METHOD": "CC",
        "SIGNATURE": f"TATTOO-{uuid.uuid4().hex[:8]}",
    }


def verify_ipn_hash(basket_id: str, err_code: str, received_hash: str) -> bool:
    """Verify PayFast IPN validation_hash. Format: basket_id|secured_key|merchant_id|err_code"""
    data = f"{basket_id}|{PAYFAST_SECURED_KEY}|{PAYFAST_MERCHANT_ID}|{err_code}"
    expected = hashlib.sha256(data.encode()).hexdigest()
    return expected == received_hash
