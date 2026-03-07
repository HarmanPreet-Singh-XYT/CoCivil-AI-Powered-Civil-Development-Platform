#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_sync_db
from app.devtools import redact_connection_url, render_preflight_checks, run_preflight_checks, raise_for_failed_checks
from app.models.dataset import DatasetFeature, DatasetLayer
from app.models.entitlement import DevelopmentApplication
from app.models.geospatial import Jurisdiction, Parcel, ParcelZoningAssignment
from app.models.ingestion import IngestionJob, SourceSnapshot
from app.models.policy import PolicyApplicabilityRule, PolicyClause, PolicyDocument, PolicyVersion
from app.schemas.geospatial import ParcelOverlaysResponse, PolicyStackResponse
from app.services.benchmarks import (
    evaluate_core_benchmark_case,
    load_toronto_core_benchmarks,
    summarize_benchmark_results,
)
from app.services.geospatial import list_active_snapshot_ids_sync, resolve_active_parcel_by_address_sync
from app.services.overlay_service import get_parcel_overlays_response_sync
from app.services.policy_stack import get_policy_stack_response_sync
from app.services.zoning_service import ZoningAnalysis, build_zoning_analysis

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "benchmarks" / "toronto_core.json"


def _count(db: Session, statement) -> int:
    return int(db.execute(statement).scalar() or 0)


def _rate(count: int, total: int) -> float:
    return 0.0 if total <= 0 else round((count / total) * 100.0, 2)


def _sorted_unique(values: list[str | None]) -> list[str]:
    return sorted({value for value in values if value})


def get_toronto_jurisdiction(db: Session) -> Jurisdiction:
    statement = (
        select(Jurisdiction)
        .where(func.lower(Jurisdiction.name).like("%toronto%"))
        .order_by(Jurisdiction.created_at.desc())
        .limit(1)
    )
    jurisdiction = db.execute(statement).scalar_one_or_none()
    if jurisdiction is None:
        raise RuntimeError("Toronto jurisdiction not found in the database")
    return jurisdiction


def collect_row_counts(db: Session, jurisdiction_id: uuid.UUID) -> dict[str, int]:
    return {
        "jurisdictions": _count(db, select(func.count()).select_from(Jurisdiction)),
        "source_snapshots": _count(
            db,
            select(func.count()).select_from(SourceSnapshot).where(SourceSnapshot.jurisdiction_id == jurisdiction_id),
        ),
        "ingestion_jobs": _count(
            db,
            select(func.count()).select_from(IngestionJob).where(IngestionJob.jurisdiction_id == jurisdiction_id),
        ),
        "parcels": _count(
            db,
            select(func.count()).select_from(Parcel).where(Parcel.jurisdiction_id == jurisdiction_id),
        ),
        "parcel_zoning_assignments": _count(
            db,
            select(func.count())
            .select_from(ParcelZoningAssignment)
            .join(Parcel, Parcel.id == ParcelZoningAssignment.parcel_id)
            .where(Parcel.jurisdiction_id == jurisdiction_id),
        ),
        "dataset_layers": _count(
            db,
            select(func.count()).select_from(DatasetLayer).where(DatasetLayer.jurisdiction_id == jurisdiction_id),
        ),
        "dataset_features": _count(
            db,
            select(func.count())
            .select_from(DatasetFeature)
            .join(DatasetLayer, DatasetLayer.id == DatasetFeature.dataset_layer_id)
            .where(DatasetLayer.jurisdiction_id == jurisdiction_id),
        ),
        "development_applications": _count(
            db,
            select(func.count())
            .select_from(DevelopmentApplication)
            .where(DevelopmentApplication.jurisdiction_id == jurisdiction_id),
        ),
        "policy_documents": _count(
            db,
            select(func.count()).select_from(PolicyDocument).where(PolicyDocument.jurisdiction_id == jurisdiction_id),
        ),
        "policy_versions": _count(
            db,
            select(func.count())
            .select_from(PolicyVersion)
            .join(PolicyDocument, PolicyDocument.id == PolicyVersion.document_id)
            .where(PolicyDocument.jurisdiction_id == jurisdiction_id),
        ),
        "policy_clauses": _count(
            db,
            select(func.count())
            .select_from(PolicyClause)
            .join(PolicyVersion, PolicyVersion.id == PolicyClause.policy_version_id)
            .join(PolicyDocument, PolicyDocument.id == PolicyVersion.document_id)
            .where(PolicyDocument.jurisdiction_id == jurisdiction_id),
        ),
        "policy_applicability_rules": _count(
            db,
            select(func.count())
            .select_from(PolicyApplicabilityRule)
            .where(PolicyApplicabilityRule.jurisdiction_id == jurisdiction_id),
        ),
    }


