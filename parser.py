import re
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import requests

COORD_PAIR_RE = re.compile(
    r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$"
)
COORD_PAIR_ANYWHERE_RE = re.compile(
    r"(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)"
)
AT_COORD_RE = re.compile(
    r"@\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)",
    re.IGNORECASE,
)
BANG_COORD_RE = re.compile(
    r"!3d(-?\d{1,2}(?:\.\d+)?)!4d(-?\d{1,3}(?:\.\d+)?)",
    re.IGNORECASE,
)

SHORT_DOMAINS = {"maps.app.goo.gl", "goo.gl"}


def _is_valid_coordinate(lat: float, lng: float) -> bool:
    return -90 <= lat <= 90 and -180 <= lng <= 180


def _to_valid_coordinate_pair(lat_str: str, lng_str: str) -> Optional[Tuple[float, float]]:
    try:
        lat = float(lat_str)
        lng = float(lng_str)
    except (TypeError, ValueError):
        return None

    if not _is_valid_coordinate(lat, lng):
        return None

    return lat, lng


def _extract_raw_coordinates(text: str) -> Optional[Tuple[float, float]]:
    match = COORD_PAIR_RE.match(text)
    if not match:
        return None
    return _to_valid_coordinate_pair(match.group(1), match.group(2))


def _search_with_regex(pattern: re.Pattern, text: str) -> Optional[Tuple[float, float]]:
    match = pattern.search(text)
    if not match:
        return None
    return _to_valid_coordinate_pair(match.group(1), match.group(2))


def _extract_exact_pin_coordinates(decoded_text: str) -> Optional[Tuple[float, float]]:
    # Highest priority: Google pinned-place coordinates encoded as !3dLAT!4dLNG.
    return _search_with_regex(BANG_COORD_RE, decoded_text)


def _extract_map_center_coordinates(decoded_text: str) -> Optional[Tuple[float, float]]:
    # Second priority: @LAT,LNG map center coordinates.
    return _search_with_regex(AT_COORD_RE, decoded_text)


def _extract_plain_coordinates_from_url(decoded_text: str) -> Optional[Tuple[float, float]]:
    parsed = urlparse(decoded_text)
    query = parse_qs(parsed.query)

    # Look into query parameters that often carry direct coordinates.
    for key in ("q", "ll", "query", "destination", "origin"):
        for value in query.get(key, []):
            match = COORD_PAIR_ANYWHERE_RE.search(value)
            if match:
                coords = _to_valid_coordinate_pair(match.group(1), match.group(2))
                if coords:
                    return coords

    # Last fallback for plain LAT,LNG anywhere in the decoded URL.
    generic_match = COORD_PAIR_ANYWHERE_RE.search(decoded_text)
    if generic_match:
        return _to_valid_coordinate_pair(generic_match.group(1), generic_match.group(2))

    return None


def extract_coordinate_pair(text: str) -> Optional[Tuple[float, float]]:
    """Return coordinates with strict priority: !3d!4d > @lat,lng > plain lat,lng."""
    decoded = unquote(text)

    for extractor in (
        _extract_exact_pin_coordinates,
        _extract_map_center_coordinates,
        _extract_plain_coordinates_from_url,
    ):
        coords = extractor(decoded)
        if coords:
            return coords

    return None


def _normalize_to_url(text: str) -> Optional[str]:
    candidate = text.strip()
    if not candidate:
        return None

    if candidate.startswith(("http://", "https://")):
        return candidate

    if candidate.startswith("www."):
        return f"https://{candidate}"

    return None


def _is_short_maps_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if host not in SHORT_DOMAINS:
        return False

    if host == "goo.gl":
        return parsed.path.startswith("/maps")

    return True


def _resolve_short_url(url: str, timeout: int) -> Tuple[bool, str]:
    try:
        # stream=True avoids downloading full response bodies during redirects.
        response = requests.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            stream=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        final_url = response.url
        response.close()
    except requests.Timeout:
        return False, "Short link resolution timed out. Try the full Google Maps link."
    except requests.RequestException:
        return False, "Failed to resolve short Google Maps link."

    if not final_url:
        return False, "Could not resolve shortened Google Maps link."

    return True, final_url


def extract_coordinates(raw_input: str, timeout: int = 10) -> Dict[str, object]:
    text = raw_input.strip()
    if not text:
        return {"ok": False, "error": "Input cannot be empty."}

    raw_coords = _extract_raw_coordinates(text)
    if raw_coords:
        return {"ok": True, "lat": raw_coords[0], "lng": raw_coords[1]}

    normalized_url = _normalize_to_url(text)
    if not normalized_url:
        return {
            "ok": False,
            "error": "Invalid input. Provide a Google Maps URL or raw coordinates (lat,lng).",
        }

    parsed_host = urlparse(normalized_url).netloc.lower()
    if "google." not in parsed_host and parsed_host not in SHORT_DOMAINS:
        return {
            "ok": False,
            "error": "The URL does not appear to be a valid Google Maps link.",
        }

    url_for_parsing = normalized_url
    if _is_short_maps_url(normalized_url):
        ok, resolved_or_error = _resolve_short_url(normalized_url, timeout)
        if not ok:
            return {"ok": False, "error": resolved_or_error}
        url_for_parsing = resolved_or_error

    coords = extract_coordinate_pair(url_for_parsing)
    if not coords:
        return {
            "ok": False,
            "error": "Could not extract coordinates from the provided Google Maps link.",
        }

    return {"ok": True, "lat": coords[0], "lng": coords[1]}
