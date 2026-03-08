"""Design version control service — branching, committing, compliance."""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design_version import DesignBranch, DesignVersion
from app.models.geospatial import Parcel
from app.models.tenant import Project

logger = structlog.get_logger()


async def create_branch(
    db: AsyncSession,
    project_id: uuid.UUID,
    name: str,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    from_version_id: uuid.UUID | None = None,
) -> DesignBranch:
    branch = DesignBranch(
        project_id=project_id,
        organization_id=organization_id,
        name=name,
        created_by=user_id,
    )
    db.add(branch)
    await db.flush()

    # If forking from an existing version, copy it as v1 on the new branch
    if from_version_id:
        result = await db.execute(
            select(DesignVersion).where(DesignVersion.id == from_version_id)
        )
        source = result.scalar_one_or_none()
        if source:
            version = DesignVersion(
                branch_id=branch.id,
                parent_version_id=from_version_id,
                version_number=1,
                floor_plans=source.floor_plans,
                model_params=source.model_params,
                compliance_status=source.compliance_status,
                compliance_details=source.compliance_details,
                variance_items=source.variance_items,
                blocking_issues=source.blocking_issues,
                message=f"Branched from version {source.version_number}",
                change_summary=None,
                created_by=user_id,
            )
            db.add(version)
            await db.flush()

    return branch


async def list_branches(db: AsyncSession, project_id: uuid.UUID) -> list[DesignBranch]:
    result = await db.execute(
        select(DesignBranch)
        .where(DesignBranch.project_id == project_id)
        .order_by(DesignBranch.created_at)
    )
    return list(result.scalars().all())


async def delete_branch(db: AsyncSession, branch_id: uuid.UUID) -> None:
    await db.execute(
        delete(DesignVersion).where(DesignVersion.branch_id == branch_id)
    )
    await db.execute(
        delete(DesignBranch).where(DesignBranch.id == branch_id)
    )
    await db.flush()


async def commit_version(
    db: AsyncSession,
    branch_id: uuid.UUID,
    floor_plans: dict | None,
    model_params: dict | None,
    message: str,
    user_id: uuid.UUID,
    parcel_id: uuid.UUID | None = None,
) -> DesignVersion:
    # Get next version number
    result = await db.execute(
        select(func.coalesce(func.max(DesignVersion.version_number), 0))
        .where(DesignVersion.branch_id == branch_id)
    )
    next_num = result.scalar() + 1

    # Get parent version (latest on branch)
    parent = await get_latest(db, branch_id)
    parent_id = parent.id if parent else None

    # Look up project asset_type via the branch
    asset_type = "building"
    branch_result = await db.execute(
        select(DesignBranch).where(DesignBranch.id == branch_id)
    )
    branch = branch_result.scalar_one_or_none()
    if branch:
        proj_result = await db.execute(
            select(Project).where(Project.id == branch.project_id)
        )
        project = proj_result.scalar_one_or_none()
        if project:
            asset_type = project.asset_type

    # Compute compliance if parcel_id provided
    compliance = await compute_compliance(db, floor_plans, model_params, parcel_id, asset_type=asset_type)

    # Compute change summary
    change_summary = _compute_change_summary(parent, floor_plans, model_params)

    version = DesignVersion(
        branch_id=branch_id,
        parent_version_id=parent_id,
        version_number=next_num,
        floor_plans=floor_plans,
        model_params=model_params,
        compliance_status=compliance.get("status", "unknown"),
        compliance_details=compliance.get("details"),
        variance_items=compliance.get("variance_items"),
        blocking_issues=compliance.get("blocking_issues"),
        message=message,
        change_summary=change_summary,
        created_by=user_id,
    )
    db.add(version)
    await db.flush()

    logger.info("design_version.committed", branch_id=str(branch_id), version=next_num)
    return version


async def get_version(db: AsyncSession, version_id: uuid.UUID) -> DesignVersion | None:
    result = await db.execute(
        select(DesignVersion).where(DesignVersion.id == version_id)
    )
    return result.scalar_one_or_none()


async def list_versions(db: AsyncSession, branch_id: uuid.UUID) -> list[DesignVersion]:
    result = await db.execute(
        select(DesignVersion)
        .where(DesignVersion.branch_id == branch_id)
        .order_by(DesignVersion.version_number.desc())
    )
    return list(result.scalars().all())