def collect_active_snapshot_counts(db: Session, jurisdiction_id: uuid.UUID) -> dict[str, int]:
    rows = db.execute(
        select(SourceSnapshot.snapshot_type, func.count())
        .where(SourceSnapshot.jurisdiction_id == jurisdiction_id)
        .where(SourceSnapshot.is_active.is_(True))
        .group_by(SourceSnapshot.snapshot_type)
        .order_by(SourceSnapshot.snapshot_type)
    ).all()
    return {snapshot_type: int(count) for snapshot_type, count in rows}


def collect_parcel_coverage(
    db: Session,
    jurisdiction_id: uuid.UUID,
    active_parcel_snapshot_ids: list[uuid.UUID],
) -> dict[str, Any]:
    parcel_filter = [Parcel.jurisdiction_id == jurisdiction_id]
    if active_parcel_snapshot_ids:
        parcel_filter.append(Parcel.source_snapshot_id.in_(list(active_parcel_snapshot_ids)))

    total = _count(db, select(func.count()).select_from(Parcel).where(*parcel_filter))
    with_address = _count(
        db,
        select(func.count())
        .select_from(Parcel)
        .where(*parcel_filter)
        .where(Parcel.address.is_not(None))
        .where(Parcel.address != ""),
    )
    with_zone_code = _count(
        db,
        select(func.count())
        .select_from(Parcel)
        .where(*parcel_filter)
        .where(Parcel.zone_code.is_not(None))
        .where(Parcel.zone_code != ""),
    )
    with_lot_area = _count(
        db,
        select(func.count()).select_from(Parcel).where(*parcel_filter).where(Parcel.lot_area_m2.is_not(None)),
    )
    with_frontage = _count(
        db,
        select(func.count()).select_from(Parcel).where(*parcel_filter).where(Parcel.lot_frontage_m.is_not(None)),
    )
    with_depth = _count(
        db,
        select(func.count()).select_from(Parcel).where(*parcel_filter).where(Parcel.lot_depth_m.is_not(None)),
    )
    with_current_use = _count(
        db,
        select(func.count()).select_from(Parcel).where(*parcel_filter).where(Parcel.current_use.is_not(None)),
    )

    return {
        "active_parcel_count": total,
        "with_address": with_address,
        "with_address_rate_pct": _rate(with_address, total),
        "with_zone_code": with_zone_code,
        "with_zone_code_rate_pct": _rate(with_zone_code, total),
        "with_lot_area_m2": with_lot_area,
        "with_lot_area_rate_pct": _rate(with_lot_area, total),
        "with_lot_frontage_m": with_frontage,
        "with_lot_frontage_rate_pct": _rate(with_frontage, total),
        "with_lot_depth_m": with_depth,
        "with_lot_depth_rate_pct": _rate(with_depth, total),
        "with_current_use": with_current_use,
        "with_current_use_rate_pct": _rate(with_current_use, total),
    }


def collect_zoning_summary(
    db: Session,
    jurisdiction_id: uuid.UUID,
    active_zoning_snapshot_ids: list[uuid.UUID],
) -> dict[str, Any]:
    assignment_filter = [Parcel.jurisdiction_id == jurisdiction_id]
    if active_zoning_snapshot_ids:
        assignment_filter.append(ParcelZoningAssignment.source_snapshot_id.in_(list(active_zoning_snapshot_ids)))

    assignment_base = (
        select(
            ParcelZoningAssignment.parcel_id.label("parcel_id"),
            func.count().label("assignment_count"),
        )
        .select_from(ParcelZoningAssignment)
        .join(Parcel, Parcel.id == ParcelZoningAssignment.parcel_id)
        .where(*assignment_filter)
        .group_by(ParcelZoningAssignment.parcel_id)
    ).subquery()

    total_assignments = _count(
        db,
        select(func.count())
        .select_from(ParcelZoningAssignment)
        .join(Parcel, Parcel.id == ParcelZoningAssignment.parcel_id)
        .where(*assignment_filter),
    )
    assigned_parcels = _count(db, select(func.count()).select_from(assignment_base))
    multi_zone_parcels = _count(
        db,
        select(func.count()).select_from(assignment_base).where(assignment_base.c.assignment_count > 1),
    )
    primary_assignments = _count(
        db,
        select(func.count())
        .select_from(ParcelZoningAssignment)
        .join(Parcel, Parcel.id == ParcelZoningAssignment.parcel_id)
        .where(*assignment_filter)
        .where(ParcelZoningAssignment.is_primary.is_(True)),
    )

    return {
        "active_assignment_count": total_assignments,
        "assigned_parcel_count": assigned_parcels,
        "multi_zone_parcel_count": multi_zone_parcels,
        "multi_zone_parcel_rate_pct": _rate(multi_zone_parcels, assigned_parcels),
        "primary_assignment_count": primary_assignments,
    }


