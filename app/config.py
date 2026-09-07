import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    site_url: str = os.getenv("SITE_URL", "https://landwiseai.com").rstrip("/")
    database_path: str = os.getenv("DATABASE_PATH", "/tmp/landwise-ai.db")
    smtp_host: str | None = os.getenv("SMTP_HOST")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str | None = os.getenv("SMTP_USERNAME")
    smtp_password: str | None = os.getenv("SMTP_PASSWORD")
    smtp_from_email: str | None = os.getenv("SMTP_FROM_EMAIL")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    max_coverage_ratio: float = float(os.getenv("MAX_COVERAGE_RATIO", "0.50"))
    cost_per_sqm_ngn: float = float(os.getenv("COST_PER_SQM_NGN", "350000"))
    unit_built_area_sqm: float = float(os.getenv("UNIT_BUILT_AREA_SQM", "250"))
    unit_sale_price_ngn: float = float(os.getenv("UNIT_SALE_PRICE_NGN", "180000000"))


settings = Settings()
