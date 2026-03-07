from __future__ import annotations

from typing import Any


TYPE_ALIASES = {
    "site plan control": "site_plan",
    "site_plan": "site_plan",
    "zoning by-law amendment": "zba",
    "zoning by law amendment": "zba",
    "zoning bylaw amendment": "zba",
    "zba": "zba",
    "minor variance": "minor_variance",
    "consent": "consent",
    "tlab": "appeal",
    "olt": "appeal",
}


def normalize_application_type(value: str | None) -> str:
    if not value:
        return "unknown"
    normalized = value.strip().lower().replace("-", " ").replace("/", " ")
    return TYPE_ALIASES.get(normalized, normalized.replace(" ", "_"))


def permit_bonus(count: int) -> float:
    if count <= 0:
        return 0.0
    if count == 1:
        return 0.05
    return 0.1


def score_precedent_match(
    application: Any,
    distance_m: float | None,
    scenario_metrics: dict[str, float | str | None],
    permit_count: int = 0,
) -> dict[str, Any]:
    distance = float(distance_m or 0.0)
    app_type = normalize_application_type(getattr(application, "app_type", None))
    target_type = normalize_application_type(str(scenario_metrics.get("application_type") or ""))
    distance_score = max(0.0, 1.0 - min(distance, 2000.0) / 2000.0)
    type_score = 1.0 if target_type and app_type == target_type else 0.6 if target_type else 0.5

    height_delta = abs(float(getattr(application, "proposed_height_m", 0.0) or 0.0) - float(scenario_metrics.get("height_m") or 0.0))
    units_delta = abs(float(getattr(application, "proposed_units", 0.0) or 0.0) - float(scenario_metrics.get("units") or 0.0))
    fsi_delta = abs(float(getattr(application, "proposed_fsi", 0.0) or 0.0) - float(scenario_metrics.get("fsi") or 0.0))

    height_score = max(0.0, 1.0 - height_delta / 60.0) if scenario_metrics.get("height_m") else 0.5
    unit_score = max(0.0, 1.0 - units_delta / 400.0) if scenario_metrics.get("units") else 0.5
    fsi_score = max(0.0, 1.0 - fsi_delta / 8.0) if scenario_metrics.get("fsi") else 0.5

    decision = (getattr(application, "decision", None) or "").strip().lower()
    decision_score = {
        "approved": 1.0,
        "conditionally approved": 0.9,
        "refused": 0.25,
        "withdrawn": 0.15,
    }.get(decision, 0.5)

    score = (
        distance_score * 0.30
        + type_score * 0.15
        + height_score * 0.20
        + unit_score * 0.10
        + fsi_score * 0.10
        + decision_score * 0.10
        + permit_bonus(permit_count) * 0.05
    )
    return {
        "score": round(score, 4),
        "breakdown": {
            "distance_score": round(distance_score, 4),
            "type_score": round(type_score, 4),
            "height_score": round(height_score, 4),
            "unit_score": round(unit_score, 4),
            "fsi_score": round(fsi_score, 4),
            "decision_score": round(decision_score, 4),
            "permit_bonus": round(permit_bonus(permit_count), 4),
        },
    }