def collect_development_application_summary(db: Session, jurisdiction_id: uuid.UUID) -> dict[str, Any]:
    total = _count(
        db,
        select(func.count())
        .select_from(DevelopmentApplication)
        .where(DevelopmentApplication.jurisdiction_id == jurisdiction_id),
    )
    with_geom = _count(
        db,
        select(func.count())
        .select_from(DevelopmentApplication)
        .where(DevelopmentApplication.jurisdiction_id == jurisdiction_id)
        .where(DevelopmentApplication.geom.is_not(None)),
    )
    with_parcel = _count(
        db,
        select(func.count())
        .select_from(DevelopmentApplication)
        .where(DevelopmentApplication.jurisdiction_id == jurisdiction_id)
        .where(DevelopmentApplication.parcel_id.is_not(None)),
    )
    with_source_url = _count(
        db,
        select(func.count())
        .select_from(DevelopmentApplication)
        .where(DevelopmentApplication.jurisdiction_id == jurisdiction_id)
        .where(DevelopmentApplication.source_url.is_not(None))
        .where(DevelopmentApplication.source_url != ""),
    )
    with_decision = _count(
        db,
        select(func.count())
        .select_from(DevelopmentApplication)
        .where(DevelopmentApplication.jurisdiction_id == jurisdiction_id)
        .where(DevelopmentApplication.decision.is_not(None))
        .where(DevelopmentApplication.decision != ""),
    )
    decision_rows = db.execute(
        select(DevelopmentApplication.decision, func.count())
        .where(DevelopmentApplication.jurisdiction_id == jurisdiction_id)
        .group_by(DevelopmentApplication.decision)
        .order_by(DevelopmentApplication.decision)
    ).all()

    return {
        "count": total,
        "with_geom": with_geom,
        "with_geom_rate_pct": _rate(with_geom, total),
        "linked_to_parcel": with_parcel,
        "linked_to_parcel_rate_pct": _rate(with_parcel, total),
        "with_source_url": with_source_url,
        "with_source_url_rate_pct": _rate(with_source_url, total),
        "with_decision": with_decision,
        "with_decision_rate_pct": _rate(with_decision, total),
        "decision_distribution": {
            (decision or "null"): int(count) for decision, count in decision_rows
        },
    }


def collect_policy_summary(db: Session, jurisdiction_id: uuid.UUID) -> dict[str, Any]:
    clause_subquery = (
        select(
            PolicyClause.needs_review.label("needs_review"),
            PolicyClause.confidence.label("confidence"),
        )
        .join(PolicyVersion, PolicyVersion.id == PolicyClause.policy_version_id)
        .join(PolicyDocument, PolicyDocument.id == PolicyVersion.document_id)
        .where(PolicyDocument.jurisdiction_id == jurisdiction_id)
    ).subquery()

    active_versions = _count(
        db,
        select(func.count())
        .select_from(PolicyVersion)
        .join(PolicyDocument, PolicyDocument.id == PolicyVersion.document_id)
        .where(PolicyDocument.jurisdiction_id == jurisdiction_id)
        .where(PolicyVersion.is_active.is_(True)),
    )
    clause_count = _count(db, select(func.count()).select_from(clause_subquery))
    clauses_needing_review = _count(
        db,
        select(func.count()).select_from(clause_subquery).where(clause_subquery.c.needs_review.is_(True)),
    )
    confidence_avg = db.execute(select(func.avg(clause_subquery.c.confidence))).scalar()
    rules_with_zone_filter = _count(
        db,
        select(func.count())
        .select_from(PolicyApplicabilityRule)
        .where(PolicyApplicabilityRule.jurisdiction_id == jurisdiction_id)
        .where(func.coalesce(func.cardinality(PolicyApplicabilityRule.zone_filter), 0) > 0),
    )
    rules_with_use_filter = _count(
        db,
        select(func.count())
        .select_from(PolicyApplicabilityRule)
        .where(PolicyApplicabilityRule.jurisdiction_id == jurisdiction_id)
        .where(func.coalesce(func.cardinality(PolicyApplicabilityRule.use_filter), 0) > 0),
    )
    rules_with_geometry_filter = _count(
        db,
        select(func.count())
        .select_from(PolicyApplicabilityRule)
        .where(PolicyApplicabilityRule.jurisdiction_id == jurisdiction_id)
        .where(PolicyApplicabilityRule.geometry_filter.is_not(None)),
    )

    return {
        "active_version_count": active_versions,
        "clause_count": clause_count,
        "clauses_needing_review": clauses_needing_review,
        "clauses_needing_review_rate_pct": _rate(clauses_needing_review, clause_count),
        "confidence_avg": None if confidence_avg is None else round(float(confidence_avg), 4),
        "rules_with_zone_filter": rules_with_zone_filter,
        "rules_with_use_filter": rules_with_use_filter,
        "rules_with_geometry_filter": rules_with_geometry_filter,
    }


