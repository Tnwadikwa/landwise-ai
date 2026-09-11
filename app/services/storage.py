import logging
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _storage_headers() -> dict[str, str]:
    if not settings.supabase_url or not settings.supabase_service_role_key or not settings.supabase_document_bucket:
        raise RuntimeError("Private document storage is not configured.")
    return {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }


def upload_private_document(storage_key: str, content: bytes, content_type: str) -> None:
    headers = _storage_headers()
    url = (
        f"{settings.supabase_url}/storage/v1/object/"
        f"{quote(settings.supabase_document_bucket, safe='')}/{quote(storage_key, safe='/')}"
    )
    response = httpx.post(
        url,
        headers={**headers, "Content-Type": content_type, "x-upsert": "false"},
        content=content,
        timeout=15,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        if response.status_code in {401, 403}:
            message = "Private document storage rejected the credentials. Check the Supabase service-role key in Render."
        elif response.status_code == 404:
            message = "Private document storage could not find the bucket or Supabase project. Check SUPABASE_URL and SUPABASE_DOCUMENT_BUCKET in Render."
        else:
            message = "Private document storage is temporarily unavailable. Please try again shortly."
        raise RuntimeError(message) from error


def create_private_download_url(storage_key: str) -> str:
    headers = _storage_headers()
    url = (
        f"{settings.supabase_url}/storage/v1/object/sign/"
        f"{quote(settings.supabase_document_bucket, safe='')}/{quote(storage_key, safe='/')}"
    )
    response = httpx.post(url, headers=headers, json={"expiresIn": 300}, timeout=15)
    try:
        response.raise_for_status()
        signed_path = response.json()["signedURL"]
    except (httpx.HTTPError, KeyError, ValueError) as error:
        raise RuntimeError("A secure document link could not be created. Check Supabase storage configuration.") from error
    return signed_path if signed_path.startswith("http") else f"{settings.supabase_url}/storage/v1{signed_path}"


def download_private_document(storage_key: str) -> bytes:
    url = (
        f"{settings.supabase_url}/storage/v1/object/"
        f"{quote(settings.supabase_document_bucket or '', safe='')}/{quote(storage_key, safe='/')}"
    )
    response = httpx.get(url, headers=_storage_headers(), timeout=15)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise RuntimeError("The private document could not be retrieved.") from error
    return response.content


def delete_private_documents(storage_keys: list[str]) -> None:
    if not storage_keys:
        return
    url = f"{settings.supabase_url}/storage/v1/object/{quote(settings.supabase_document_bucket or '', safe='')}"
    try:
        response = httpx.delete(url, headers=_storage_headers(), json={"prefixes": storage_keys}, timeout=15)
        response.raise_for_status()
    except Exception as error:
        logger.warning("Supabase document deletion failed: %s", error)
        raise RuntimeError("The private documents could not be deleted.") from error


def delete_private_document(storage_key: str) -> None:
    delete_private_documents([storage_key])