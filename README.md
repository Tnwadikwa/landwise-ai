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