def _get_active_zoning_assignment_count(
    db: Session,
    parcel_id: uuid.UUID,
    active_zoning_snapshot_ids: list[uuid.UUID],
) -> int:
    filters = [ParcelZoningAssignment.parcel_id == parcel_id]
    if active_zoning_snapshot_ids:
        filters.append(ParcelZoningAssignment.source_snapshot_id.in_(list(active_zoning_snapshot_ids)))
    return _count(db, select(func.count()).select_from(ParcelZoningAssignment).where(*filters))


def build_benchmark_actual_payload(
    parcel: Parcel,
    zoning_analysis: ZoningAnalysis,
    overlay_response: ParcelOverlaysResponse,
    policy_stack: PolicyStackResponse,
) -> dict[str, Any]:
    return {
        "parcel": {
            "address": parcel.address,
            "pin": parcel.pin,
        },
        "zoning": {
            "zone_code": parcel.zone_code,
            "zone_string": zoning_analysis.zone_string,
            "category": zoning_analysis.components.category if zoning_analysis.components else None,
            "max_height_m": zoning_analysis.standards.max_height_m if zoning_analysis.standards else None,
            "max_storeys": zoning_analysis.standards.max_storeys if zoning_analysis.standards else None,
            "max_fsi": zoning_analysis.standards.max_fsi if zoning_analysis.standards else None,
            "overlay_layers": _sorted_unique([overlay.layer_type for overlay in overlay_response.overlays]),
            "warnings": list(zoning_analysis.warnings),
        },
        "policy_stack": {
            "documents": _sorted_unique([entry.document_title for entry in policy_stack.applicable_policies]),
            "sections": _sorted_unique([entry.section_ref for entry in policy_stack.applicable_policies]),
        },
    }


