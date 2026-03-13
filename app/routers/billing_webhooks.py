"""
app/routers/billing_webhooks.py

Stripe webhook handler. Uses get_users_db() — same pattern as all other routers.

Register in main.py:
    from app.routers import billing_webhooks
    application.include_router(billing_webhooks.router, prefix=prefix, tags=["billing"])
"""

from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.config import settings
from app.database import get_users_db
from app.models.users_db import (
    Invoice,
    Organisation,
    Subscription,
    StripeWebhookEvent,
    TokenAccount,
    TokenLedger,
    User,
)

router = APIRouter(prefix="/webhooks")

HANDLED_EVENTS = {
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
}


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_users_db),
):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    # Idempotency: skip if already processed
    existing = await db.execute(
        select(StripeWebhookEvent.id).where(
            StripeWebhookEvent.stripe_event_id == event["id"]
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_processed"}

    event_type = event["type"]
    obj = event["data"]["object"]
    status = "skipped"
    error_msg = None

    if event_type in HANDLED_EVENTS:
        try:
            await _dispatch(db, event_type, obj)
            status = "processed"
        except Exception as exc:
            error_msg = str(exc)
            status = "failed"
            # Return 200 so Stripe doesn't retry infinitely — log to your monitoring
            print(f"[webhook] FAILED {event_type} {event['id']}: {exc}")

    log = StripeWebhookEvent(
        stripe_event_id=event["id"],
        event_type=event_type,
        status=status,
        error_message=error_msg,
        payload=dict(event),
    )
    db.add(log)
    # get_users_db commits on exit — no explicit commit needed here

    return {"status": status}


# ──────────────────────────────────────────────────────────────
# Event handlers
# ──────────────────────────────────────────────────────────────

async def _dispatch(db: AsyncSession, event_type: str, obj: dict) -> None:
    match event_type:
        case "customer.subscription.updated":
            await _on_subscription_updated(db, obj)
        case "customer.subscription.deleted":
            await _on_subscription_deleted(db, obj)
        case "invoice.paid":
            await _on_invoice_paid(db, obj)
        case "invoice.payment_failed":
            await _on_invoice_payment_failed(db, obj)
        case "payment_intent.succeeded":
            await _on_payment_intent_succeeded(db, obj)
        case "payment_intent.payment_failed":
            await _on_payment_intent_failed(db, obj)


async def _on_subscription_updated(db: AsyncSession, obj: dict) -> None:
    await db.execute(
        update(Subscription)
        .where(Subscription.stripe_subscription_id == obj["id"])
        .values(
            status=obj["status"],
            current_period_start=datetime.fromtimestamp(obj["current_period_start"], tz=timezone.utc),
            current_period_end=datetime.fromtimestamp(obj["current_period_end"], tz=timezone.utc),
            cancel_at_period_end=obj["cancel_at_period_end"],
            updated_at=datetime.now(timezone.utc),
        )
    )


async def _on_subscription_deleted(db: AsyncSession, obj: dict) -> None:
    await db.execute(
        update(Subscription)
        .where(Subscription.stripe_subscription_id == obj["id"])
        .values(
            status="canceled",
            canceled_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )


async def _on_invoice_paid(db: AsyncSession, obj: dict) -> None:
    metadata = obj.get("metadata", {})

    # ── Postpaid invoice ──
    if not obj.get("subscription") and metadata.get("org_id"):
        await db.execute(
            update(Invoice)
            .where(Invoice.stripe_invoice_id == obj["id"])
            .values(
                status="paid",
                amount_paid_cents=obj["amount_paid"],
                paid_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        return

    # ── Subscription invoice paid → apply rollover cap + grant new period tokens ──
    stripe_sub_id = obj.get("subscription")
    if not stripe_sub_id:
        return

    from app.services.token_service import handle_subscription_renewal
    await handle_subscription_renewal(db, stripe_sub_id)


async def _on_invoice_payment_failed(db: AsyncSession, obj: dict) -> None:
    await db.execute(
        update(Invoice)
        .where(Invoice.stripe_invoice_id == obj["id"])
        .values(status="past_due", updated_at=datetime.now(timezone.utc))
    )


async def _on_payment_intent_succeeded(db: AsyncSession, obj: dict) -> None:
    metadata = obj.get("metadata", {})
    if metadata.get("type") != "token_purchase":
        return

    # Credit tokens if not already done (handles 3DS redirect case)
    already = await db.execute(
        select(TokenLedger.id).where(
            TokenLedger.stripe_payment_intent_id == obj["id"]
        )
    )
    if already.scalar_one_or_none():
        return   # already credited synchronously in the purchase endpoint

    tokens = int(metadata.get("tokens", 0))
    if not tokens:
        return

    user_id = metadata.get("user_id")
    org_id = metadata.get("org_id")

    col = TokenAccount.org_id if org_id else TokenAccount.user_id
    val = org_id or user_id

    acct_result = await db.execute(
        select(TokenAccount).where(col == val).with_for_update()
    )
    account = acct_result.scalar_one_or_none()
    if not account:
        return

    from app.services.token_service import credit_purchased_tokens
    await credit_purchased_tokens(
        db, account, tokens,
        txn_type="purchase",
        stripe_pi_id=obj["id"],
        description="Token purchase (webhook)",
    )


async def _on_payment_intent_failed(db: AsyncSession, obj: dict) -> None:
    metadata = obj.get("metadata", {})
    if metadata.get("type") == "auto_topup":
        account_id = metadata.get("account_id")
        # TODO: surface to your monitoring / notify the user
        print(f"[webhook] Auto top-up payment failed for account {account_id}")