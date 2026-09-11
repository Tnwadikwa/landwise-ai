# Landwise AI

A FastAPI service that estimates Abuja development feasibility, FCDA-related planning notes, project finances, and marketing copy.

Public domain: <https://landwiseai.com>

## Setup

```zsh
cd /Users/toby/abuja-proptech
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

`OPENAI_API_KEY` is optional. If it is empty, the API returns safe fallback marketing copy.

Set `SITE_URL=https://landwiseai.com` in production. Never commit `.env` or API keys.

## Run

```zsh
uvicorn app.main:app --reload
```

Open the website at <http://127.0.0.1:8000/> or the interactive API documentation at <http://127.0.0.1:8000/docs>.

## Accounts

The website now includes email/password registration at `/login.html` and a signed-in workspace at `/dashboard.html`. Sessions use an HTTP-only cookie and passwords are stored as PBKDF2 hashes. This is an MVP authentication flow; before onboarding real customers, move users and sessions to managed PostgreSQL, add email verification, password recovery, and two-factor authentication.

Local development falls back to SQLite through `DATABASE_PATH`. Production must set `DATABASE_URL` to a managed PostgreSQL connection string because Render's default filesystem is temporary. Create a PostgreSQL database with Render, Supabase, Neon, or another provider, then add its private connection URL to the Web Service environment variables. Existing SQLite accounts will need to be recreated or migrated.

Document uploads use Supabase Storage when `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_DOCUMENT_BUCKET` are configured. The local app falls back to `LOCAL_DOCUMENT_PATH` (default: `/tmp/landwise-ai-documents`) when those Supabase variables are empty, so uploads can be tested locally without exposing a service-role key. Configure the Supabase variables in the local shell as well if you want to test the production storage path.

Password recovery requires SMTP environment variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL`. Add these securely in Render before using recovery with customers.

## Deploy the public site

Deploy this project to a host that supports Python web services, such as Render, Railway, Fly.io, or a VPS. Use this start command:

```zsh
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Then point `landwiseai.com` to the host using the DNS records supplied by that provider. Enable HTTPS, set `SITE_URL=https://landwiseai.com`, and verify `/health`, `/robots.txt`, and `/sitemap.xml` after DNS finishes propagating.

## Test

```zsh
pytest
```

## Endpoint

`POST /api/v1/feasibility/generate`

Example request:

```json
{
  "district": "Katampe Extension",
  "plot_size_sqm": 1200,
  "title_type": "Right of Occupancy (R of O)",
  "cadastral_zone": "Zone B07",
  "target_asset_type": "4-Bedroom Terrace Duplexes",
  "acquisition_cost_ngn": 150000000
}
```

The financial values are estimates and should be validated by qualified planning, legal, and financial professionals before investment decisions.
