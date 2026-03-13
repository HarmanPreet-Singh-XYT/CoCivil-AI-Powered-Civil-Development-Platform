from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Main app DB (existing) ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://cocivil:cocivil@localhost:5432/cocivil"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://cocivil:cocivil@localhost:5432/cocivil"

    # ── Users / billing DB (separate physical database) ────────────────────
    # Same database, two drivers:
    #   USERS_DATABASE_URL      → asyncpg  → used by FastAPI async request handlers
    #   USERS_DATABASE_URL_SYNC → psycopg2 → used by Celery background workers
    USERS_DATABASE_URL: str = "postgresql+asyncpg://cocivil:cocivil@localhost:5432/cocivil_users"
    USERS_DATABASE_URL_SYNC: str = "postgresql+psycopg2://cocivil:cocivil@localhost:5432/cocivil_users"

    REDIS_URL: str = "redis://localhost:6379/0"

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "cocivil-docs"

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    API_V1_PREFIX: str = "/api/v1"

    AI_PROVIDER: str = "claude"
    AI_API_KEY: str = ""
    AI_MODEL: str = ""

    GOOGLE_PLACES_API_KEY: str = ""

    # ── Stripe ─────────────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()