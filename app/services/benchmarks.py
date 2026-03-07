from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class PolicyStackExpectation(BaseModel):
    required_documents: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)


class ScenarioExpectation(BaseModel):
    scenario_type: str
    expected_constraints: list[str] = Field(default_factory=list)
    expected_metrics: dict[str, float] = Field(default_factory=dict)


class TorontoCoreBenchmarkCase(BaseModel):
    benchmark_id: str
    verification_status: Literal["template", "verified"] = "template"
    source_notes: str
    address_input: str
    expected_parcel: dict[str, Any] | None = None
    expected_zoning: dict[str, Any] | None = None
    expected_policy_stack: PolicyStackExpectation | None = None
    expected_scenario: ScenarioExpectation | None = None


@dataclass(slots=True)
class BenchmarkResult:
    benchmark_id: str
    status: str
    passed_checks: int
    total_checks: int
    failures: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_toronto_core_benchmarks(path: str | Path) -> list[TorontoCoreBenchmarkCase]:
    data = json.loads(Path(path).read_text())
    return [TorontoCoreBenchmarkCase.model_validate(item) for item in data]


def evaluate_core_benchmark_case(
    case: TorontoCoreBenchmarkCase,
    actual: dict[str, Any],
) -> BenchmarkResult:
    if case.verification_status != "verified":
        return BenchmarkResult(
            benchmark_id=case.benchmark_id,
            status="skipped",
            passed_checks=0,
            total_checks=0,
            failures=[],
        )

    failures: list[str] = []
    passed_checks = 0
    total_checks = 0

    if case.expected_parcel:
        for key, expected in case.expected_parcel.items():
            total_checks += 1
            if actual.get("parcel", {}).get(key) == expected:
                passed_checks += 1
            else:
                failures.append(f"parcel.{key}")

    if case.expected_zoning:
        for key, expected in case.expected_zoning.items():
            total_checks += 1
            if actual.get("zoning", {}).get(key) == expected:
                passed_checks += 1
            else:
                failures.append(f"zoning.{key}")

    if case.expected_policy_stack:
        policy = actual.get("policy_stack", {})
        for document in case.expected_policy_stack.required_documents:
            total_checks += 1
            if document in policy.get("documents", []):
                passed_checks += 1
            else:
                failures.append(f"policy.documents:{document}")
        for section in case.expected_policy_stack.required_sections:
            total_checks += 1
            if section in policy.get("sections", []):
                passed_checks += 1
            else:
                failures.append(f"policy.sections:{section}")

    if case.expected_scenario:
        scenario = actual.get("scenario", {})
        total_checks += 1
        if scenario.get("scenario_type") == case.expected_scenario.scenario_type:
            passed_checks += 1
        else:
            failures.append("scenario.scenario_type")
        for constraint in case.expected_scenario.expected_constraints:
            total_checks += 1
            if constraint in scenario.get("constraints", []):
                passed_checks += 1
            else:
                failures.append(f"scenario.constraints:{constraint}")
        for metric, expected in case.expected_scenario.expected_metrics.items():
            total_checks += 1
            if scenario.get("metrics", {}).get(metric) == expected:
                passed_checks += 1
            else:
                failures.append(f"scenario.metrics:{metric}")

    status = "passed" if total_checks and not failures else "failed"
    return BenchmarkResult(
        benchmark_id=case.benchmark_id,
        status=status,
        passed_checks=passed_checks,
        total_checks=total_checks,
        failures=failures,
    )


def summarize_benchmark_results(results: list[BenchmarkResult]) -> dict[str, Any]:
    counted = [result for result in results if result.status != "skipped"]
    passed = [result for result in counted if result.status == "passed"]
    total_checks = sum(result.total_checks for result in counted)
    passed_checks = sum(result.passed_checks for result in counted)
    return {
        "case_count": len(counted),
        "passed_case_count": len(passed),
        "skipped_case_count": len(results) - len(counted),
        "pass_rate": 0.0 if not counted else len(passed) / len(counted),
        "check_pass_rate": 0.0 if not total_checks else passed_checks / total_checks,
    }
