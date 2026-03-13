"""
app/services/token_service.py

All token operations: granting, consuming, renewing, topping up.

The two-bucket rules enforced here:
  1. Consume subscription_balance first, spill into purchased_balance
  2. On subscription renewal: cap subscription_balance rollover, then add new allocation
  3. Auto top-up threshold checks total_balance (both buckets combined)
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import stripe
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.users_db import (
    Subscription,
    SubscriptionPlan,
    TokenAccount,
    TokenLedger,
    TokenPackage,
    UsageEvent,
)

stripe.api_key = settings.STRIPE_SECRET_KEY


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

def _ledger_entry(
    account: TokenAccount,
    txn_type: str,
    bucket: str,
    amount: int,
    description: str,
    stripe_pi_id: Optional[str] = None,
    usage_event_id: Optional[UUID] = None,
) -> TokenLedger:
    """Build a TokenLedger row using current account bucket snapshots."""
    return TokenLedger(
        account_id=account.id,
        txn_type=txn_type,
        bucket=bucket,
        amount=amount,
        subscription_balance_after=account.subscription_balance,
        purchased_balance_after=account.purchased_balance,
        stripe_payment_intent_id=stripe_pi_id,
        usage_event_id=usage_event_id,
        description=description,
    )


# ─────────────────────────────────────────────────────────────
# GRANT — called when a subscription is created or renewed
# ─────────────────────────────────────────────────────────────

async def grant_subscription_tokens(
    db: AsyncSession,
    account: TokenAccount,
    plan: SubscriptionPlan,
    is_renewal: bool = False,
) -> TokenLedger:
    """
    Credit subscription_balance with the plan's included_tokens.

    On renewal (is_renewal=True):
        1. Apply rollover cap first: clamp current subscription_balance to
           included_tokens * rollover_cap_multiplier
        2. Then add the new period's allocation on top

    On first grant (is_renewal=False):
        Just credit the full allocation directly.

    purchased_balance is never touched here.
    """
    included = plan.included_tokens
    cap_multiplier = float(plan.rollover_cap_multiplier or 2)
    rollover_cap = int(included * cap_multiplier)

    expired_tokens = 0

    if is_renewal and account.subscription_balance > rollover_cap:
        # Tokens above the cap are silently expired before the new grant
        expired_tokens = account.subscription_balance - rollover_cap
        account.subscription_balance = rollover_cap

        expire_entry = _ledger_entry(
            account,
            txn_type="subscription_expire",
            bucket="subscription",
            amount=-expired_tokens,
            description=(
                f"Rollover cap applied: {expired_tokens:,} tokens expired "
                f"(cap={rollover_cap:,} = {included:,} × {cap_multiplier})"
            ),
        )
        db.add(expire_entry)

    # Credit new period's tokens
    account.subscription_balance += included
    account.subscription_rollover_cap = rollover_cap
    account.updated_at = datetime.now(timezone.utc)

    grant_entry = _ledger_entry(
        account,
        txn_type="subscription_grant",
        bucket="subscription",
        amount=included,
        description=(
            f"{'Renewal' if is_renewal else 'Initial'} grant: "
            f"{included:,} tokens from plan '{plan.name}'"
            + (f" ({expired_tokens:,} expired at rollover)" if expired_tokens else "")
        ),
    )
    db.add(grant_entry)
    return grant_entry


# ─────────────────────────────────────────────────────────────
# CONSUME — called on every API usage event
# ─────────────────────────────────────────────────────────────

async def consume_tokens(
    db: AsyncSession,
    account: TokenAccount,
    quantity: int,
    resource_type: str,
    request_id: str,
    user_id: Optional[UUID] = None,
    org_id: Optional[UUID] = None,
    unit_cost=None,
    api_endpoint: Optional[str] = None,
) -> UsageEvent:
    """
    Deduct `quantity` tokens using subscription-first ordering.

    If subscription_balance covers the full amount → one ledger entry.
    If subscription_balance runs out mid-way → two ledger entries
        (one for the subscription portion, one for the purchased portion).

    Raises ValueError if total_balance < quantity.
    """
    total = account.subscription_balance + account.purchased_balance
    if total < quantity:
        raise ValueError(
            f"Insufficient tokens: total={total:,}, required={quantity:,} "
            f"(subscription={account.subscription_balance:,}, "
            f"purchased={account.purchased_balance:,})"
        )

    remaining = quantity
    from_subscription = 0
    from_purchased = 0
    ledger_ids = []

    # ── Draw from subscription bucket first ──
    if account.subscription_balance > 0 and remaining > 0:
        draw = min(account.subscription_balance, remaining)
        account.subscription_balance -= draw
        remaining -= draw
        from_subscription = draw

        entry = _ledger_entry(
            account,
            txn_type="consume_subscription",
            bucket="subscription",
            amount=-draw,
            description=f"Used {draw:,} subscription tokens for {resource_type}",
        )
        db.add(entry)
        await db.flush()
        ledger_ids.append(entry.id)

    # ── Spill into purchased bucket if subscription was exhausted ──
    if remaining > 0:
        draw = remaining
        account.purchased_balance -= draw
        from_purchased = draw

        entry = _ledger_entry(
            account,
            txn_type="consume_purchased",
            bucket="purchased",
            amount=-draw,
            description=f"Used {draw:,} purchased tokens for {resource_type}",
        )
        db.add(entry)
        await db.flush()
        ledger_ids.append(entry.id)

    account.updated_at = datetime.now(timezone.utc)

    from decimal import Decimal
    total_cost = (Decimal(str(unit_cost)) * quantity) if unit_cost else None

    event = UsageEvent(
        user_id=user_id,
        org_id=org_id,
        resource_type=resource_type,
        quantity=quantity,
        unit_cost=unit_cost,
        total_cost=total_cost,
        billing_type="token",
        tokens_from_subscription=from_subscription,
        tokens_from_purchased=from_purchased,
        token_ledger_ids=ledger_ids,
        request_id=request_id,
        api_endpoint=api_endpoint,
    )
    db.add(event)
    await db.flush()

    account.updated_at = datetime.now(timezone.utc)

    # ── Auto top-up check (fires when total drops below threshold) ──
    new_total = account.subscription_balance + account.purchased_balance
    if (
        account.auto_topup_enabled
        and account.auto_topup_threshold is not None
        and new_total <= account.auto_topup_threshold
    ):
        asyncio.create_task(_run_auto_topup(account))

    return event


# ─────────────────────────────────────────────────────────────
# PURCHASE — explicit token top-up buy
# ─────────────────────────────────────────────────────────────

async def credit_purchased_tokens(
    db: AsyncSession,
    account: TokenAccount,
    tokens: int,
    txn_type: str,                    # "purchase" | "auto_topup" | "refund" | "adjustment"
    stripe_pi_id: Optional[str] = None,
    description: str = "",
) -> TokenLedger:
    """
    Add tokens to purchased_balance only.
    Purchased tokens never expire and are not subject to rollover caps.
    """
    account.purchased_balance += tokens
    account.updated_at = datetime.now(timezone.utc)

    entry = _ledger_entry(
        account,
        txn_type=txn_type,
        bucket="purchased",
        amount=tokens,
        description=description or f"Credited {tokens:,} purchased tokens",
        stripe_pi_id=stripe_pi_id,
    )
    db.add(entry)
    return entry


# ─────────────────────────────────────────────────────────────
# AUTO TOP-UP (background task)
# ─────────────────────────────────────────────────────────────

async def _run_auto_topup(account: TokenAccount) -> None:
    """
    Fired as asyncio.create_task() — runs in a fresh DB session
    so the parent request session is already committed before this starts.
    """
    from app.database import users_async_session_factory

    if not account.auto_topup_stripe_pm_id or not account.auto_topup_amount:
        return

    try:
        async with users_async_session_factory() as session:
            # Match to the closest package, or use the raw amount
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
                off_session=True,
                metadata={
                    "type": "auto_topup",
                    "account_id": str(account.id),
                    "tokens": str(pkg.tokens + pkg.bonus_tokens),
                },
            )

            if intent["status"] == "succeeded":
                fresh = await session.get(TokenAccount, account.id, with_for_update=True)
                if fresh:
                    total_tokens = pkg.tokens + pkg.bonus_tokens
                    await credit_purchased_tokens(
                        session, fresh, total_tokens,
                        txn_type="auto_topup",
                        stripe_pi_id=intent["id"],
                        description=f"Auto top-up: {total_tokens:,} tokens",
                    )
                await session.commit()

    except stripe.error.CardError as exc:
        # Card declined — notify user, optionally disable auto top-up after N failures
        print(f"[auto_topup] card declined for account {account.id}: {exc}")
    except Exception as exc:
        print(f"[auto_topup] failed for account {account.id}: {exc}")


# ─────────────────────────────────────────────────────────────
# RENEWAL HANDLER — called from the webhook on invoice.paid
# ─────────────────────────────────────────────────────────────

async def handle_subscription_renewal(
    db: AsyncSession,
    stripe_subscription_id: str,
) -> None:
    """
    Called by the invoice.paid webhook when a subscription invoice is paid.
    Applies rollover cap and grants the new period's token allocation.
    """
    sub_result = await db.execute(
        select(Subscription)
        .where(Subscription.stripe_subscription_id == stripe_subscription_id)
    )
    sub = sub_result.scalar_one_or_none()
    if not sub or not sub.plan_id:
        return

    plan_result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == sub.plan_id)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan or plan.included_tokens <= 0:
        return

    col = TokenAccount.org_id if sub.org_id else TokenAccount.user_id
    val = sub.org_id or sub.user_id

    acct_result = await db.execute(
        select(TokenAccount).where(col == val).with_for_update()
    )
    account = acct_result.scalar_one_or_none()
    if not account:
        return

    # is_renewal=True → applies rollover cap before granting
    await grant_subscription_tokens(db, account, plan, is_renewal=True)