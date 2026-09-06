from openai import AsyncOpenAI

from app.config import settings


def fallback_marketing_copy(district: str, asset_type: str, units: int) -> str:
    return (
        f"Luxury development opportunity in {district}, Abuja, offering {units} units of "
        f"{asset_type}. Contact us for title verification, investment details, and the sales brochure."
    )


async def generate_global_marketing_copy(district: str, asset_type: str, units: int) -> str:
    if not settings.openai_api_key:
        return fallback_marketing_copy(district, asset_type, units)

    prompt = (
        "Write a concise, professional luxury real-estate marketing blurb for international "
        "diaspora investors and local buyers in Abuja, Nigeria.\n"
        f"Location: {district}, Abuja\nAsset type: {units} units of {asset_type}\n"
        "Mention prime location, title verification, smart-home potential, and rental yield."
    )

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
        )
        content = response.choices[0].message.content
        return content.strip() if content else fallback_marketing_copy(district, asset_type, units)
    except Exception:
        return fallback_marketing_copy(district, asset_type, units)