def run_benchmark_suite(
    db: Session,
    jurisdiction_id: uuid.UUID,
    fixture_path: str | Path,
) -> dict[str, Any]:
    fixture = Path(fixture_path)
    cases = load_toronto_core_benchmarks(fixture)
    active_parcel_snapshot_ids = list_active_snapshot_ids_sync(db, "parcel_base", jurisdiction_id=jurisdiction_id)
    active_zoning_snapshot_ids = list_active_snapshot_ids_sync(db, "zoning_geometry", jurisdiction_id=jurisdiction_id)

    benchmark_results = []
    case_rows: list[dict[str, Any]] = []

    for case in cases:
        parcel = None
        actual: dict[str, Any] = {}
        overlay_count = 0
        warning_count = 0
        policy_document_count = 0
        error_message = None

        try:
            parcel = resolve_active_parcel_by_address_sync(
                db,
                case.address_input,
                jurisdiction_id=jurisdiction_id,
                active_snapshot_ids=active_parcel_snapshot_ids,
            )
            if parcel is not None:
                overlay_response = get_parcel_overlays_response_sync(db, parcel)
                zoning_analysis = build_zoning_analysis(
                    parcel,
                    overlay_data=[overlay.model_dump() for overlay in overlay_response.overlays],
                    zoning_assignment_count=_get_active_zoning_assignment_count(
                        db,
                        parcel.id,
                        active_zoning_snapshot_ids,
                    ),
                )
                policy_stack = get_policy_stack_response_sync(db, parcel)
                actual = build_benchmark_actual_payload(parcel, zoning_analysis, overlay_response, policy_stack)
                overlay_count = len(overlay_response.overlays)
                warning_count = len(zoning_analysis.warnings)
                policy_document_count = len(actual.get("policy_stack", {}).get("documents", []))
        except Exception as exc:  # pragma: no cover - defensive audit behavior
            error_message = str(exc)

        result = evaluate_core_benchmark_case(case, actual)
        benchmark_results.append(result)
        case_rows.append(
            {
                "benchmark_id": case.benchmark_id,
                "verification_status": case.verification_status,
                "address_input": case.address_input,
                "resolved": parcel is not None,
                "parcel_address": parcel.address if parcel is not None else None,
                "zone_code": actual.get("zoning", {}).get("zone_code"),
                "zone_category": actual.get("zoning", {}).get("category"),
                "policy_document_count": policy_document_count,
                "overlay_count": overlay_count,
                "warning_count": warning_count,
                "status": result.status,
                "passed_checks": result.passed_checks,
                "total_checks": result.total_checks,
                "failures": list(result.failures),
                "error": error_message,
            }
        )

    resolved_count = sum(1 for row in case_rows if row["resolved"])
    with_zone_code = sum(1 for row in case_rows if row["zone_code"])
    with_policy_documents = sum(1 for row in case_rows if row["policy_document_count"] > 0)
    with_overlays = sum(1 for row in case_rows if row["overlay_count"] > 0)
    with_warnings = sum(1 for row in case_rows if row["warning_count"] > 0)

    return {
        "fixture_path": str(fixture),
        "verified_summary": summarize_benchmark_results(benchmark_results),
        "candidate_summary": {
            "fixture_case_count": len(cases),
            "verified_case_count": sum(1 for case in cases if case.verification_status == "verified"),
            "template_case_count": sum(1 for case in cases if case.verification_status != "verified"),
            "resolved_parcel_count": resolved_count,
            "resolved_parcel_rate_pct": _rate(resolved_count, len(cases)),
            "cases_with_zone_code": with_zone_code,
            "cases_with_zone_code_rate_pct": _rate(with_zone_code, len(cases)),
            "cases_with_policy_documents": with_policy_documents,
            "cases_with_policy_documents_rate_pct": _rate(with_policy_documents, len(cases)),
            "cases_with_overlays": with_overlays,
            "cases_with_overlays_rate_pct": _rate(with_overlays, len(cases)),
            "cases_with_warnings": with_warnings,
            "cases_with_warnings_rate_pct": _rate(with_warnings, len(cases)),
            "unresolved_benchmark_ids": [row["benchmark_id"] for row in case_rows if not row["resolved"]],
        },
        "results": case_rows,
    }


def build_audit_report(db: Session, fixture_path: str | Path = DEFAULT_FIXTURE_PATH) -> dict[str, Any]:
    jurisdiction = get_toronto_jurisdiction(db)
    active_parcel_snapshot_ids = list_active_snapshot_ids_sync(db, "parcel_base", jurisdiction_id=jurisdiction.id)
    active_zoning_snapshot_ids = list_active_snapshot_ids_sync(db, "zoning_geometry", jurisdiction_id=jurisdiction.id)

    return {
        "jurisdiction": {
            "id": str(jurisdiction.id),
            "name": jurisdiction.name,
            "province": jurisdiction.province,
            "country": jurisdiction.country,
        },
        "active_snapshots": {
            "counts_by_type": collect_active_snapshot_counts(db, jurisdiction.id),
            "parcel_base_snapshot_count": len(active_parcel_snapshot_ids),
            "zoning_snapshot_count": len(active_zoning_snapshot_ids),
        },
        "row_counts": collect_row_counts(db, jurisdiction.id),
        "coverage": {
            "parcels": collect_parcel_coverage(db, jurisdiction.id, active_parcel_snapshot_ids),
            "zoning": collect_zoning_summary(db, jurisdiction.id, active_zoning_snapshot_ids),
            "development_applications": collect_development_application_summary(db, jurisdiction.id),
            "policies": collect_policy_summary(db, jurisdiction.id),
        },
        "benchmarks": run_benchmark_suite(db, jurisdiction.id, fixture_path),
    }


