"""
Payment API routes: PayFast hosted checkout + credit management.
Flow: Frontend POSTs to /api/payment/initiate → gets PayFast form data →
browser POSTs form to PayFast → user pays → PayFast redirects to callback URL →
we add credits and redirect user back to the app.
"""
import os
from fastapi import APIRouter, HTTPException, Header, Request, Form
from fastapi.responses import RedirectResponse, PlainTextResponse

from . import database as db
from . import payfast

payment_router = APIRouter()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://tattoo-ai-flax.vercel.app")
BACKEND_URL = os.environ.get("BACKEND_URL", "https://tattoo-ai-backend.fly.dev")


@payment_router.get("/api/credits")
async def get_credits(request: Request, x_device_id: str = Header(..., alias="X-Device-ID")):
    """Return credit balance for a device."""
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
    """Create a payment session and return form data for PayFast hosted checkout."""
    basket_id = payfast.generate_basket_id()

    token = await payfast.get_access_token(basket_id)
    if not token:
        raise HTTPException(status_code=502, detail="Could not connect to payment gateway")

    await db.create_transaction(x_device_id, basket_id, payfast.TRANSACTION_AMOUNT)

    success_url = f"{BACKEND_URL}/api/payment/callback?status=success&basket_id={basket_id}&device_id={x_device_id}"
    failure_url = f"{BACKEND_URL}/api/payment/callback?status=failed&basket_id={basket_id}&device_id={x_device_id}"
    ipn_url = f"{BACKEND_URL}/api/payment/ipn"

    form_data = payfast.build_checkout_form(
        token=token,
        basket_id=basket_id,
        success_url=success_url,
        failure_url=failure_url,
        ipn_url=ipn_url,
    )

    return {
        "checkout_url": f"{payfast.PAYFAST_BASE_URL}/PostTransaction",
        "form_data": form_data,
        "basket_id": basket_id,
    }


@payment_router.get("/api/payment/callback")
async def payment_callback(
    status: str = "failed",
    basket_id: str = "",
    device_id: str = "",
):
    """PayFast redirects here after payment. Add credits and redirect user back to app."""
    if status == "success" and basket_id and device_id:
        await db.update_transaction(basket_id, basket_id, "success")
        new_credits = await db.add_credits(device_id, db.CREDITS_PER_PURCHASE)
        print(f"[Payment] Success: device={device_id}, basket={basket_id}, credits={new_credits}")
        redirect_url = f"{FRONTEND_URL}?payment=success&credits={new_credits}"
    else:
        if basket_id:
            await db.update_transaction(basket_id, basket_id, f"failed:{status}")
        print(f"[Payment] Failed: device={device_id}, basket={basket_id}, status={status}")
        redirect_url = f"{FRONTEND_URL}?payment=failed"

    return RedirectResponse(url=redirect_url, status_code=302)


@payment_router.post("/api/payment/ipn")
async def payment_ipn(
    request: Request,
    basket_id: str = Form(""),
    err_code: str = Form(""),
    err_msg: str = Form(""),
    transaction_id: str = Form(""),
    validation_hash: str = Form(""),
    order_date: str = Form(""),
):
    """PayFast IPN: verify hash, add credits if err_code=000. Must return 200 OK."""
    if not basket_id or not err_code or not validation_hash:
        print(f"[IPN] Missing params: basket_id={basket_id}, err_code={err_code}")
        return PlainTextResponse("Missing params", status_code=400)

    if not payfast.verify_ipn_hash(basket_id, err_code, validation_hash):
        print(f"[IPN] Hash mismatch for basket={basket_id}")
        return PlainTextResponse("Hash mismatch", status_code=400)

    if err_code == "000":
        device_id = await db.get_device_id_by_basket(basket_id)
        if device_id:
            await db.update_transaction(basket_id, transaction_id or basket_id, "success")
            new_credits = await db.add_credits(device_id, db.CREDITS_PER_PURCHASE)
            print(f"[IPN] Success: basket={basket_id}, device={device_id}, credits={new_credits}")
        else:
            print(f"[IPN] No device found for basket={basket_id}")
    else:
        await db.update_transaction(basket_id, transaction_id or basket_id, f"failed:{err_code}")
        print(f"[IPN] Failed: basket={basket_id}, err_code={err_code}, err_msg={err_msg}")

    return PlainTextResponse("OK", status_code=200)
