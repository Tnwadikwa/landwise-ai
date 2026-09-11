from urllib.parse import quote

import httpx

from app.config import settings


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
        raise RuntimeError("The document could not be stored securely.") from error


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
        raise RuntimeError("A secure document link could not be created.") from error
    return signed_path if signed_path.startswith("http") else f"{settings.supabase_url}{signed_path}"


def delete_private_documents(storage_keys: list[str]) -> None:
    if not storage_keys:
        return
    url = f"{settings.supabase_url}/storage/v1/object/{quote(settings.supabase_document_bucket or '', safe='')}"
    response = httpx.delete(url, headers=_storage_headers(), json={"prefixes": storage_keys}, timeout=15)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise RuntimeError("The private documents could not be deleted.") from error