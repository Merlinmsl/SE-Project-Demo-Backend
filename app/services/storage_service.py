from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional
import httpx

from app.core.config import settings


class StorageService(Protocol):
    """Abstraction over resource storage (Supabase Storage private bucket)."""

    def create_signed_view_url(self, storage_path: str) -> str: ...


@dataclass
class MockStorageService:
    """Returns deterministic fake signed URLs for local testing."""
    bucket: str = "mindup-resources"

    def create_signed_view_url(self, storage_path: str) -> str:
        safe = storage_path.lstrip("/")
        return f"https://mock.supabase.local/storage/v1/object/sign/{self.bucket}/{safe}?token=mock&expiresIn=3600"


class SupabaseStorageService:
    """Generates signed URLs using Supabase Storage signing endpoint.

    POST {SUPABASE_URL}/storage/v1/object/sign/{bucket}/{path}
    Body: {"expiresIn": <seconds>}
    Headers: apikey + Authorization (Service Role)
    """

    def __init__(self, supabase_url: str, service_role_key: str, bucket: str, expires_in: int):
        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key
        self.bucket = bucket
        self.expires_in = expires_in

    def create_signed_view_url(self, storage_path: str) -> str:
        path = storage_path.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket}/{path}"
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }
        r = httpx.post(url, headers=headers, json={"expiresIn": self.expires_in}, timeout=20)
        r.raise_for_status()
        data = r.json()
        signed = data.get("signedURL") or data.get("signedUrl") or data.get("signed_url")
        if not signed:
            raise RuntimeError(f"Unexpected Supabase sign response: {data}")
        if signed.startswith("http://") or signed.startswith("https://"):
            return signed
        # Supabase often returns a relative path beginning with /storage/...
        return f"{self.supabase_url}{signed}"


def get_storage_service() -> StorageService:
    if settings.storage_mode == "mock":
        return MockStorageService(bucket=settings.supabase_storage_bucket)

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required when storage_mode=supabase")
    return SupabaseStorageService(
        supabase_url=settings.supabase_url,
        service_role_key=settings.supabase_service_role_key,
        bucket=settings.supabase_storage_bucket,
        expires_in=settings.supabase_signed_url_expires_in,
    )
