"""
Stripe Checkout integration.
Creates hosted checkout sessions — user pays on Stripe's secure page,
then Stripe redirects back to our callback URL.
"""
import os
import stripe

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "price_1TYBfY1omP2DLjOumzU8UF6P")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(
    device_id: str,
    success_url: str,
    cancel_url: str,
) -> stripe.checkout.Session:
    """Create a Stripe Checkout Session for a one-time $1 purchase."""
    return stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"device_id": device_id},
    )


def retrieve_session(session_id: str) -> stripe.checkout.Session:
    """Retrieve and verify a Checkout Session by ID."""
    return stripe.checkout.Session.retrieve(session_id)


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Validate and construct a webhook Event from raw payload + Stripe-Signature."""
    return stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