def render_text_report(report: dict[str, Any]) -> str:
    lines = [
        "Toronto Seed Audit",
        f"Jurisdiction: {report['jurisdiction']['name']} ({report['jurisdiction']['province']}, {report['jurisdiction']['country']})",
        "",
        "Row counts:",
    ]
    for key, value in report["row_counts"].items():
        lines.append(f"  {key}: {value:,}")

    lines.extend(
        [
            "",
            "Coverage:",
            f"  active parcels: {report['coverage']['parcels']['active_parcel_count']:,}",
            (
                "  parcel coverage: "
                f"address {report['coverage']['parcels']['with_address_rate_pct']:.2f}% | "
                f"zone_code {report['coverage']['parcels']['with_zone_code_rate_pct']:.2f}% | "
                f"lot_area {report['coverage']['parcels']['with_lot_area_rate_pct']:.2f}% | "
                f"frontage {report['coverage']['parcels']['with_lot_frontage_rate_pct']:.2f}% | "
                f"depth {report['coverage']['parcels']['with_lot_depth_rate_pct']:.2f}% | "
                f"current_use {report['coverage']['parcels']['with_current_use_rate_pct']:.2f}%"
            ),
            (
                "  zoning coverage: "
                f"assigned parcels {report['coverage']['zoning']['assigned_parcel_count']:,} | "
                f"multi-zone parcels {report['coverage']['zoning']['multi_zone_parcel_count']:,} "
                f"({report['coverage']['zoning']['multi_zone_parcel_rate_pct']:.2f}%)"
            ),
            (
                "  development applications: "
                f"count {report['coverage']['development_applications']['count']:,} | "
                f"with geometry {report['coverage']['development_applications']['with_geom_rate_pct']:.2f}% | "
                f"linked to parcel {report['coverage']['development_applications']['linked_to_parcel_rate_pct']:.2f}% | "
                f"with decision {report['coverage']['development_applications']['with_decision_rate_pct']:.2f}%"
            ),
            (
                "  policy coverage: "
                f"active versions {report['coverage']['policies']['active_version_count']:,} | "
                f"clauses {report['coverage']['policies']['clause_count']:,} | "
                f"zone-filtered rules {report['coverage']['policies']['rules_with_zone_filter']:,} | "
                f"geometry-filtered rules {report['coverage']['policies']['rules_with_geometry_filter']:,}"
            ),
            "",
            "Benchmarks:",
            (
                "  verified summary: "
                f"cases {report['benchmarks']['verified_summary']['case_count']:,} | "
                f"skipped templates {report['benchmarks']['verified_summary']['skipped_case_count']:,} | "
                f"case pass rate {report['benchmarks']['verified_summary']['pass_rate'] * 100:.2f}% | "
                f"check pass rate {report['benchmarks']['verified_summary']['check_pass_rate'] * 100:.2f}%"
            ),
            (
                "  candidate resolution: "
                f"resolved {report['benchmarks']['candidate_summary']['resolved_parcel_count']:,}/"
                f"{report['benchmarks']['candidate_summary']['fixture_case_count']:,} "
                f"({report['benchmarks']['candidate_summary']['resolved_parcel_rate_pct']:.2f}%) | "
                f"with zone_code {report['benchmarks']['candidate_summary']['cases_with_zone_code']:,} | "
                f"with policy documents {report['benchmarks']['candidate_summary']['cases_with_policy_documents']:,} | "
                f"with overlays {report['benchmarks']['candidate_summary']['cases_with_overlays']:,}"
            ),
        ]
    )

    unresolved = report["benchmarks"]["candidate_summary"]["unresolved_benchmark_ids"]
    if unresolved:
        lines.append(f"  unresolved benchmark ids: {', '.join(unresolved)}")

    lines.append("")
    lines.append("Benchmark results:")
    for row in report["benchmarks"]["results"]:
        label = f"{row['benchmark_id']} [{row['verification_status']}]"
        outcome = (
            f"resolved={row['resolved']} status={row['status']} "
            f"zone={row['zone_code'] or 'n/a'} policy_docs={row['policy_document_count']} "
            f"overlays={row['overlay_count']} warnings={row['warning_count']}"
        )
        if row["error"]:
            outcome = f"{outcome} error={row['error']}"
        lines.append(f"  {label}: {outcome}")

    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the current Toronto seed state and benchmark coverage.")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help="Path to the Toronto benchmark fixture JSON.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the audit report as JSON instead of plain text.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_stream = sys.stderr if args.json else sys.stdout
    print(f"Database target: {redact_connection_url(settings.DATABASE_URL_SYNC)}", file=output_stream)
    checks = run_preflight_checks(required_paths=[args.fixture])
    print(render_preflight_checks(checks), file=output_stream)
    try:
        raise_for_failed_checks(checks)
    except RuntimeError as exc:
        raise SystemExit(f"Preflight failed: {exc}") from exc
    db = get_sync_db()
    try:
        report = build_audit_report(db, fixture_path=args.fixture)
    finally:
        db.close()

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text_report(report))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
