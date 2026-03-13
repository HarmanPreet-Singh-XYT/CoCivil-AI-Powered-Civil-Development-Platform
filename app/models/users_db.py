"""
app/models/users_db.py

SQLAlchemy ORM models for the USERS / BILLING database.

Token balance design — two separate buckets:
  subscription_balance  tokens granted by the active subscription plan,
                        refilled on every renewal, roll over up to a cap
                        (2x monthly allowance by default).
  purchased_balance     tokens bought explicitly via token packages / top-ups,
                        never expire, accumulate without limit.

Consumption order: subscription_balance is drawn down first.
When it hits zero, purchased_balance is used.
This means users always burn through their "included" tokens before
touching anything they paid extra for.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UsersBase(DeclarativeBase):
    pass


# ─────────────────────────────────────────────────────────────
# ORGANISATIONS
# ─────────────────────────────────────────────────────────────

class Organisation(UsersBase):
    __tablename__ = "organisations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    stripe_customer_id = Column(Text, unique=True)
    billing_email = Column(Text, nullable=False)
    billing_contact_name = Column(Text)

    billing_cycle_day = Column(Integer)
    billing_cycle_months = Column(Integer, default=1)
    billing_currency = Column(String(3), default="usd")

    credit_limit = Column(Numeric(12, 4))
    auto_charge_enabled = Column(Boolean, default=True)
    payment_terms_days = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    users = relationship("User", back_populates="organisation")
    subscriptions = relationship("Subscription", back_populates="organisation")
    token_account = relationship("TokenAccount", back_populates="organisation", uselist=False)
    invoices = relationship("Invoice", back_populates="organisation")
    usage_events = relationship("UsageEvent", back_populates="organisation")
    rate_cards = relationship("BillingRateCard", back_populates="organisation")


# ─────────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────────

class User(UsersBase):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="SET NULL"), nullable=True)
    email = Column(Text, unique=True, nullable=False)
    full_name = Column(Text)
    hashed_password = Column(Text)
    stripe_customer_id = Column(Text, unique=True)
    billing_type = Column(Text, nullable=False, default="subscription")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    organisation = relationship("Organisation", back_populates="users")
    subscriptions = relationship("Subscription", back_populates="user")
    token_account = relationship("TokenAccount", back_populates="user", uselist=False)
    usage_events = relationship("UsageEvent", back_populates="user")

    __table_args__ = (
        CheckConstraint(
            "billing_type IN ('subscription','token','postpaid')",
            name="ck_user_billing_type",
        ),
    )


# ─────────────────────────────────────────────────────────────
# TRACK 1 — SUBSCRIPTION PLANS
# ─────────────────────────────────────────────────────────────

class SubscriptionPlan(UsersBase):
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    stripe_product_id = Column(Text, unique=True, nullable=False)
    stripe_price_id_monthly = Column(Text)
    stripe_price_id_annual = Column(Text)
    price_monthly_cents = Column(Integer)
    price_annual_cents = Column(Integer)

    # Tokens granted at the start of each billing period
    included_tokens = Column(BigInteger, default=0)

    # Rollover cap: max subscription tokens carried into the next period.
    # Stored as a multiplier of included_tokens.
    # e.g. rollover_cap_multiplier=2 and included_tokens=100k
    #      → max 200k subscription tokens can roll over.
    # NULL means use the system default (2x).
    rollover_cap_multiplier = Column(Numeric(4, 2), default=2)

    api_rate_limit_rpm = Column(Integer, default=60)
    max_seats = Column(Integer, default=1)
    features = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(UsersBase):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"))

    stripe_subscription_id = Column(Text, unique=True, nullable=False)
    stripe_price_id = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="active")
    interval = Column(Text, nullable=False)

    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime(timezone=True))
    trial_end = Column(DateTime(timezone=True))
    stripe_latest_invoice_id = Column(Text)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    user = relationship("User", back_populates="subscriptions")
    organisation = relationship("Organisation", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")

    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND org_id IS NULL) OR (user_id IS NULL AND org_id IS NOT NULL)",
            name="ck_subscription_owner",
        ),
        CheckConstraint("interval IN ('month','year')", name="ck_subscription_interval"),
    )


# ─────────────────────────────────────────────────────────────
# TRACK 2 — TOKEN SYSTEM
# ─────────────────────────────────────────────────────────────

class TokenPackage(UsersBase):
    __tablename__ = "token_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    stripe_price_id = Column(Text, unique=True, nullable=False)
    tokens = Column(BigInteger, nullable=False)
    bonus_tokens = Column(BigInteger, default=0)
    price_cents = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)


class TokenAccount(UsersBase):
    """
    Two-bucket token balance.

    subscription_balance   — refilled each period, rolls over up to cap
    purchased_balance      — bought explicitly, never expire

    total_balance (property) = subscription_balance + purchased_balance

    Consumption order enforced in service layer:
        1. Draw from subscription_balance first
        2. Spill into purchased_balance only when subscription_balance = 0
    """
    __tablename__ = "token_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=True)

    # ── Two buckets ──────────────────────────────────────────
    subscription_balance = Column(BigInteger, nullable=False, default=0)
    # Cap applied at renewal: min(current + included, included * rollover_cap_multiplier)
    # Stored here as a snapshot from the plan at last renewal time
    subscription_rollover_cap = Column(BigInteger, nullable=False, default=0)

    purchased_balance = Column(BigInteger, nullable=False, default=0)
    # ─────────────────────────────────────────────────────────

    # Auto top-up config (only applies to purchased_balance)
    auto_topup_enabled = Column(Boolean, default=False)
    # Fires when (subscription_balance + purchased_balance) <= threshold
    auto_topup_threshold = Column(BigInteger)
    auto_topup_amount = Column(BigInteger)
    auto_topup_stripe_pm_id = Column(Text)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    user = relationship("User", back_populates="token_account")
    organisation = relationship("Organisation", back_populates="token_account")
    ledger_entries = relationship("TokenLedger", back_populates="account")

    @property
    def total_balance(self) -> int:
        return self.subscription_balance + self.purchased_balance

    __table_args__ = (
        CheckConstraint("subscription_balance >= 0", name="ck_sub_balance_non_negative"),
        CheckConstraint("purchased_balance >= 0",    name="ck_pur_balance_non_negative"),
        CheckConstraint(
            "(user_id IS NOT NULL AND org_id IS NULL) OR (user_id IS NULL AND org_id IS NOT NULL)",
            name="ck_token_account_owner",
        ),
        UniqueConstraint("user_id", name="uq_token_account_user"),
        UniqueConstraint("org_id",  name="uq_token_account_org"),
    )


class TokenLedger(UsersBase):
    """
    Full audit trail of every token movement.

    txn_type values:
        subscription_grant   — tokens granted at subscription start / renewal
        subscription_expire  — tokens removed at renewal that exceeded rollover cap
        purchase             — tokens bought via token package
        auto_topup           — tokens bought via automatic top-up
        consume_subscription — deducted from subscription_balance
        consume_purchased    — deducted from purchased_balance
        refund               — tokens returned (e.g. disputed charge)
        adjustment           — manual correction by support

    bucket values:
        subscription   — this entry touched subscription_balance
        purchased      — this entry touched purchased_balance
        mixed          — a single consume that spanned both buckets
                         (one ledger row per bucket is preferred, but mixed
                          is valid for atomic cross-bucket deductions)
    """
    __tablename__ = "token_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("token_accounts.id", ondelete="CASCADE"), nullable=False)

    txn_type = Column(Text, nullable=False)
    bucket = Column(Text, nullable=False)   # subscription | purchased | mixed

    amount = Column(BigInteger, nullable=False)   # positive = credit, negative = debit

    # Snapshots of both buckets after this transaction — makes debugging trivial
    subscription_balance_after = Column(BigInteger, nullable=False)
    purchased_balance_after = Column(BigInteger, nullable=False)

    stripe_payment_intent_id = Column(Text)
    usage_event_id = Column(UUID(as_uuid=True), ForeignKey("usage_events.id"), nullable=True)
    description = Column(Text)
    metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now)

    account = relationship("TokenAccount", back_populates="ledger_entries")

    __table_args__ = (
        CheckConstraint(
            "bucket IN ('subscription','purchased','mixed')",
            name="ck_ledger_bucket",
        ),
    )


# ─────────────────────────────────────────────────────────────
# SHARED — USAGE EVENTS
# ─────────────────────────────────────────────────────────────

class UsageEvent(UsersBase):
    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=True)

    resource_type = Column(Text, nullable=False)
    resource_id = Column(Text)
    quantity = Column(Numeric(18, 6), nullable=False)
    unit_cost = Column(Numeric(12, 8))
    total_cost = Column(Numeric(12, 4))
    currency = Column(String(3), default="usd")

    billing_type = Column(Text, nullable=False)

    # How this consumption was split across buckets
    tokens_from_subscription = Column(BigInteger)
    tokens_from_purchased = Column(BigInteger)
    token_ledger_ids = Column(ARRAY(UUID(as_uuid=True)))  # up to 2 entries (one per bucket)

    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    invoiced_at = Column(DateTime(timezone=True))

    request_id = Column(Text, unique=True)
    api_endpoint = Column(Text)
    metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now)

    user = relationship("User", back_populates="usage_events")
    organisation = relationship("Organisation", back_populates="usage_events")

    __table_args__ = (
        CheckConstraint(
            "billing_type IN ('subscription','token','postpaid')",
            name="ck_usage_billing_type",
        ),
    )


# ─────────────────────────────────────────────────────────────
# TRACK 3 — INVOICES (postpaid)
# ─────────────────────────────────────────────────────────────

class Invoice(UsersBase):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False)

    stripe_invoice_id = Column(Text, unique=True)
    stripe_payment_intent_id = Column(Text)

    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True))

    subtotal_cents = Column(BigInteger, nullable=False, default=0)
    tax_cents = Column(BigInteger, nullable=False, default=0)
    total_cents = Column(BigInteger, nullable=False, default=0)
    amount_paid_cents = Column(BigInteger, nullable=False, default=0)
    currency = Column(String(3), default="usd")

    status = Column(Text, nullable=False, default="draft")
    collection_method = Column(Text, nullable=False, default="auto_charge")

    hosted_invoice_url = Column(Text)
    invoice_pdf_url = Column(Text)
    memo = Column(Text)
    footer = Column(Text)

    generated_at = Column(DateTime(timezone=True))
    finalized_at = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True))
    voided_at = Column(DateTime(timezone=True))
    next_billing_date = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    organisation = relationship("Organisation", back_populates="invoices")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLineItem(UsersBase):
    __tablename__ = "invoice_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)

    description = Column(Text, nullable=False)
    resource_type = Column(Text)
    quantity = Column(Numeric(18, 6), nullable=False)
    unit_cost_cents = Column(BigInteger, nullable=False)
    total_cents = Column(BigInteger, nullable=False)
    usage_event_ids = Column(ARRAY(UUID(as_uuid=True)))
    metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now)

    invoice = relationship("Invoice", back_populates="line_items")


# ─────────────────────────────────────────────────────────────
# STRIPE WEBHOOK LOG
# ─────────────────────────────────────────────────────────────

class StripeWebhookEvent(UsersBase):
    __tablename__ = "stripe_webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stripe_event_id = Column(Text, unique=True, nullable=False)
    event_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="processed")
    error_message = Column(Text)
    payload = Column(JSONB, nullable=False)
    processed_at = Column(DateTime(timezone=True), default=_now)


# ─────────────────────────────────────────────────────────────
# BILLING RATE CARDS
# ─────────────────────────────────────────────────────────────

class BillingRateCard(UsersBase):
    __tablename__ = "billing_rate_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)

    resource_type = Column(Text, nullable=False)
    unit_cost = Column(Numeric(12, 8), nullable=False)
    currency = Column(String(3), default="usd")

    tier_threshold = Column(BigInteger)
    tier_unit_cost = Column(Numeric(12, 8))

    effective_from = Column(DateTime(timezone=True), nullable=False, default=_now)
    effective_to = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=_now)

    organisation = relationship("Organisation", back_populates="rate_cards")

    __table_args__ = (
        UniqueConstraint("org_id", "resource_type", "effective_from",
                         name="uq_rate_card_org_resource_from"),
    )