from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ValidationIssue:
    code: str
    message: str
    blocking: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationSummary:
    ok: bool
    blocking_issue_count: int
    non_blocking_issue_count: int
    issues: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_issues(issues: list[ValidationIssue]) -> ValidationSummary:
    blocking = [issue for issue in issues if issue.blocking]
    non_blocking = [issue for issue in issues if not issue.blocking]
    return ValidationSummary(
        ok=not blocking,
        blocking_issue_count=len(blocking),
        non_blocking_issue_count=len(non_blocking),
        issues=[issue.to_dict() for issue in issues],
    )


def validate_source_metadata(metadata: dict[str, Any]) -> ValidationSummary:
    issues: list[ValidationIssue] = []
    if not metadata.get("publisher"):
        issues.append(ValidationIssue("missing_publisher", "publisher is required"))
    if not metadata.get("source_url"):
        issues.append(ValidationIssue("missing_source_url", "source_url is required"))
    if metadata.get("license_status", "unknown") == "unknown":
        issues.append(ValidationIssue("unknown_license_status", "license_status must be explicit"))
    if not metadata.get("export_allowed", False) and metadata.get("derived_export_allowed", False):
        issues.append(
            ValidationIssue(
                "derived_export_only",
                "derived export is allowed, but raw export is not",
                blocking=False,
            )
        )
    return summarize_issues(issues)


def validate_policy_rule(rule: dict[str, Any]) -> ValidationSummary:
    issues: list[ValidationIssue] = []
    if not rule.get("section_ref"):
        issues.append(ValidationIssue("missing_section_ref", "section_ref is required"))
    normalized = rule.get("normalized_json") or {}
    if not normalized.get("rule_type"):
        issues.append(ValidationIssue("missing_rule_type", "normalized_json.rule_type is required"))
    if normalized.get("effective_date") in (None, ""):
        issues.append(ValidationIssue("missing_effective_date", "normalized_json.effective_date is required"))
    confidence = rule.get("confidence")
    if confidence is None or not 0.0 <= float(confidence) <= 1.0:
        issues.append(ValidationIssue("invalid_confidence", "confidence must be between 0 and 1"))
    if confidence is not None and float(confidence) < 0.6:
        issues.append(
            ValidationIssue("low_confidence", "low-confidence policy extraction requires review", blocking=False)
        )
    return summarize_issues(issues)


def validate_precedent_record(record: dict[str, Any]) -> ValidationSummary:
    issues: list[ValidationIssue] = []
    if not record.get("app_number"):
        issues.append(ValidationIssue("missing_app_number", "app_number is required"))
    if not record.get("status"):
        issues.append(ValidationIssue("missing_status", "status is required"))
    if not any(record.get(field) for field in ("parcel_id", "geom", "address")):
        issues.append(
            ValidationIssue("missing_location_linkage", "precedent record needs parcel_id, geom, or address")
        )
    if record.get("license_status", "unknown") == "unknown":
        issues.append(ValidationIssue("unknown_license_status", "license_status must be explicit"))
    return summarize_issues(issues)


def validate_finance_record(record: dict[str, Any]) -> ValidationSummary:
    issues: list[ValidationIssue] = []
    if not record.get("effective_date"):
        issues.append(ValidationIssue("missing_effective_date", "effective_date is required"))
    if not record.get("source"):
        issues.append(ValidationIssue("missing_source", "source is required"))
    attributes = record.get("attributes_json") or {}
    if not attributes.get("unit_basis"):
        issues.append(ValidationIssue("missing_unit_basis", "attributes_json.unit_basis is required"))
    if not attributes.get("geography"):
        issues.append(ValidationIssue("missing_geography", "attributes_json.geography is required"))
    if record.get("license_status", "unknown") == "unknown":
        issues.append(ValidationIssue("unknown_license_status", "license_status must be explicit"))
    return summarize_issues(issues)
