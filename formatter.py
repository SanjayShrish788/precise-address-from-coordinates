from typing import Dict, List


def _clean(value: object) -> str:
    return str(value or "").strip()


def _is_placeholder_road(text: str) -> bool:
    lowered = text.strip().lower()
    return lowered in {"unnamed road", "unknown road", "unnamed", "na", "n/a"}


def _pick_first_non_empty(components: Dict, keys) -> str:
    for key in keys:
        value = _clean(components.get(key))
        if value:
            return value
    return ""


def _component_map_from_google(address_components: List[Dict]) -> Dict[str, str]:
    mapped: Dict[str, str] = {}
    for entry in address_components:
        long_name = _clean(entry.get("long_name"))
        for comp_type in entry.get("types", []):
            if comp_type not in mapped and long_name:
                mapped[comp_type] = long_name
    return mapped


def extract_address_components(result: Dict) -> Dict[str, str]:
    # Google Geocoding: list of {long_name, short_name, types}. Keep OpenCage fallback.
    google_components = result.get("address_components") or []
    if google_components:
        components = _component_map_from_google(google_components)
        house_number = _pick_first_non_empty(components, ("street_number",))
        road = _pick_first_non_empty(
            components,
            ("route", "premise", "point_of_interest", "establishment"),
        )
        suburb = _pick_first_non_empty(
            components,
            (
                "sublocality",
                "sublocality_level_1",
                "neighborhood",
                "sublocality_level_2",
                "administrative_area_level_3",
            ),
        )
        city = _pick_first_non_empty(
            components,
            (
                "locality",
                "postal_town",
                "administrative_area_level_2",
                "administrative_area_level_1",
            ),
        )
        state = _pick_first_non_empty(components, ("administrative_area_level_1",))
        postcode = _pick_first_non_empty(components, ("postal_code",))
        country = _pick_first_non_empty(components, ("country",))
    else:
        components = result.get("components", {}) or {}
        house_number = _clean(components.get("house_number"))

        road = _pick_first_non_empty(
            components,
            ("road", "footway", "residential", "path", "pedestrian"),
        )
        suburb = _pick_first_non_empty(
            components,
            ("suburb", "neighbourhood", "city_district", "quarter", "hamlet"),
        )

        city = _pick_first_non_empty(
            components,
            ("city", "town", "village", "municipality", "county"),
        )

        state = _pick_first_non_empty(components, ("state", "state_code"))
        postcode = _clean(components.get("postcode"))
        country = _clean(components.get("country"))

    if _is_placeholder_road(road):
        road = ""

    # Prefer road-level precision, but avoid surfacing placeholders like "unnamed road".
    line1_base = road or suburb or city
    line1 = " ".join(part for part in (house_number, line1_base) if part).strip()

    return {
        "line1": line1,
        "suburb": suburb,
        "city": city,
        "state": state,
        "postcode": postcode,
        "country": country,
    }


def format_address(parts: Dict[str, str]) -> str:
    line1 = _clean(parts.get("line1"))
    suburb = _clean(parts.get("suburb"))
    city = _clean(parts.get("city"))
    state = _clean(parts.get("state"))
    postcode = _clean(parts.get("postcode"))
    country = _clean(parts.get("country"))

    # Avoid duplicate text like "Bengaluru, Bengaluru".
    if suburb and city and suburb.casefold() == city.casefold():
        line2 = city
    else:
        line2 = ", ".join(p for p in (suburb, city) if p).strip()

    if state and postcode:
        line3 = f"{state} - {postcode}"
    else:
        line3 = state or postcode

    lines = [line for line in (line1, line2, line3, country) if line]
    return "\n".join(lines)
