"""
app/routers/billing.py

Billing router — plugs into your existing FastAPI app exactly like every
other router in main.py.  All DB work goes through get_users_db().

Register in main.py:
    from app.routers import billing as billing
    application.include_router(billing.router, prefix=prefix, tags=["billing"])
"""

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

import stripe
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_users_db
from app.models.users_db import (
    BillingRateCard,
    Invoice,
    InvoiceLineItem,
    Organisation,
    StripeWebhookEvent,
    Subscription,
    SubscriptionPlan,
    TokenAccount,
    TokenLedger,
    TokenPackage,
    UsageEvent,
    User,
)

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/billing")


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

async def _get_token_account(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    org_id: Optional[UUID] = None,
) -> TokenAccount:
    col = TokenAccount.org_id if org_id else TokenAccount.user_id
    val = org_id or user_id
    result = await db.execute(select(TokenAccount).where(col == val).with_for_update())
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Token account not found")
    return account


async def _credit_tokens(
    db: AsyncSession,
    account: TokenAccount,
    tokens: int,
    txn_type: str,
    stripe_pi_id: Optional[str] = None,
    description: str = "",
) -> None:
    """Add tokens to an account and write a ledger entry. Call inside a transaction."""
    account.balance += tokens
    account.updated_at = datetime.now(timezone.utc)

    entry = TokenLedger(
        account_id=account.id,
        txn_type=txn_type,
        amount=tokens,
        balance_after=account.balance,
        stripe_payment_intent_id=stripe_pi_id,
        description=description,
    )
    db.add(entry)


# ──────────────────────────────────────────────────────────────
# TRACK 1 — SUBSCRIPTIONS
# ──────────────────────────────────────────────────────────────

class CreateSubscriptionRequest(BaseModel):
    user_id: UUID
    stripe_price_id: str
    trial_days: int = 0
    org_id: Optional[UUID] = None


@router.post("/subscriptions")
async def create_subscription(
    body: CreateSubscriptionRequest,
    db: AsyncSession = Depends(get_users_db),
):
    # Resolve stripe_customer_id from whichever owner was passed
    if body.org_id:
        result = await db.execute(select(Organisation).where(Organisation.id == body.org_id))
        owner = result.scalar_one_or_none()
    else:
        result = await db.execute(select(User).where(User.id == body.user_id))
        owner = result.scalar_one_or_none()

    if not owner or not owner.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Stripe customer not set up for this account")

    params: dict = {
        "customer": owner.stripe_customer_id,
        "items": [{"price": body.stripe_price_id}],
        "payment_behavior": "default_incomplete",
        "payment_settings": {"save_default_payment_method": "on_subscription"},
        "expand": ["latest_invoice.payment_intent"],
    }
    if body.trial_days:
        params["trial_period_days"] = body.trial_days

    stripe_sub = stripe.Subscription.create(**params)

    # Resolve plan by stripe_price_id
    plan_result = await db.execute(
        select(SubscriptionPlan).where(
            (SubscriptionPlan.stripe_price_id_monthly == body.stripe_price_id)
            | (SubscriptionPlan.stripe_price_id_annual == body.stripe_price_id)
        )
    )
    plan = plan_result.scalar_one_or_none()

    sub = Subscription(
        user_id=body.user_id if not body.org_id else None,
        org_id=body.org_id,
        plan_id=plan.id if plan else None,
        stripe_subscription_id=stripe_sub["id"],
        stripe_price_id=body.stripe_price_id,
        status=stripe_sub["status"],
        interval=stripe_sub["items"]["data"][0]["plan"]["interval"],
        current_period_start=datetime.fromtimestamp(
            stripe_sub["current_period_start"], tz=timezone.utc
        ),
        current_period_end=datetime.fromtimestamp(
            stripe_sub["current_period_end"], tz=timezone.utc
        ),
    )
    db.add(sub)
    await db.flush()

    return {
        "subscription_id": stripe_sub["id"],
        "status": stripe_sub["status"],
        "client_secret": stripe_sub["latest_invoice"]["payment_intent"]["client_secret"],
    }


