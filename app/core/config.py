from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DB
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/mindup"

    # Auth — Clerk JWT (Authorization: Bearer <token>)
    auth_mode: str = "prod"  # dev | prod
    clerk_jwks_url: str  # https://<frontend-api>/.well-known/jwks.json
    clerk_issuer: str    # https://<frontend-api>

    # Webhooks (used by /api/webhooks/clerk)
    clerk_webhook_secret: str | None = None

    # Storage (for PDF resources)
    # mock: returns fake signed URLs
    # supabase: generates signed URLs from Supabase Storage private bucket
    storage_mode: str = "mock"  # mock | supabase
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "mindup-resources"
    supabase_signed_url_expires_in: int = 3600  # seconds

    # Admin API key (used by admin team member)
    admin_api_key: str = "change-me"

    # CORS (keep open for local testing)
    cors_allow_origins: str = "*"


settings = Settings()
