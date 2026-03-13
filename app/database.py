from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# ── Main app DB ─────────────────────────────────────────────────────────────
# Same physical database, two drivers:
#   async_engine  → asyncpg   → FastAPI request handlers (non-blocking)
#   sync_engine   → psycopg2  → Celery workers (long jobs, sync library compat)

async_engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
async_session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False, pool_pre_ping=True)
sync_session_factory = sessionmaker(sync_engine, class_=Session, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_db() -> Session:
    return sync_session_factory()


# ── Users / billing DB ──────────────────────────────────────────────────────
# Separate physical database (cocivil_users). Same driver split as above:
#   users_async_engine  → asyncpg   → FastAPI billing/auth request handlers
#   users_sync_engine   → psycopg2  → Celery workers that need to touch user data
#                                      (e.g. scheduled invoice generation,
#                                       subscription sync tasks)

users_async_engine = create_async_engine(
    settings.USERS_DATABASE_URL, echo=False, pool_pre_ping=True
)
users_async_session_factory = async_sessionmaker(
    users_async_engine, class_=AsyncSession, expire_on_commit=False
)

users_sync_engine = create_engine(
    settings.USERS_DATABASE_URL_SYNC, echo=False, pool_pre_ping=True
)
users_sync_session_factory = sessionmaker(
    users_sync_engine, class_=Session, expire_on_commit=False
)


async def get_users_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — asyncpg, non-blocking.
    Use this in all billing and auth route handlers.

    Example:
        @router.post("/billing/subscriptions")
        async def create_sub(db: AsyncSession = Depends(get_users_db)):
            ...
    """
    async with users_async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_users_sync_db() -> Session:
    """
    Synchronous session — psycopg2, for Celery workers.
    Use this in tasks that touch user/billing data (invoice cron, sub sync, etc.).

    Example:
        @celery_app.task
        def generate_monthly_invoices():
            db = get_users_sync_db()
            try:
                orgs = db.query(Organisation).filter(...).all()
                ...
            finally:
                db.close()
    """
    return users_sync_session_factory()


# ── Redis (shared across both DBs) ──────────────────────────────────────────
def get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)