@router.delete("/subscriptions/{stripe_subscription_id}")
async def cancel_subscription(
    stripe_subscription_id: str,
    at_period_end: bool = True,
    db: AsyncSession = Depends(get_users_db),
):
    if at_period_end:
        stripe.Subscription.modify(stripe_subscription_id, cancel_at_period_end=True)
        await db.execute(
            update(Subscription)
            .where(Subscription.stripe_subscription_id == stripe_subscription_id)
            .values(cancel_at_period_end=True, updated_at=datetime.now(timezone.utc))
        )
    else:
        stripe.Subscription.cancel(stripe_subscription_id)
        await db.execute(
            update(Subscription)
            .where(Subscription.stripe_subscription_id == stripe_subscription_id)
            .values(
                status="canceled",
                canceled_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
    return {"status": "ok"}


@router.post("/portal")
async def create_billing_portal(
    customer_id: str = Body(..., embed=True),
    return_url: str = Body(..., embed=True),
):
    session = stripe.billing_portal.Session.create(
        customer=customer_id, return_url=return_url
    )
    return {"url": session.url}


# ──────────────────────────────────────────────────────────────
# TRACK 2 — TOKEN SYSTEM
# ──────────────────────────────────────────────────────────────

class PurchaseTokensRequest(BaseModel):
    user_id: UUID
    package_id: UUID
    stripe_payment_method_id: Optional[str] = None
    org_id: Optional[UUID] = None


class ConsumeTokensRequest(BaseModel):
    user_id: UUID
    quantity: int
    resource_type: str
    request_id: str
    unit_cost: Optional[Decimal] = None
    org_id: Optional[UUID] = None


class TopupConfigRequest(BaseModel):
    enabled: bool
    threshold: Optional[int] = None
    amount: Optional[int] = None
    stripe_payment_method_id: Optional[str] = None


@router.post("/tokens/purchase")
async def purchase_tokens(
    body: PurchaseTokensRequest,
    db: AsyncSession = Depends(get_users_db),
):
    pkg_result = await db.execute(
        select(TokenPackage).where(TokenPackage.id == body.package_id, TokenPackage.is_active == True)
    )
    pkg = pkg_result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Token package not found")

    if body.org_id:
        result = await db.execute(select(Organisation).where(Organisation.id == body.org_id))
        owner = result.scalar_one_or_none()
    else:
        result = await db.execute(select(User).where(User.id == body.user_id))
        owner = result.scalar_one_or_none()

    if not owner or not owner.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Stripe customer not configured")

    total_tokens = pkg.tokens + pkg.bonus_tokens
    intent_params: dict = {
        "amount": pkg.price_cents,
        "currency": "usd",
        "customer": owner.stripe_customer_id,
        "metadata": {
            "type": "token_purchase",
            "package_id": str(body.package_id),
            "tokens": str(total_tokens),
            "user_id": str(body.user_id),
            "org_id": str(body.org_id) if body.org_id else "",
        },
    }
    if body.stripe_payment_method_id:
        intent_params["payment_method"] = body.stripe_payment_method_id
        intent_params["confirm"] = True

    intent = stripe.PaymentIntent.create(**intent_params)

    # Credit immediately on synchronous confirm; otherwise wait for webhook
    if intent["status"] == "succeeded":
        account = await _get_token_account(db, body.user_id, body.org_id)
        await _credit_tokens(
            db, account, total_tokens,
            txn_type="purchase",
            stripe_pi_id=intent["id"],
            description=f"Purchased {pkg.name}",
        )

    return {
        "payment_intent_id": intent["id"],
        "status": intent["status"],
        "client_secret": intent.get("client_secret"),
        "tokens": total_tokens,
    }


@router.post("/tokens/consume")
async def consume_tokens(
    body: ConsumeTokensRequest,
    db: AsyncSession = Depends(get_users_db),
):
    account = await _get_token_account(db, body.user_id, body.org_id)

    if account.balance < body.quantity:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient tokens (balance={account.balance}, required={body.quantity})",
        )

    account.balance -= body.quantity
    account.updated_at = datetime.now(timezone.utc)

    entry = TokenLedger(
        account_id=account.id,
        txn_type="consume",
        amount=-body.quantity,
        balance_after=account.balance,
        description=f"Used {body.quantity} tokens for {body.resource_type}",
    )
    db.add(entry)
    await db.flush()

    total_cost = (Decimal(str(body.unit_cost)) * body.quantity) if body.unit_cost else None
    event = UsageEvent(
        user_id=body.user_id,
        org_id=body.org_id,
        resource_type=body.resource_type,
        quantity=body.quantity,
        unit_cost=body.unit_cost,
        total_cost=total_cost,
        billing_type="token",
        tokens_deducted=body.quantity,
        token_ledger_id=entry.id,
        request_id=body.request_id,
    )
    db.add(event)
    await db.flush()

    # Trigger auto top-up check outside the current transaction
    if (
        account.auto_topup_enabled
        and account.auto_topup_threshold is not None
        and account.balance <= account.auto_topup_threshold
    ):
        asyncio.create_task(_run_auto_topup(account))

    return {"usage_event_id": str(event.id), "balance": account.balance}


@router.get("/tokens/balance")
async def get_token_balance(
    user_id: Optional[UUID] = None,
    org_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_users_db),
):
    col = TokenAccount.org_id if org_id else TokenAccount.user_id
    result = await db.execute(select(TokenAccount.balance).where(col == (org_id or user_id)))
    balance = result.scalar_one_or_none()
    return {"balance": balance or 0}


