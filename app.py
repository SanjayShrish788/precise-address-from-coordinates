import os
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from formatter import extract_address_components, format_address
from parser import extract_coordinates

load_dotenv()

app = Flask(__name__)

GOOGLE_GEOCODE_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))
SELECTION_DEBUG = os.getenv("GEOCODE_SELECTION_DEBUG", "0").strip() == "1"


def error_response(message: str, status_code: int = 400):
    return jsonify({"status": "error", "message": message}), status_code


def _google_status_to_error(status: str) -> str:
    mapping = {
        "ZERO_RESULTS": "No address found for the provided coordinates.",
        "OVER_QUERY_LIMIT": "Google Geocoding API quota exceeded. Please try later.",
        "REQUEST_DENIED": "Google Geocoding API request denied. Check API key and restrictions.",
        "INVALID_REQUEST": "Invalid geocoding request sent to Google API.",
        "UNKNOWN_ERROR": "Google Geocoding API returned an unknown error. Please retry.",
    }
    return mapping.get(status, f"Google Geocoding API error: {status}")


def _distance_sq(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Squared distance in lat/lng space for lightweight nearest-result ranking."""
    return (lat1 - lat2) ** 2 + (lng1 - lng2) ** 2


def _result_distance(result: Dict[str, Any], input_lat: float, input_lng: float) -> float:
    location = (result.get("geometry") or {}).get("location") or {}
    try:
        result_lat = float(location.get("lat"))
        result_lng = float(location.get("lng"))
    except (TypeError, ValueError):
        return float("inf")
    return _distance_sq(input_lat, input_lng, result_lat, result_lng)


def _has_any_type(result: Dict[str, Any], accepted_types: List[str]) -> bool:
    result_types = result.get("types") or []
    return any(result_type in accepted_types for result_type in result_types)


def _result_summary(result: Dict[str, Any], input_lat: float, input_lng: float) -> Dict[str, Any]:
    return {
        "formatted_address": result.get("formatted_address", ""),
        "types": result.get("types") or [],
        "location_type": ((result.get("geometry") or {}).get("location_type") or ""),
        "distance_sq": _result_distance(result, input_lat, input_lng),
    }


def _select_best_result_with_meta(
    results: List[Dict[str, Any]], input_lat: float, input_lng: float
) -> Dict[str, Any]:
    """
    Returns {"result": ..., "meta": ...} where meta carries selection diagnostics.
    """
    if not results:
        return {"result": {}, "meta": {"stage": "empty", "candidate_count": 0}}

    rooftop_results = [
        result
        for result in results
        if ((result.get("geometry") or {}).get("location_type") == "ROOFTOP")
    ]

    if rooftop_results:
        rooftop_precise = [
            result
            for result in rooftop_results
            if _has_any_type(result, ["street_address", "premise"])
        ]
        candidates = rooftop_precise or rooftop_results
        stage = "rooftop_precise" if rooftop_precise else "rooftop"
        chosen = min(candidates, key=lambda r: _result_distance(r, input_lat, input_lng))
        return {
            "result": chosen,
            "meta": {
                "stage": stage,
                "candidate_count": len(candidates),
                "chosen": _result_summary(chosen, input_lat, input_lng),
            },
        }

    for fallback_type in ("street_address", "route", "neighborhood"):
        candidates = [result for result in results if _has_any_type(result, [fallback_type])]
        if candidates:
            chosen = min(candidates, key=lambda r: _result_distance(r, input_lat, input_lng))
            return {
                "result": chosen,
                "meta": {
                    "stage": f"fallback_{fallback_type}",
                    "candidate_count": len(candidates),
                    "chosen": _result_summary(chosen, input_lat, input_lng),
                },
            }

    chosen = min(results, key=lambda r: _result_distance(r, input_lat, input_lng))
    return {
        "result": chosen,
        "meta": {
            "stage": "fallback_any",
            "candidate_count": len(results),
            "chosen": _result_summary(chosen, input_lat, input_lng),
        },
    }


def select_best_result(results: List[Dict[str, Any]], input_lat: float, input_lng: float) -> Dict[str, Any]:
    """
    Select most accurate Google geocoding result using strict priority rules:
    1) Prefer ROOFTOP results.
    2) Within ROOFTOP, prefer street_address/premise.
    3) Within candidates, choose smallest coordinate distance.
    4) If no ROOFTOP exists, fallback by types: street_address -> route -> neighborhood.
    """
    return _select_best_result_with_meta(results, input_lat, input_lng)["result"]


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/convert")
def convert():
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    raw_link = str(payload.get("link", "")).strip()

    if not raw_link:
        return error_response("Please provide a Google Maps link or coordinates.")

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return error_response("Server configuration error: missing Google API key.", 500)

    parsed = extract_coordinates(raw_link, timeout=REQUEST_TIMEOUT)
    if not parsed["ok"]:
        return error_response(parsed["error"])

    lat = parsed["lat"]
    lng = parsed["lng"]

    # Defensive validation in route as a safety net even though parser validates bounds.
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return error_response("Coordinates are out of range.")

    try:
        response = requests.get(
            GOOGLE_GEOCODE_ENDPOINT,
            params={
                "latlng": f"{lat},{lng}",
                "key": api_key,
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        return error_response("Google Geocoding API timed out. Please try again.", 504)
    except requests.RequestException:
        return error_response("Failed to reach Google Geocoding API. Please try again.", 502)

    if response.status_code >= 500:
        return error_response("Google Geocoding API is currently unavailable.", 502)
    if response.status_code in (401, 403):
        return error_response("Google Geocoding API authentication failed.", 502)
    if response.status_code == 429:
        return error_response("Google Geocoding API quota exceeded. Please try later.", 429)
    if response.status_code >= 400:
        return error_response("Google Geocoding API request failed.", 502)

    try:
        data = response.json()
    except ValueError:
        return error_response("Invalid response from Google Geocoding API.", 502)

    status = str(data.get("status", "")).strip()
    if status != "OK":
        return error_response(_google_status_to_error(status), 502 if status != "ZERO_RESULTS" else 404)

    results = data.get("results") or []
    if not results:
        return error_response("No address found for the provided coordinates.", 404)

    selection = _select_best_result_with_meta(results, lat, lng)
    best_result = selection.get("result") or {}
    if not best_result:
        return error_response("No suitable address candidate found.", 404)

    if SELECTION_DEBUG:
        meta = selection.get("meta") or {}
        app.logger.info(
            "geocode_selection stage=%s candidates=%s location_type=%s distance_sq=%.12f types=%s address=%s",
            meta.get("stage"),
            meta.get("candidate_count"),
            ((meta.get("chosen") or {}).get("location_type")),
            float((meta.get("chosen") or {}).get("distance_sq") or float("inf")),
            ((meta.get("chosen") or {}).get("types")),
            ((meta.get("chosen") or {}).get("formatted_address")),
        )

    components = extract_address_components(best_result)
    address = format_address(components)

    if not address:
        address = str(best_result.get("formatted_address", "")).strip()

    if not address:
        return error_response("Address data is incomplete for this location.", 404)

    return jsonify({"status": "success", "address": address})


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
