import uuid
from types import SimpleNamespace

import pytest

from app.services.precedent import normalize_application_type, score_precedent_match
from app.services.thin_slice_runtime import (
    FinancialAssumptionPayload,
    MassingTemplateParameters,
    TORONTO_FINANCIAL_ASSUMPTIONS,
    TORONTO_MASSING_TEMPLATES,
    compute_financial_output,
    compute_layout_result,
    compute_massing_summary,
)


def _parcel(*, lot_area_m2: float, geom_area_m2: float | None = None):
    return SimpleNamespace(lot_area_m2=lot_area_m2, geom_area_m2=geom_area_m2)


def _unit_type(name: str, bedroom_count: int, typical_area_m2: float, *, is_accessible: bool = False):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        bedroom_count=bedroom_count,
        typical_area_m2=typical_area_m2,
        is_accessible=is_accessible,
    )


def _template(index: int = 0, **overrides):
    payload = dict(TORONTO_MASSING_TEMPLATES[index]["parameters_json"])
    payload.update(overrides)
    return MassingTemplateParameters.model_validate(payload)


def test_compute_massing_summary_caps_to_policy_fsi():
    summary, compliance = compute_massing_summary(_parcel(lot_area_m2=1000.0), _template(0))

    assert summary["estimated_gfa_m2"] == 10000.0
    assert summary["estimated_fsi"] == 10.0
    assert compliance["max_fsi_applied"] == 10.0


def test_compute_massing_summary_rejects_zero_area_parcel():
    with pytest.raises(ValueError, match="positive lot area"):
        compute_massing_summary(_parcel(lot_area_m2=0.0), _template(0))


def test_compute_layout_result_produces_deterministic_toronto_allocation():
    summary, _ = compute_massing_summary(_parcel(lot_area_m2=1000.0), _template(0))
    unit_types = [
        _unit_type("studio", 0, 40.0),
        _unit_type("one_bed", 1, 52.0),
        _unit_type("two_bed", 2, 74.0),
        _unit_type("three_bed", 3, 96.0),
        _unit_type("one_bed_accessible", 1, 58.0, is_accessible=True),
        _unit_type("two_bed_accessible", 2, 82.0, is_accessible=True),
    ]

    result = compute_layout_result(summary, _template(0), unit_types)

    assert result["objective"] == "max_revenue"
    assert result["total_units"] == 139
    assert result["parking_required"] == 48.65
    assert result["amenity_required_m2"] == 278.0
    assert result["accessible_units_required"] == 21
    assert result["accessible_units_supplied"] == 0


def test_compute_layout_result_uses_even_mix_when_targets_missing():
    summary = {"estimated_gla_m2": 1000.0}
    template = _template(
        0,
        layout_defaults={
            "unit_mix_targets": {},
            "objective": "max_revenue",
        },
    )
    unit_types = [
        _unit_type("studio", 0, 40.0),
        _unit_type("one_bed", 1, 52.0),
    ]

    result = compute_layout_result(summary, template, unit_types)

    assert [allocation["count"] for allocation in result["allocations"]] == [12, 9]
    assert result["total_units"] == 21


def test_compute_financial_output_rental_uses_average_rate_fallback():
    assumptions = FinancialAssumptionPayload.model_validate(
        {
            "tenure": "rental",
            "revenue_assumptions": {
                "rate_per_m2_by_unit_type": {"studio": 420.0},
                "annualization_factor": 12.0,
            },
            "cost_assumptions": {
                "hard_cost_per_m2": 1000.0,
                "soft_cost_pct": 0.2,
                "opex_pct_of_revenue": 0.25,
                "contingency_pct": 0.1,
            },
            "vacancy_rate": 0.05,
            "absorption_months": 12,
            "valuation": {"cap_rate": 0.05},
            "financing": {"loan_to_cost_pct": 0.65, "interest_rate": 0.055},
        }
    )
    unit_types = [
        _unit_type("studio", 0, 40.0),
        _unit_type("one_bed", 1, 52.0),
    ]
    layout_result = {
        "allocations": [
            {"name": "studio", "count": 5},
            {"name": "one_bed", "count": 3},
        ]
    }
    massing_summary = {"estimated_gfa_m2": 1000.0}

    output = compute_financial_output(layout_result, massing_summary, unit_types, assumptions)

    assert output["total_revenue"] == 1704528.0
    assert output["valuation"] == 25567920.0
    assert output["residual_land_value"] == 24247920.0


def test_compute_financial_output_condo_uses_revenue_as_valuation():
    assumptions = FinancialAssumptionPayload.model_validate(TORONTO_FINANCIAL_ASSUMPTIONS[1]["assumptions_json"])
    unit_types = [_unit_type("studio", 0, 40.0)]
    layout_result = {"allocations": [{"name": "studio", "count": 2}]}
    massing_summary = {"estimated_gfa_m2": 500.0}

    output = compute_financial_output(layout_result, massing_summary, unit_types, assumptions)

    assert output["tenure"] == "condo"
    assert output["total_revenue"] == 1060000.0
    assert output["valuation"] == 1060000.0
    assert output["residual_land_value"] < output["valuation"]


def test_score_precedent_match_favors_closer_approved_and_more_similar_cases():
    scenario_metrics = {
        "application_type": "Zoning By-law Amendment",
        "height_m": 72.0,
        "units": 240,
        "fsi": 7.5,
    }
    stronger = SimpleNamespace(
        app_type="zba",
        proposed_height_m=70.0,
        proposed_units=235,
        proposed_fsi=7.2,
        decision="approved",
    )
    weaker = SimpleNamespace(
        app_type="site plan control",
        proposed_height_m=18.0,
        proposed_units=40,
        proposed_fsi=1.4,
        decision="withdrawn",
    )

    stronger_score = score_precedent_match(stronger, 120.0, scenario_metrics, permit_count=2)
    weaker_score = score_precedent_match(weaker, 1800.0, scenario_metrics, permit_count=0)

    assert normalize_application_type("Zoning By-law Amendment") == "zba"
    assert stronger_score["score"] > weaker_score["score"]
    assert stronger_score["breakdown"]["distance_score"] > weaker_score["breakdown"]["distance_score"]