async def get_latest(db: AsyncSession, branch_id: uuid.UUID) -> DesignVersion | None:
    result = await db.execute(
        select(DesignVersion)
        .where(DesignVersion.branch_id == branch_id)
        .order_by(DesignVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _compliance_status(proposed: float, maximum: float) -> str:
    """Determine compliance status: ok, variance (<=115%), or rezone (>115%)."""
    if maximum <= 0:
        return "ok"
    if proposed <= maximum:
        return "ok"
    if proposed <= maximum * 1.15:
        return "variance"
    return "rezone"


async def compute_compliance(
    db: AsyncSession,
    floor_plans: dict | None,
    model_params: dict | None,
    parcel_id: uuid.UUID | None,
    asset_type: str = "building",
) -> dict:
    """Compute compliance of design against parcel's zoning standards."""
    if not model_params:
        return {"status": "unknown", "details": {}, "variance_items": [], "blocking_issues": []}

    # Dispatch by asset_type for infrastructure
    if asset_type == "pipeline":
        from dataclasses import asdict
        from app.services.infrastructure_compliance import check_pipeline_compliance
        pipe_type = model_params.get("pipe_type", "water_main")
        result = check_pipeline_compliance(pipe_type, model_params)
        return {
            "status": "as_of_right" if result.overall_compliant else "needs_variance",
            "details": {r.parameter: {"permitted": r.permitted_value, "proposed": r.proposed_value, "status": "ok" if r.compliant else "variance"} for r in result.rules},
            "variance_items": [r.note or r.parameter for r in result.variances_needed],
            "blocking_issues": [],
        }

    if asset_type == "bridge":
        from dataclasses import asdict
        from app.services.infrastructure_compliance import check_bridge_compliance
        bridge_type = model_params.get("bridge_type", "road_bridge")
        result = check_bridge_compliance(bridge_type, model_params)
        return {
            "status": "as_of_right" if result.overall_compliant else "needs_variance",
            "details": {r.parameter: {"permitted": r.permitted_value, "proposed": r.proposed_value, "status": "ok" if r.compliant else "variance"} for r in result.rules},
            "variance_items": [r.note or r.parameter for r in result.variances_needed],
            "blocking_issues": [],
        }

    # Default: building compliance
    if not parcel_id:
        return {"status": "unknown", "details": {}, "variance_items": [], "blocking_issues": []}

    # Look up parcel and its zoning
    result = await db.execute(select(Parcel).where(Parcel.id == parcel_id))
    parcel = result.scalar_one_or_none()
    if not parcel or not parcel.zone_code:
        return {"status": "unknown", "details": {}, "variance_items": [], "blocking_issues": []}

    from app.services.zoning_parser import get_zone_standards, parse_zone_string

    try:
        components = parse_zone_string(parcel.zone_code)
        standards = get_zone_standards(components)
    except ValueError:
        return {"status": "unknown", "details": {}, "variance_items": [], "blocking_issues": []}

    # Extract proposed values from model_params
    proposed_height = model_params.get("height_m", 0)
    proposed_storeys = model_params.get("storeys", 0)
    proposed_coverage = model_params.get("footprint_coverage", 0) * 100  # convert to %

    # Compute FSI if lot area available
    proposed_fsi = 0
    lot_area = parcel.lot_area_m2 or 0
    if lot_area > 0 and floor_plans:
        total_floor_area = 0
        for fp_data in (floor_plans.get("floor_plans") or []):
            for room in fp_data.get("rooms", []):
                total_floor_area += room.get("area_m2", 0)
        if total_floor_area > 0:
            proposed_fsi = total_floor_area / lot_area
        else:
            # Estimate from coverage and storeys
            proposed_fsi = (proposed_coverage / 100) * proposed_storeys

    details = {}
    variance_items = []
    blocking_issues = []

    # Height check
    max_h = standards.max_height_m or 0
    if max_h > 0:
        h_status = _compliance_status(proposed_height, max_h)
        details["height"] = {"permitted": max_h, "proposed": proposed_height, "status": h_status}
        if h_status == "variance":
            variance_items.append(
                f"Height exceeds {max_h}m by {round(proposed_height - max_h, 1)}m"
            )
        elif h_status == "rezone":
            variance_items.append(
                f"Height {proposed_height}m significantly exceeds {max_h}m — rezoning likely required"
            )

    # Storeys check
    max_s = standards.max_storeys or 0
    if max_s > 0:
        s_status = _compliance_status(proposed_storeys, max_s)
        details["storeys"] = {"permitted": max_s, "proposed": proposed_storeys, "status": s_status}
        if s_status in ("variance", "rezone"):
            variance_items.append(
                f"Storeys ({proposed_storeys}) exceeds maximum {max_s}"
            )

    # Lot coverage check
    max_cov = standards.max_lot_coverage_pct or 0
    if max_cov > 0:
        cov_status = _compliance_status(proposed_coverage, max_cov)
        details["lot_coverage"] = {"permitted": max_cov, "proposed": round(proposed_coverage, 1), "status": cov_status}
        if cov_status in ("variance", "rezone"):
            variance_items.append(
                f"Lot coverage {round(proposed_coverage, 1)}% exceeds {max_cov}%"
            )

    # FSI check
    max_fsi = standards.max_fsi or 0
    if max_fsi > 0 and proposed_fsi > 0:
        fsi_status = _compliance_status(proposed_fsi, max_fsi)
        details["fsi"] = {"permitted": max_fsi, "proposed": round(proposed_fsi, 2), "status": fsi_status}
        if fsi_status in ("variance", "rezone"):
            variance_items.append(
                f"FSI {round(proposed_fsi, 2)} exceeds {max_fsi}"
            )

    # Determine overall status
    statuses = [d.get("status", "ok") for d in details.values()]
    if "rezone" in statuses:
        overall = "needs_rezoning"
    elif "variance" in statuses:
        overall = "needs_variance"
    elif all(s == "ok" for s in statuses):
        overall = "as_of_right"
    else:
        overall = "unknown"

    # Check for blocking issues (OBC hard constraints)
    if proposed_height > 0 and max_h > 0 and proposed_height > max_h * 1.5:
        blocking_issues.append(
            f"Height {proposed_height}m is >150% of permitted {max_h}m — may trigger Part 3 OBC requirements"
        )

    if blocking_issues:
        overall = "blocked"

    # Interior compliance check (OBC Part 9)
    interior_compliance = None
    if floor_plans:
        from dataclasses import asdict
        from app.services.interior_compliance import check_interior_compliance

        floor_plan_list = floor_plans.get("floor_plans") or []
        all_interior_results = []
        for fp_data in floor_plan_list:
            result = check_interior_compliance(
                floor_plan=fp_data,
                ceiling_height_m=model_params.get("ceiling_height_m", 2.7) if model_params else 2.7,
            )
            all_interior_results.append({
                "rules": [asdict(r) for r in result.rules],
                "errors": result.errors,
                "warnings": result.warnings,
                "overall_compliant": result.overall_compliant,
                "load_bearing_warnings": result.load_bearing_warnings,
            })
            # Promote interior blockers to top-level blocking_issues
            for rule in result.rules:
                if rule.severity == "blocker" and not rule.compliant:
                    blocking_issues.append(f"OBC {rule.obc_section}: {rule.note}")
        interior_compliance = all_interior_results

    if blocking_issues:
        overall = "blocked"

    return {
        "status": overall,
        "details": details,
        "variance_items": variance_items,
        "blocking_issues": blocking_issues,
        "interior_compliance": interior_compliance,
    }


def _compute_change_summary(
    parent: DesignVersion | None,
    floor_plans: dict | None,
    model_params: dict | None,
) -> str | None:
    """Generate a human-readable summary of what changed."""
    if not parent:
        return "Initial version"

    changes = []
    old_params = parent.model_params or {}
    new_params = model_params or {}

    for key in ("height_m", "storeys", "footprint_coverage", "typology", "setback_m", "podium_storeys"):
        old_val = old_params.get(key)
        new_val = new_params.get(key)
        if old_val != new_val and new_val is not None:
            label = key.replace("_", " ").title()
            if old_val is not None:
                changes.append(f"{label}: {old_val} → {new_val}")
            else:
                changes.append(f"{label}: {new_val}")

    # Compare floor counts
    old_floors = len((parent.floor_plans or {}).get("floor_plans", []))
    new_floors = len((floor_plans or {}).get("floor_plans", []))
    if old_floors != new_floors:
        changes.append(f"Floor count: {old_floors} → {new_floors}")

    return "; ".join(changes) if changes else None
