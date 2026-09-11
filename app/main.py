from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.routes.feasibility import router as feasibility_router
from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router
from app.routes.premium import router as premium_router
from app.config import settings
from app.services.auth import database_diagnostics, engine, init_database

app = FastAPI(
    title="Landwise AI",
    version="1.0.0",
    description="AI-guided property feasibility analysis and marketing for land development.",
)

app.include_router(feasibility_router)
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(premium_router)
init_database()


@app.get("/health")
def health_check() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {
        "status": "ok",
        **database_diagnostics(),
        "smtp": "configured" if all(
            (settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_from_email)
        ) else "incomplete",
        "private_document_storage": "configured" if all(
            (settings.supabase_url, settings.supabase_service_role_key, settings.supabase_document_bucket)
        ) else "incomplete",
    }


@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
def robots() -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {settings.site_url}/sitemap.xml\n"


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap() -> Response:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{settings.site_url}/</loc></url>"
        "</urlset>"
    )
    return Response(content=body, media_type="application/xml")


# The consumer website is served at /; API routes remain under /api.
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="website")
