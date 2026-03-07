import structlog
from datetime import datetime, timezone

from sqlalchemy import func, or_

from app.database import get_sync_db
from app.models.entitlement import BuildingPermit, DevelopmentApplication, EntitlementResult, PrecedentMatch, PrecedentSearch
from app.models.simulation import LayoutRun, Massing
from app.services.precedent import normalize_application_type, score_precedent_match
from app.services.thin_slice_runtime import resolve_project_context
from app.worker import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, name="app.tasks.entitlement.run_entitlement_check")
def run_entitlement_check(self, job_id: str, scenario_id: str, params: dict | None = None):
    """Run entitlement / compliance check for a scenario.

    TODO: Implement entitlement engine:
    1. Load scenario massing and policy stack
    2. Compare each metric against policy rules
    3. Classify pass/fail/variance for each rule
    4. Score overall approval likelihood
    5. Store results and update job status
    """
    logger.info("entitlement.started", job_id=job_id, scenario_id=scenario_id)
    db = get_sync_db()
    try:
        result = db.query(EntitlementResult).filter(EntitlementResult.id == job_id).one()
        massing = (
            db.query(Massing)
            .filter(Massing.scenario_run_id == scenario_id)
            .order_by(Massing.created_at.desc())
            .first()
        )
        layout = (
            db.query(LayoutRun)
            .join(Massing, LayoutRun.massing_id == Massing.id)
            .filter(Massing.scenario_run_id == scenario_id, LayoutRun.status == "completed")
            .order_by(LayoutRun.created_at.desc())
            .first()
        )
        if massing is None or not massing.summary_json:
            raise ValueError("No completed massing output found for entitlement analysis")

        warnings = list((massing.compliance_json or {}).get("warnings", []))
        layout_result = layout.result_json if layout and layout.result_json else {}
        total_units = int(layout_result.get("total_units", 0))
        parking_required = float(layout_result.get("parking_required", 0))
        amenity_required_m2 = float(layout_result.get("amenity_required_m2", 0))

        checks = [
            {
                "rule": "template_assumptions",
                "status": "review" if warnings else "pass",
                "details": warnings,
            },
            {
                "rule": "unit_program",
                "status": "pass" if total_units > 0 else "review",
                "details": {"total_units": total_units},
            },
            {
                "rule": "parking",
                "status": "pass" if parking_required >= 0 else "fail",
                "details": {"parking_required": parking_required},
            },
            {
                "rule": "amenity",
                "status": "pass" if amenity_required_m2 >= 0 else "fail",
                "details": {"amenity_required_m2": amenity_required_m2},
            },
        ]
        overall = "review" if warnings or total_units == 0 else "pass"
        score = 0.7 if overall == "pass" else 0.55

        result.overall_compliance = overall
        result.result_json = {"checks": checks, "warnings": warnings}
        result.score = score
        db.commit()

        logger.info("entitlement.completed", job_id=job_id, scenario_id=scenario_id, overall=overall)
        return {"job_id": job_id, "status": "completed", "result": result.result_json}
    except Exception as exc:
        db.rollback()
        try:
            result = db.query(EntitlementResult).filter(EntitlementResult.id == job_id).one()
            result.overall_compliance = "failed"
            result.result_json = {"error": str(exc)}
            db.commit()
        except Exception:
            db.rollback()
        logger.error("entitlement.failed", job_id=job_id, scenario_id=scenario_id, error=str(exc))
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.entitlement.run_precedent_search")
def run_precedent_search(self, job_id: str, scenario_id: str, params: dict | None = None):
    """Search for comparable precedent development applications.

    TODO: Implement precedent retrieval:
    1. Load scenario location and parameters
    2. Find nearby applications with similar characteristics
    3. Rank by similarity (spatial, programmatic, zoning)
    4. Extract rationale summaries
    5. Store results and update job status
    """
    logger.info("precedent_search.started", job_id=job_id, scenario_id=scenario_id)
    db = get_sync_db()
    try:
        search = db.query(PrecedentSearch).filter(PrecedentSearch.id == job_id).one()
        search.status = "running"
        search.started_at = datetime.now(timezone.utc)
        db.commit()

        context = resolve_project_context(db, scenario_id)
        radius_m = float((params or {}).get("radius_m") or 500.0)
        max_results = int((params or {}).get("max_results") or 20)
        requested_types = (params or {}).get("application_types") or []
        normalized_requested_types = {normalize_application_type(app_type) for app_type in requested_types}
        search_params = (params or {}).get("search_params") or {}
        massing = (
            db.query(Massing)
            .filter(Massing.scenario_run_id == scenario_id)
            .order_by(Massing.created_at.desc())
            .first()
        )
        layout = (
            db.query(LayoutRun)
            .join(Massing, LayoutRun.massing_id == Massing.id)
            .filter(Massing.scenario_run_id == scenario_id, LayoutRun.status == "completed")
            .order_by(LayoutRun.created_at.desc())
            .first()
        )
        scenario_metrics = {
            "application_type": search_params.get("application_type") or (requested_types[0] if requested_types else None),
            "height_m": search_params.get("height_m")
            or (massing.height_m if massing and massing.height_m is not None else (massing.summary_json or {}).get("height_m") if massing else None),
            "units": search_params.get("units")
            or (layout.total_units if layout and layout.total_units is not None else (layout.result_json or {}).get("total_units") if layout else None),
            "fsi": search_params.get("fsi")
            or (massing.fsi if massing and massing.fsi is not None else (massing.summary_json or {}).get("estimated_fsi") if massing else None),
        }

        distance_expr = func.ST_DistanceSphere(
            DevelopmentApplication.geom,
            func.ST_Centroid(context.parcel.geom),
        ).label("distance_m")
        query = db.query(DevelopmentApplication, distance_expr).filter(
            or_(
                DevelopmentApplication.parcel_id == context.parcel.id,
                DevelopmentApplication.geom.isnot(None),
            )
        )

        candidates = []
        for application, distance_m in query.all():
            normalized_type = normalize_application_type(application.app_type)
            if normalized_requested_types and normalized_type not in normalized_requested_types:
                continue
            if application.parcel_id != context.parcel.id and distance_m is not None and float(distance_m) > radius_m:
                continue
            if application.parcel_id != context.parcel.id and distance_m is None:
                continue
            permit_count = (
                db.query(BuildingPermit)
                .filter(
                    or_(
                        BuildingPermit.development_application_id == application.id,
                        BuildingPermit.parcel_id == application.parcel_id,
                    )
                )
                .count()
            )
            distance_value = float(distance_m or 0.0)
            scoring = score_precedent_match(
                application,
                distance_value,
                scenario_metrics,
                permit_count=permit_count,
            )
            candidates.append(
                (
                    application,
                    {
                        "address": application.address,
                        "app_number": application.app_number,
                        "app_type": application.app_type,
                        "decision": application.decision,
                        "proposed_height_m": application.proposed_height_m,
                        "proposed_units": application.proposed_units,
                        "proposed_fsi": application.proposed_fsi,
                        "distance_m": round(distance_value, 2),
                        "permit_count": permit_count,
                        "score": scoring["score"],
                        "score_breakdown": scoring["breakdown"],
                    },
                )
            )

        candidates.sort(key=lambda item: (-item[1]["score"], item[1]["distance_m"]))
        db.query(PrecedentMatch).filter(PrecedentMatch.precedent_search_id == search.id).delete(synchronize_session=False)

        results_json: list[dict] = []
        for rank, (application, summary) in enumerate(candidates[:max_results], start=1):
            match = PrecedentMatch(
                precedent_search_id=search.id,
                development_application_id=application.id,
                rank=rank,
                score=summary["score"],
                distance_m=summary["distance_m"],
                matched_permit_count=summary["permit_count"],
                score_breakdown_json=summary["score_breakdown"],
                summary_json={
                    "address": summary["address"],
                    "app_number": summary["app_number"],
                    "app_type": summary["app_type"],
                    "decision": summary["decision"],
                    "proposed_height_m": summary["proposed_height_m"],
                    "proposed_units": summary["proposed_units"],
                    "proposed_fsi": summary["proposed_fsi"],
                },
            )
            db.add(match)
            results_json.append(
                {
                    "rank": rank,
                    "development_application_id": str(application.id),
                    "score": summary["score"],
                    "distance_m": summary["distance_m"],
                    "matched_permit_count": summary["permit_count"],
                    "summary": match.summary_json,
                    "score_breakdown": summary["score_breakdown"],
                }
            )

        search.result_count = len(results_json)
        search.results_json = results_json
        search.status = "completed"
        search.error_message = None
        search.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("precedent_search.completed", job_id=job_id, scenario_id=scenario_id, result_count=len(results_json))
        return {"job_id": job_id, "status": "completed", "results": results_json}
    except Exception as exc:
        db.rollback()
        try:
            search = db.query(PrecedentSearch).filter(PrecedentSearch.id == job_id).one()
            search.status = "failed"
            search.error_message = str(exc)
            search.result_count = 0
            search.results_json = []
            search.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            db.rollback()
        logger.error("precedent_search.failed", job_id=job_id, scenario_id=scenario_id, error=str(exc))
        raise
    finally:
        db.close()
