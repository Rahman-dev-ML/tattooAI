"""
Payment API routes: Stripe Checkout + credit management.
Flow: Frontend POSTs to /api/payment/initiate → gets Stripe checkout URL →
browser redirects to Stripe → user pays → Stripe redirects to our callback URL →
we verify with Stripe API, add credits, and redirect back to the app.
"""
import os
import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import RedirectResponse

from . import database as db
from . import stripe_payment as sp

payment_router = APIRouter()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://tattoo-ai-flax.vercel.app")
BACKEND_URL = os.environ.get("BACKEND_URL", "https://tattoo-ai-backend.fly.dev")


@payment_router.get("/api/credits")
async def get_credits(request: Request, x_device_id: str = Header(..., alias="X-Device-ID")):
    """Return credit balance for a device."""
    if os.environ.get("SKIP_CREDITS", "0").strip() == "1":
        return {"credits": 999}
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.headers.get("X-Real-IP", "")
        or (request.client.host if request.client else "")
    )
    credits = await db.get_or_create_device(x_device_id, client_ip)
    return {"credits": credits}


@payment_router.post("/api/payment/initiate")
async def initiate_payment(
    request: Request,
    x_device_id: str = Header(..., alias="X-Device-ID"),
):
    """Create a Stripe Checkout Session and return the hosted checkout URL."""
    success_url = (
        f"{BACKEND_URL}/api/payment/callback"
        f"?session_id={{CHECKOUT_SESSION_ID}}&device_id={x_device_id}"
    )
    cancel_url = f"{FRONTEND_URL}?payment=cancelled"

    try:
        session = sp.create_checkout_session(
            device_id=x_device_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except stripe.StripeError as e:
        print(f"[Stripe] Session creation failed: {e}")
        raise HTTPException(status_code=502, detail="Could not connect to payment gateway")

    await db.create_transaction(x_device_id, session.id, 100)  # $1.00 in cents

    print(f"[Stripe] Session created: {session.id} for device {x_device_id}")
    return {"checkout_url": session.url, "session_id": session.id}


@payment_router.get("/api/payment/callback")
async def payment_callback(session_id: str = "", device_id: str = ""):
    """
    Stripe redirects here after payment. We verify the session with Stripe
    (not just trusting the URL params), then add credits and redirect to the app.
    """
    if not session_id or not device_id:
        return RedirectResponse(url=f"{FRONTEND_URL}?payment=failed", status_code=302)

    try:
        session = sp.retrieve_session(session_id)
    except stripe.StripeError as e:
        print(f"[Stripe] Could not retrieve session {session_id}: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}?payment=failed", status_code=302)

    if session.payment_status == "paid":
        # Double-check device_id matches metadata stored at session creation
        # session.metadata is a StripeObject — access via ["key"], not .get()
        try:
            meta_device = session.metadata["device_id"] if session.metadata else ""
        except (KeyError, TypeError):
            meta_device = ""
        if meta_device and meta_device != device_id:
            print(f"[Stripe] Device mismatch: meta={meta_device} vs param={device_id}")
            return RedirectResponse(url=f"{FRONTEND_URL}?payment=failed", status_code=302)

        # Guard against double-crediting (callback + webhook both fire)
        already_fulfilled = await db.is_transaction_fulfilled(session_id)
        if not already_fulfilled:
            await db.update_transaction(session_id, session.payment_intent or session_id, "success")
            new_credits = await db.add_credits(device_id, db.CREDITS_PER_PURCHASE)
            print(f"[Stripe] Callback credited: device={device_id}, session={session_id}, credits={new_credits}")
        else:
            credits_row = await db.get_or_create_device(device_id)
            new_credits = credits_row
            print(f"[Stripe] Callback skipped (already fulfilled): session={session_id}")

        return RedirectResponse(
            url=f"{FRONTEND_URL}?payment=success&credits={new_credits}",
            status_code=302,
        )

    print(f"[Stripe] Callback: unpaid session {session_id}, status={session.payment_status}")
    await db.update_transaction(session_id, session_id, f"failed:{session.payment_status}")
    return RedirectResponse(url=f"{FRONTEND_URL}?payment=failed", status_code=302)


@payment_router.post("/api/payment/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe webhook endpoint. More reliable than the callback redirect because
    Stripe retries on failure. Set this URL in your Stripe Dashboard under
    Webhooks: https://<your-backend>/api/payment/webhook
    Listen for: checkout.session.completed
    """
    if not sp.STRIPE_WEBHOOK_SECRET:
        # Webhook secret not configured — skip verification (not recommended for production)
        print("[Stripe] Webhook secret not set, skipping signature verification")
        return {"status": "ok"}

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = sp.construct_webhook_event(payload, sig_header)
    except stripe.SignatureVerificationError:
        print("[Stripe] Webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        print(f"[Stripe] Webhook error: {e}")
        raise HTTPException(status_code=400, detail="Webhook error")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payment_status = session["payment_status"] if "payment_status" in session else ""
        if payment_status == "paid":
            session_id = session["id"]
            try:
                raw_meta = session["metadata"]
                device_id = raw_meta["device_id"] if raw_meta else ""
            except (KeyError, TypeError):
                device_id = ""

            if device_id:
                already_fulfilled = await db.is_transaction_fulfilled(session_id)
                if not already_fulfilled:
                    pi = session["payment_intent"] if "payment_intent" in session else session_id
                    await db.update_transaction(session_id, pi or session_id, "success")
                    new_credits = await db.add_credits(device_id, db.CREDITS_PER_PURCHASE)
                    print(f"[Stripe] Webhook credited: device={device_id}, session={session_id}, credits={new_credits}")
                else:
                    print(f"[Stripe] Webhook skipped (already fulfilled): session={session_id}")
            else:
                print(f"[Stripe] Webhook: no device_id in metadata for session {session_id}")

    return {"status": "ok"}