@router.put("/tokens/topup-config")
async def set_topup_config(
    body: TopupConfigRequest,
    user_id: Optional[UUID] = None,
    org_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_users_db),
):
    col = TokenAccount.org_id if org_id else TokenAccount.user_id
    await db.execute(
        update(TokenAccount)
        .where(col == (org_id or user_id))
        .values(
            auto_topup_enabled=body.enabled,
            auto_topup_threshold=body.threshold,
            auto_topup_amount=body.amount,
            auto_topup_stripe_pm_id=body.stripe_payment_method_id,
            updated_at=datetime.now(timezone.utc),
        )
    )
    return {"status": "updated"}


async def _run_auto_topup(account: TokenAccount) -> None:
    """
    Background task: charge the saved PaymentMethod and credit tokens.
    Runs a fresh DB session since the parent session may already be committed.
    """
    from app.database import users_async_session_factory

    if not account.auto_topup_stripe_pm_id or not account.auto_topup_amount:
        return
    try:
        async with users_async_session_factory() as session:
            pkg_result = await session.execute(
                select(TokenPackage).where(
                    TokenPackage.tokens == account.auto_topup_amount,
                    TokenPackage.is_active == True,
                )
            )
            pkg = pkg_result.scalar_one_or_none()
            if not pkg:
                return

            intent = stripe.PaymentIntent.create(
                amount=pkg.price_cents,
                currency="usd",
                payment_method=account.auto_topup_stripe_pm_id,
                confirm=True,
                metadata={"type": "auto_topup", "account_id": str(account.id)},
            )
            if intent["status"] == "succeeded":
                # Re-fetch account in this session with lock
                fresh = await session.get(TokenAccount, account.id, with_for_update=True)
                if fresh:
                    await _credit_tokens(
                        session, fresh,
                        pkg.tokens + pkg.bonus_tokens,
                        txn_type="auto_topup",
                        stripe_pi_id=intent["id"],
                        description="Auto top-up",
                    )
                await session.commit()
    except Exception as exc:
        print(f"[auto_topup] failed for account {account.id}: {exc}")


# ──────────────────────────────────────────────────────────────
# TRACK 3 — POSTPAID / CUSTOM BILLING
# ──────────────────────────────────────────────────────────────

class RecordUsageRequest(BaseModel):
    org_id: UUID
    resource_type: str
    quantity: Decimal
    request_id: str
    user_id: Optional[UUID] = None
    api_endpoint: Optional[str] = None


class GenerateInvoiceRequest(BaseModel):
    org_id: UUID
    period_start: datetime
    period_end: datetime
    memo: Optional[str] = None


@router.post("/usage")
async def record_postpaid_usage(
    body: RecordUsageRequest,
    db: AsyncSession = Depends(get_users_db),
):
    # Look up the org's custom rate for this resource type
    rate_result = await db.execute(
        select(BillingRateCard)
        .where(
            BillingRateCard.org_id == body.org_id,
            BillingRateCard.resource_type == body.resource_type,
            BillingRateCard.effective_from <= datetime.now(timezone.utc),
            (BillingRateCard.effective_to == None) | (BillingRateCard.effective_to > datetime.now(timezone.utc)),
        )
        .order_by(BillingRateCard.effective_from.desc())
        .limit(1)
    )
    rate = rate_result.scalar_one_or_none()

    unit_cost = Decimal("0")
    if rate:
        if rate.tier_threshold and body.quantity > rate.tier_threshold:
            unit_cost = Decimal(str(rate.tier_unit_cost))
        else:
            unit_cost = Decimal(str(rate.unit_cost))

    event = UsageEvent(
        user_id=body.user_id,
        org_id=body.org_id,
        resource_type=body.resource_type,
        quantity=body.quantity,
        unit_cost=unit_cost,
        total_cost=body.quantity * unit_cost,
        billing_type="postpaid",
        request_id=body.request_id,
        api_endpoint=body.api_endpoint,
    )
    db.add(event)
    await db.flush()
    return {"usage_event_id": str(event.id)}


