from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from typing import Any


def build_manifest_hash(
    jurisdiction_id: uuid.UUID,
    items: list[dict[str, Any]],
    parser_versions: dict[str, Any] | None = None,
    model_versions: dict[str, Any] | None = None,
) -> str:
    payload = {
        "jurisdiction_id": str(jurisdiction_id),
        "items": sorted(
            [
                {
                    "source_snapshot_id": str(item["source_snapshot_id"]),
                    "snapshot_role": item["snapshot_role"],
                    "is_required": bool(item.get("is_required", True)),
                }
                for item in items
            ],
            key=lambda item: (item["snapshot_role"], item["source_snapshot_id"]),
        ),
        "parser_versions": parser_versions or {},
        "model_versions": model_versions or {},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass(slots=True)
class ExportControlDecision:
    decision: str
    governance_status: str
    blocked_reason: str | None
    applied_controls: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_export_controls(source_controls: list[dict[str, Any]] | None) -> ExportControlDecision:
    if not source_controls:
        return ExportControlDecision(
            decision="allow",
            governance_status="approved",
            blocked_reason=None,
            applied_controls=[],
        )

    normalized = []
    for control in source_controls:
        normalized.append(
            {
                "source": control.get("source") or control.get("source_type") or "unknown",
                "license_status": control.get("license_status", "unknown"),
                "internal_storage_allowed": bool(control.get("internal_storage_allowed", False)),
                "export_allowed": bool(control.get("export_allowed", False)),
                "derived_export_allowed": bool(control.get("derived_export_allowed", False)),
                "aggregation_required": bool(control.get("aggregation_required", False)),
            }
        )

    if any(control["license_status"] == "unknown" for control in normalized):
        return ExportControlDecision(
            decision="block",
            governance_status="blocked",
            blocked_reason="unknown_license_status",
            applied_controls=normalized,
        )

    if any(not control["internal_storage_allowed"] for control in normalized):
        return ExportControlDecision(
            decision="block",
            governance_status="blocked",
            blocked_reason="internal_storage_disallowed",
            applied_controls=normalized,
        )

    if any(not control["export_allowed"] and not control["derived_export_allowed"] for control in normalized):
        return ExportControlDecision(
            decision="block",
            governance_status="blocked",
            blocked_reason="export_disallowed",
            applied_controls=normalized,
        )

    if any(control["aggregation_required"] or not control["export_allowed"] for control in normalized):
        return ExportControlDecision(
            decision="redact",
            governance_status="redacted",
            blocked_reason=None,
            applied_controls=normalized,
        )

    return ExportControlDecision(
        decision="allow",
        governance_status="approved",
        blocked_reason=None,
        applied_controls=normalized,
    )
