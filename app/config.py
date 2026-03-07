from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://arterial:arterial@localhost:5432/arterial"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://arterial:arterial@localhost:5432/arterial"
    REDIS_URL: str = "redis://localhost:6379/0"

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "arterial-docs"

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    API_V1_PREFIX: str = "/api/v1"

    AI_PROVIDER: str = "claude"
    AI_API_KEY: str = ""
    AI_MODEL: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