@router.post("/invoices/generate")
async def generate_invoice(
    body: GenerateInvoiceRequest,
    db: AsyncSession = Depends(get_users_db),
):
    org_result = await db.execute(select(Organisation).where(Organisation.id == body.org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    # Aggregate uninvoiced usage by resource type
    from sqlalchemy import func
    agg_result = await db.execute(
        select(
            UsageEvent.resource_type,
            func.sum(UsageEvent.quantity).label("total_qty"),
            func.sum(UsageEvent.total_cost).label("total_cost"),
        )
        .where(
            UsageEvent.org_id == body.org_id,
            UsageEvent.billing_type == "postpaid",
            UsageEvent.invoiced_at == None,
            UsageEvent.created_at.between(body.period_start, body.period_end),
        )
        .group_by(UsageEvent.resource_type)
    )
    rows = agg_result.all()
    if not rows:
        return {"message": "No uninvoiced usage in this period"}

    stripe_invoice = stripe.Invoice.create(
        customer=org.stripe_customer_id,
        collection_method="charge_automatically" if org.auto_charge_enabled else "send_invoice",
        days_until_due=org.payment_terms_days if not org.auto_charge_enabled else None,
        description=body.memo or f"Usage {body.period_start.date()} – {body.period_end.date()}",
        metadata={"org_id": str(org.id)},
        currency=org.billing_currency,
    )

    subtotal_cents = 0
    line_items_data = []

    for row in rows:
        amount_cents = int(Decimal(str(row.total_cost)) * 100)
        subtotal_cents += amount_cents
        stripe.InvoiceItem.create(
            customer=org.stripe_customer_id,
            invoice=stripe_invoice["id"],
            amount=amount_cents,
            currency=org.billing_currency,
            description=f"{row.resource_type} — {row.total_qty} units",
        )
        line_items_data.append((row, amount_cents))

    stripe_invoice = stripe.Invoice.finalize_invoice(stripe_invoice["id"])

    due_date = (
        datetime.fromtimestamp(stripe_invoice["due_date"], tz=timezone.utc)
        if stripe_invoice.get("due_date")
        else None
    )

    invoice = Invoice(
        org_id=org.id,
        stripe_invoice_id=stripe_invoice["id"],
        period_start=body.period_start,
        period_end=body.period_end,
        due_date=due_date,
        subtotal_cents=subtotal_cents,
        total_cents=int(stripe_invoice["amount_due"]),
        currency=org.billing_currency,
        status=stripe_invoice["status"],
        collection_method="auto_charge" if org.auto_charge_enabled else "send_email",
        hosted_invoice_url=stripe_invoice.get("hosted_invoice_url"),
        invoice_pdf_url=stripe_invoice.get("invoice_pdf"),
        memo=body.memo,
        generated_at=datetime.now(timezone.utc),
        finalized_at=datetime.now(timezone.utc),
    )
    db.add(invoice)
    await db.flush()

    for row, amount_cents in line_items_data:
        li = InvoiceLineItem(
            invoice_id=invoice.id,
            description=f"{row.resource_type} — {row.total_qty} units",
            resource_type=row.resource_type,
            quantity=row.total_qty,
            unit_cost_cents=int(amount_cents / float(row.total_qty)) if row.total_qty else 0,
            total_cents=amount_cents,
        )
        db.add(li)

    # Mark usage events as invoiced
    await db.execute(
        update(UsageEvent)
        .where(
            UsageEvent.org_id == body.org_id,
            UsageEvent.billing_type == "postpaid",
            UsageEvent.invoiced_at == None,
            UsageEvent.created_at.between(body.period_start, body.period_end),
        )
        .values(invoice_id=invoice.id, invoiced_at=datetime.now(timezone.utc))
    )

    return {
        "invoice_id": str(invoice.id),
        "stripe_invoice_id": stripe_invoice["id"],
        "status": stripe_invoice["status"],
        "total_cents": int(stripe_invoice["amount_due"]),
        "hosted_invoice_url": stripe_invoice.get("hosted_invoice_url"),
    }


@router.get("/invoices/{org_id}")
async def list_invoices(org_id: UUID, db: AsyncSession = Depends(get_users_db)):
    result = await db.execute(
        select(Invoice)
        .where(Invoice.org_id == org_id)
        .order_by(Invoice.created_at.desc())
        .limit(50)
    )
    invoices = result.scalars().all()
    return [
        {
            "id": str(i.id),
            "stripe_invoice_id": i.stripe_invoice_id,
            "period_start": i.period_start,
            "period_end": i.period_end,
            "total_cents": i.total_cents,
            "status": i.status,
            "hosted_invoice_url": i.hosted_invoice_url,
            "paid_at": i.paid_at,
            "due_date": i.due_date,
        }
        for i in invoices
    ]