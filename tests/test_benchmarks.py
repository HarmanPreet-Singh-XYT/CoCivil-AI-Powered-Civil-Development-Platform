from pathlib import Path

from app.services.benchmarks import (
    TorontoCoreBenchmarkCase,
    evaluate_core_benchmark_case,
    load_toronto_core_benchmarks,
    summarize_benchmark_results,
)


def test_load_toronto_core_benchmarks_uses_template_seed_file():
    path = Path(__file__).parent / "fixtures" / "benchmarks" / "toronto_core.json"
    cases = load_toronto_core_benchmarks(path)

    assert len(cases) == 3
    assert all(case.verification_status == "template" for case in cases)


def test_evaluate_verified_benchmark_case():
    case = TorontoCoreBenchmarkCase.model_validate(
        {
            "benchmark_id": "verified-case",
            "verification_status": "verified",
            "source_notes": "Synthetic verified case used to test benchmark scoring logic.",
            "address_input": "100 Queen St W, Toronto, ON",
            "expected_parcel": {"address": "100 Queen St W, Toronto, ON"},
            "expected_zoning": {"zone_code": "CR 3.0"},
            "expected_policy_stack": {
                "required_documents": ["Zoning By-law 569-2013"],
                "required_sections": ["40.10.40.10"],
            },
            "expected_scenario": {
                "scenario_type": "base",
                "expected_constraints": ["max_height"],
                "expected_metrics": {"max_height_m": 36.0},
            },
        }
    )

    actual = {
        "parcel": {"address": "100 Queen St W, Toronto, ON"},
        "zoning": {"zone_code": "CR 3.0"},
        "policy_stack": {
            "documents": ["Zoning By-law 569-2013"],
            "sections": ["40.10.40.10"],
        },
        "scenario": {
            "scenario_type": "base",
            "constraints": ["max_height"],
            "metrics": {"max_height_m": 36.0},
        },
    }

    result = evaluate_core_benchmark_case(case, actual)

    assert result.status == "passed"
    assert result.failures == []
    assert result.total_checks == 7


def test_benchmark_summary_ignores_template_cases():
    verified_case = TorontoCoreBenchmarkCase.model_validate(
        {
            "benchmark_id": "verified-case",
            "verification_status": "verified",
            "source_notes": "Synthetic verified case used to test suite summary logic.",
            "address_input": "100 Queen St W, Toronto, ON",
            "expected_parcel": {"address": "100 Queen St W, Toronto, ON"},
        }
    )

    passed = evaluate_core_benchmark_case(
        verified_case,
        {"parcel": {"address": "100 Queen St W, Toronto, ON"}},
    )
    skipped = evaluate_core_benchmark_case(
        TorontoCoreBenchmarkCase.model_validate(
            {
                "benchmark_id": "template-case",
                "verification_status": "template",
                "source_notes": "Pending manual verification.",
                "address_input": "111 Richmond St W, Toronto, ON",
            }
        ),
        {},
    )

    summary = summarize_benchmark_results([passed, skipped])

    assert summary["case_count"] == 1
    assert summary["skipped_case_count"] == 1
    assert summary["pass_rate"] == 1.0
