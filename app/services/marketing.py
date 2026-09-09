from openai import AsyncOpenAI

from app.config import settings


def fallback_marketing_copy(
    district: str,
    cadastral_zone: str,
    title_type: str,
    asset_type: str,
    units: int,
) -> str:
    return (
        f"Development opportunity in {district}, cadastral zone {cadastral_zone}, "
        f"offering {units} units of {asset_type}. The site is presented under "
        f"{title_type}. Confirm the title, local planning requirements, access, "
        "services, and market demand before making an investment decision."
    )


async def generate_global_marketing_copy(
    district: str,
    cadastral_zone: str,
    title_type: str,
    asset_type: str,
    units: int,
) -> str:
    if not settings.openai_api_key:
        return fallback_marketing_copy(district, cadastral_zone, title_type, asset_type, units)

    prompt = (
        "Write a concise, professional real-estate marketing blurb using only the supplied "
        "project facts. Do not assume a country, city, state, planning authority, market, "
        "rental yield, infrastructure, or local advantage that is not provided. Do not call "
        "the location prime unless the supplied facts establish that. Use careful language "
        "such as 'the proposed development' and end with a practical verification note.\n"
        f"District or locality: {district}\nCadastral zone: {cadastral_zone}\n"
        f"Title type: {title_type}\nDevelopment: {units} units of {asset_type}\n"
    )

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
        )
        content = response.choices[0].message.content
        return content.strip() if content else fallback_marketing_copy(district, cadastral_zone, title_type, asset_type, units)
    except Exception:
        return fallback_marketing_copy(district, cadastral_zone, title_type, asset_type, units)
