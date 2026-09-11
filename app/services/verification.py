import re

from app.schemas import PlotDetails


_PLACEHOLDER_VALUES = {
    "na",
    "n/a",
    "none",
    "test",
    "testing",
    "unknown",
    "-",
}
_TITLE_KEYWORDS = (
    "certificate of occupancy",
    "c of o",
    "right of occupancy",
    "r of o",
    "deed",
    "leasehold",
    "freehold",
    "governor's consent",
    "governors consent",
)


def validate_supplied_land_details(plot: PlotDetails) -> None:
    values = {
        "district": plot.district,
        "title type": plot.title_type,
        "cadastral zone": plot.cadastral_zone,
        "target asset type": plot.target_asset_type,
    }
    for label, value in values.items():
        normalized = value.strip().lower()
        if normalized in _PLACEHOLDER_VALUES or not re.search(r"[a-zA-Z]", normalized):
            raise ValueError(f"Enter a real {label}; placeholder values cannot be analysed.")

    title_type = plot.title_type.strip().lower()
    if not any(keyword in title_type for keyword in _TITLE_KEYWORDS):
        raise ValueError(
            "The title type could not be recognised. Use a Nigerian title such as C of O, R of O, deed, or leasehold."
        )

    if plot.plot_size_sqm > 1_000_000:
        raise ValueError("The plot size is outside the supported range. Check the survey measurement.")
    if plot.acquisition_cost_ngn > 100_000_000_000:
        raise ValueError("The acquisition cost is outside the supported range. Check the entered amount.")