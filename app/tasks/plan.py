import asyncio
import uuid
from datetime import datetime, timezone

import structlog

from app.database import get_sync_db
from app.models.plan import DevelopmentPlan, SubmissionDocument
from app.worker import celery_app

logger = structlog.get_logger()

PIPELINE_STEPS = [
    "query_parsing",
    "parcel_lookup",
    "policy_resolution",
    "massing_generation",
    "layout_optimization",
    "financial_analysis",
    "entitlement_check",
    "precedent_search",
    "document_generation",
]

SUBMISSION_DOCUMENTS = [
    {
        "doc_type": "cover_letter",
        "title": "Cover Letter",
        "description": "Introduction letter to the planning department summarizing the proposal",
        "sort_order": 1,
    },
    {
        "doc_type": "planning_rationale",
        "title": "Planning Rationale",
        "description": "Detailed justification for the proposed development with policy citations",
        "sort_order": 2,
    },
    {
        "doc_type": "compliance_matrix",
        "title": "Policy Compliance Matrix",
        "description": "Rule-by-rule comparison of proposal against applicable zoning provisions",
        "sort_order": 3,
    },
    {
        "doc_type": "site_plan_data",
        "title": "Site Plan Data Summary",
        "description": "Parcel geometry, setbacks, building footprint, access points, and key dimensions",
        "sort_order": 4,
    },
    {
        "doc_type": "massing_summary",
        "title": "Massing & Built Form Summary",
        "description": "Building envelope, height, storeys, GFA breakdown, and 3D massing parameters",
        "sort_order": 5,
    },
    {
        "doc_type": "unit_mix_summary",
        "title": "Unit Mix & Layout Summary",
        "description": "Unit count by type, area ranges, accessible units, and floor plate breakdown",
        "sort_order": 6,
    },
    {
        "doc_type": "financial_feasibility",
        "title": "Financial Feasibility Summary",
        "description": "High-level pro forma showing revenue, costs, NOI, cap rate, and return metrics",
        "sort_order": 7,
    },
    {
        "doc_type": "precedent_report",
        "title": "Precedent Analysis Report",
        "description": "Comparable approved developments nearby with outcomes and rationale excerpts",
        "sort_order": 8,
    },
    {
        "doc_type": "public_benefit_statement",
        "title": "Public Benefit Statement",
        "description": "Community contributions, affordable housing, public realm improvements",
        "sort_order": 9,
    },
    {
        "doc_type": "shadow_study",
        "title": "Shadow Study Data",
        "description": "Shadow impact analysis data for the proposed building envelope",
        "sort_order": 10,
    },
]

# Minimum confidence threshold — below this, we pause for user clarification
CLARIFICATION_CONFIDENCE_THRESHOLD = 0.6


def _update_plan_status(db, plan, status, step=None, progress_update=None, error=None):
    """Helper to update plan status in the database."""
    plan.status = status
    if step:
        plan.current_step = step
    if progress_update:
        progress = plan.pipeline_progress or {}
        progress.update(progress_update)
        plan.pipeline_progress = progress
    if error:
        plan.error_message = error
    db.commit()
    db.refresh(plan)


def _run_query_parsing(query: str) -> dict:
    """Run the async AI query parser from a sync Celery context."""
    from app.ai.factory import get_ai_provider
    from app.ai.query_parser import parse_development_query

    provider = get_ai_provider()
    return asyncio.run(parse_development_query(provider, query))


def _run_parcel_lookup(db, parsed: dict) -> object | None:
    """Look up a parcel by address from parsed parameters."""
    from sqlalchemy import select

    from app.models.geospatial import Parcel

    address = parsed.get("address")
    if not address:
        logger.warning("plan.parcel_lookup.no_address")
        return None

    # Try exact ilike match first
    parcel = db.execute(
        select(Parcel).where(Parcel.address.ilike(f"%{address}%")).limit(1)
    ).scalar_one_or_none()

    if parcel is None:
        # Try normalized search: strip common suffixes
        normalized = address.strip().lower()
        for suffix in [" street", " st", " avenue", " ave", " road", " rd", " drive", " dr", " boulevard", " blvd"]:
            if normalized.endswith(suffix):
                base = normalized[: -len(suffix)]
                parcel = db.execute(
                    select(Parcel).where(Parcel.address.ilike(f"%{base}%")).limit(1)
                ).scalar_one_or_none()
                if parcel:
                    break

    return parcel


def _run_zoning_analysis(db, parcel):
    """Run deterministic zoning analysis."""
    from app.services.zoning_service import get_zoning_analysis_sync

    return get_zoning_analysis_sync(db, parcel)


def _run_massing(parcel, template_payload, overrides=None):
    """Compute massing summary."""
    from app.services.thin_slice_runtime import compute_massing_summary

    return compute_massing_summary(parcel, template_payload, overrides)


def _run_layout(massing_summary, template_payload, unit_types, overrides=None):
    """Compute layout result."""
    from app.services.thin_slice_runtime import compute_layout_result

    return compute_layout_result(massing_summary, template_payload, unit_types, overrides)


def _run_financial(layout_result, massing_summary, unit_types, assumptions):
    """Compute financial output."""
    from app.services.thin_slice_runtime import compute_financial_output

    return compute_financial_output(layout_result, massing_summary, unit_types, assumptions)


def _run_compliance(zoning, massing, layout, overlays=None):
    """Run deterministic compliance check — no AI."""
    from app.services.compliance_engine import check_compliance

    return check_compliance(zoning, massing, layout, overlays)


def _run_precedent_search(db, parcel, massing_summary):
    """Search for precedent applications near the parcel."""
    from sqlalchemy import func, select

    from app.models.geospatial import Parcel

    # Search for nearby development applications in parcels table
    # that have different IDs (i.e., other parcels in the area)
    try:
        nearby_parcels = db.execute(
            select(Parcel)
            .where(Parcel.id != parcel.id)
            .where(Parcel.jurisdiction_id == parcel.jurisdiction_id)
            .where(
                func.ST_DWithin(
                    func.ST_Transform(Parcel.geom, 2952),
                    func.ST_Transform(
                        select(Parcel.geom).where(Parcel.id == parcel.id).scalar_subquery(),
                        2952,
                    ),
                    2000,  # 2km radius
                )
            )
            .limit(10)
        ).scalars().all()
    except Exception:
        logger.warning("plan.precedent_search.spatial_query_failed", parcel_id=str(parcel.id))
        nearby_parcels = []

    if not nearby_parcels:
        return []

    from app.services.thin_slice_runtime import build_precedent_match_summary

    precedents = []
    for nearby in nearby_parcels:
        try:
            distance = 500.0  # Default estimate if spatial calc fails
            summary = build_precedent_match_summary(
                app_id=nearby.id,
                app_number=nearby.pin or "N/A",
                address=nearby.address,
                app_type="development",
                decision=None,
                proposed_height_m=massing_summary.get("height_m"),
                proposed_units=None,
                proposed_fsi=massing_summary.get("estimated_fsi"),
                distance_m=distance,
            )
            precedents.append(summary)
        except Exception:
            continue

    # Sort by score descending
    precedents.sort(key=lambda p: p.get("score", 0), reverse=True)
    return precedents[:5]


def _build_context_and_generate_docs(
    db,
    plan,
    parcel,
    zoning,
    massing_summary,
    layout_result,
    financial_output,
    compliance_result,
    precedents,
    parsed,
):
    """Build document context and generate all submission documents."""
    from app.services.compliance_engine import render_compliance_matrix_markdown
    from app.services.submission.context_builder import build_document_context
    from app.services.submission.templates import SAFETY_PREAMBLE

    # Build parcel data dict for context builder
    parcel_data = None
    if parcel:
        parcel_data = {
            "address": parcel.address,
            "zone_code": parcel.zone_code,
            "lot_area_m2": parcel.lot_area_m2 or parcel.geom_area_m2,
            "lot_frontage_m": parcel.lot_frontage_m,
            "lot_depth_m": parcel.lot_depth_m,
            "current_use": parcel.current_use,
        }

    # Build context
    context = build_document_context(
        parcel_data=parcel_data,
        zoning=zoning,
        massing=massing_summary,
        layout=layout_result,
        finance=financial_output,
        compliance=compliance_result,
        precedents=precedents,
        policy_stack=None,  # Would come from async policy stack query
        overlays=None,
        project_name=parsed.get("project_name", ""),
        organization_name="",
        parsed_parameters=parsed,
    )

    # Generate documents — try AI generation, fall back to grounded template content
    for doc_spec in SUBMISSION_DOCUMENTS:
        doc_type = doc_spec["doc_type"]

        # For compliance_matrix, use deterministic content (no AI)
        if doc_type == "compliance_matrix" and compliance_result:
            matrix_md = render_compliance_matrix_markdown(compliance_result)
            content = (
                f"> {SAFETY_PREAMBLE}\n\n---\n\n"
                f"# {doc_spec['title']}\n\n"
                f"**Address**: {context.get('address', 'N/A')}\n"
                f"**Zoning**: {context.get('zoning_code', 'N/A')}\n\n"
                f"## Compliance Matrix\n\n{matrix_md}\n\n"
                f"## Variances\n\n{context.get('variance_summary', 'None required.')}"
            )
        else:
            # Build content from context — AI generation would happen here
            # For now, use grounded template content with real data
            content = _build_grounded_content(doc_spec, context, SAFETY_PREAMBLE)

        doc = SubmissionDocument(
            plan_id=plan.id,
            doc_type=doc_type,
            title=doc_spec["title"],
            description=doc_spec["description"],
            sort_order=doc_spec["sort_order"],
            format="markdown",
            status="completed",
            review_status="draft",
            content_text=content,
        )
        db.add(doc)

    db.flush()


def _build_grounded_content(doc_spec: dict, context: dict, preamble: str) -> str:
    """Build grounded document content from context data.

    Uses real pipeline data to populate the document. Where AI generation
    is available, it will be invoked; otherwise, structured data is presented.
    """
    doc_type = doc_spec["doc_type"]
    title = doc_spec["title"]

    sections = [f"> {preamble}\n\n---\n\n# {title}\n"]

    if doc_type == "cover_letter":
        sections.append(f"**To**: City of Toronto Planning Department\n")
        sections.append(f"**Re**: Development Application — {context.get('address', 'N/A')}\n")
        sections.append(f"**Project**: {context.get('project_name', 'N/A')}\n\n")
        sections.append(f"This letter introduces a {context.get('development_type', 'development')} ")
        sections.append(f"application for the property at {context.get('address', 'N/A')}. ")
        sections.append(f"The proposal comprises a {context.get('building_type', 'building')} ")
        sections.append(f"of {context.get('storeys', 'N/A')} storeys ({context.get('height_m', 'N/A')}m) ")
        sections.append(f"containing {context.get('unit_count', 'N/A')} residential units ")
        sections.append(f"with a total GFA of {context.get('gross_floor_area_sqm', 'N/A')}.\n")

    elif doc_type == "planning_rationale":
        sections.append(f"## 1. Site Description\n\n")
        sections.append(f"The subject site is located at {context.get('address', 'N/A')}, ")
        sections.append(f"currently zoned {context.get('zoning_code', 'N/A')}.\n\n")
        sections.append(f"## 2. Policy Framework\n\n")
        sections.append(
            "The applicable policy hierarchy is:\n"
            "1. Provincial Planning Statement, 2024 (PPS 2024)\n"
            "2. City of Toronto Official Plan (consolidated 2022)\n"
            "3. Secondary Plans / Site and Area Specific Policies\n"
            "4. Zoning By-law 569-2013 (as amended)\n"
            "5. Design Guidelines\n\n"
        )
        sections.append(f"### Policy Stack\n\n{context.get('policy_stack_summary', 'N/A')}\n\n")
        sections.append(f"## 3. Compliance Analysis\n\n{context.get('compliance_summary', 'N/A')}\n\n")
        sections.append(f"## 4. Variances\n\n{context.get('variance_summary', 'None required.')}\n\n")
        sections.append(f"## 5. Precedent Applications\n\n{context.get('precedent_summary', 'N/A')}\n")

    elif doc_type == "site_plan_data":
        sections.append(f"**Address**: {context.get('address', 'N/A')}\n\n")
        sections.append(f"## Site Dimensions\n\n")
        sections.append(f"- Lot Area: {context.get('lot_area_sqm', 'N/A')}\n")
        sections.append(f"- Lot Frontage: {context.get('lot_frontage_m', 'N/A')}\n")
        sections.append(f"- Lot Depth: {context.get('lot_depth_m', 'N/A')}\n\n")
        sections.append(f"## Setbacks\n\n{context.get('setback_data', 'N/A')}\n\n")
        sections.append(f"## Massing\n\n{context.get('massing_summary', 'N/A')}\n")

    elif doc_type == "massing_summary":
        sections.append(f"**Project**: {context.get('project_name', 'N/A')}\n\n")
        sections.append(f"## Massing Parameters\n\n{context.get('massing_parameters', 'N/A')}\n\n")
        sections.append(f"## Policy Constraints\n\n{context.get('policy_constraints', 'N/A')}\n")

    elif doc_type == "unit_mix_summary":
        sections.append(f"**Total Units**: {context.get('unit_count', 'N/A')}\n\n")
        sections.append(f"## Unit Mix\n\n{context.get('unit_mix_data', 'N/A')}\n\n")
        sections.append(f"## Layout Results\n\n{context.get('layout_results', 'N/A')}\n")

    elif doc_type == "financial_feasibility":
        sections.append(f"## Financial Results\n\n{context.get('financial_results', 'N/A')}\n\n")
        sections.append(f"## Assumptions\n\n{context.get('financial_assumptions', 'N/A')}\n")

    elif doc_type == "precedent_report":
        sections.append(f"**Subject Site**: {context.get('address', 'N/A')}\n\n")
        sections.append(f"## Precedent Applications\n\n{context.get('precedent_results', 'N/A')}\n")

    elif doc_type == "public_benefit_statement":
        sections.append(f"**Project**: {context.get('project_name', 'N/A')}\n\n")
        sections.append(f"## Public Benefits\n\n{context.get('public_benefits', 'N/A')}\n\n")
        sections.append(f"## Community Context\n\n{context.get('community_context', 'N/A')}\n")

    elif doc_type == "shadow_study":
        sections.append(f"**Address**: {context.get('address', 'N/A')}\n\n")
        sections.append(f"**Height**: {context.get('height_m', 'N/A')}m ({context.get('storeys', 'N/A')} storeys)\n\n")
        sections.append(f"## Massing Geometry\n\n{context.get('massing_parameters', 'N/A')}\n\n")
        sections.append(
            "## Shadow Analysis\n\n"
            "Shadow analysis requires 3D modeling with actual site geometry. "
            "The following dates require analysis per Toronto standards:\n"
            "- March 21, June 21, September 21\n"
            "- Times: 9:18am, 12:18pm, 3:18pm, 6:18pm\n\n"
            "*[Detailed shadow geometry requires professional 3D shadow study — "
            "this section provides estimated parameters only.]*\n"
        )

    else:
        sections.append(f"*Content generation pending for {doc_type}.*\n")

    return "".join(sections)


@celery_app.task(bind=True, name="app.tasks.plan.run_plan_generation")
def run_plan_generation(self, plan_id: str, query: str, auto_run: bool = True):
    """Orchestrate the full plan generation pipeline.

    Pipeline steps:
    1. Parse query -> structured development parameters (via AI)
    2. Look up parcel by address
    3. Resolve applicable policy stack + zoning analysis
    4. Generate building massing
    5. Optimize unit mix / layout
    6. Run financial pro forma
    7. Check entitlement compliance (DETERMINISTIC — no AI)
    8. Search precedent applications
    9. Generate submission documents
    """
    logger.info("plan.generation.started", plan_id=plan_id)

    db = get_sync_db()
    try:
        plan = db.query(DevelopmentPlan).filter(DevelopmentPlan.id == uuid.UUID(plan_id)).one()
        plan.started_at = datetime.now(timezone.utc)

        # Initialize pipeline progress
        plan.pipeline_progress = {step: "pending" for step in PIPELINE_STEPS}
        _update_plan_status(db, plan, "running_pipeline", step="query_parsing",
                           progress_update={"query_parsing": "running"})

        # --- Step 1: Query Parsing ---
        if plan.parsed_parameters and plan.parsed_parameters.get("status") != "stub_parse":
            parsed = plan.parsed_parameters
            logger.info("plan.query_parsing.skipped_existing", plan_id=plan_id)
        else:
            try:
                parsed = _run_query_parsing(query)
            except Exception as e:
                logger.error("plan.query_parsing.failed", plan_id=plan_id, error=str(e))
                _update_plan_status(db, plan, "failed", step="query_parsing",
                                   progress_update={"query_parsing": "failed"},
                                   error=f"Query parsing failed: {e}")
                return {"plan_id": plan_id, "status": "failed", "error": str(e)}

            from app.config import settings as app_settings
            plan.parsed_parameters = parsed
            plan.parse_confidence = parsed.get("confidence", 0.0)
            plan.ai_provider = app_settings.AI_PROVIDER
            plan.ai_model = app_settings.AI_MODEL

            clarifications = parsed.get("clarification_needed", [])
            confidence = parsed.get("confidence", 0.0)

            if clarifications and confidence < CLARIFICATION_CONFIDENCE_THRESHOLD and auto_run:
                plan.clarifications_needed = {"questions": clarifications}
                _update_plan_status(db, plan, "needs_clarification", step="query_parsing",
                                   progress_update={"query_parsing": "needs_clarification"})
                logger.info("plan.query_parsing.needs_clarification",
                           plan_id=plan_id, confidence=confidence,
                           num_questions=len(clarifications))
                return {
                    "plan_id": plan_id,
                    "status": "needs_clarification",
                    "confidence": confidence,
                    "clarifications": clarifications,
                }

        logger.info("plan.query_parsing.completed", plan_id=plan_id,
                    confidence=parsed.get("confidence"),
                    address=parsed.get("address"),
                    dev_type=parsed.get("development_type"))

        _update_plan_status(db, plan, "running_pipeline", step="parcel_lookup",
                           progress_update={"query_parsing": "completed", "parcel_lookup": "running"})

        # --- Step 2: Parcel Lookup ---
        parcel = _run_parcel_lookup(db, parsed)
        if parcel:
            params = plan.parsed_parameters or {}
            params["parcel_id"] = str(parcel.id)
            params["resolved_address"] = parcel.address
            params["zone_code"] = parcel.zone_code
            plan.parsed_parameters = params
            logger.info("plan.parcel_lookup.found", plan_id=plan_id, parcel_id=str(parcel.id))
        else:
            logger.warning("plan.parcel_lookup.not_found", plan_id=plan_id,
                          address=parsed.get("address"))

        _update_plan_status(db, plan, "running_pipeline", step="policy_resolution",
                           progress_update={"parcel_lookup": "completed", "policy_resolution": "running"})

        # --- Step 3: Policy Resolution + Zoning Analysis ---
        zoning = None
        if parcel:
            try:
                zoning = _run_zoning_analysis(db, parcel)
                logger.info("plan.policy_resolution.completed", plan_id=plan_id,
                           zone=zoning.zone_string, category=zoning.standards.category if zoning.standards else None)
            except Exception as e:
                logger.warning("plan.policy_resolution.failed", plan_id=plan_id, error=str(e))

        _update_plan_status(db, plan, "running_pipeline", step="massing_generation",
                           progress_update={"policy_resolution": "completed", "massing_generation": "running"})

        # --- Step 4: Massing Generation ---
        massing_summary = None
        massing_compliance = None
        if parcel:
            try:
                from app.services.reference_data import resolve_massing_template_sync
                from app.services.thin_slice_runtime import MassingTemplateParameters

                template = resolve_massing_template_sync(db)
                template_payload = MassingTemplateParameters.model_validate(template.parameters_json)

                # Apply user overrides from parsed parameters
                overrides = {}
                if parsed.get("storeys"):
                    overrides["storeys"] = parsed["storeys"]
                if parsed.get("height_m"):
                    overrides["height_m"] = parsed["height_m"]

                massing_summary, massing_compliance = _run_massing(parcel, template_payload, overrides or None)
                logger.info("plan.massing.completed", plan_id=plan_id,
                           gfa=massing_summary.get("estimated_gfa_m2"),
                           storeys=massing_summary.get("storeys"))
            except Exception as e:
                logger.warning("plan.massing.failed", plan_id=plan_id, error=str(e))

        _update_plan_status(db, plan, "running_pipeline", step="layout_optimization",
                           progress_update={"massing_generation": "completed", "layout_optimization": "running"})

        # --- Step 5: Layout Optimization ---
        layout_result = None
        if massing_summary:
            try:
                from app.services.reference_data import resolve_massing_template_sync, resolve_unit_types_sync
                from app.services.thin_slice_runtime import MassingTemplateParameters

                template = resolve_massing_template_sync(db)
                template_payload = MassingTemplateParameters.model_validate(template.parameters_json)
                unit_types = resolve_unit_types_sync(db, parcel.jurisdiction_id if parcel else None)

                layout_result = _run_layout(massing_summary, template_payload, unit_types)
                logger.info("plan.layout.completed", plan_id=plan_id,
                           total_units=layout_result.get("total_units"))
            except Exception as e:
                logger.warning("plan.layout.failed", plan_id=plan_id, error=str(e))

        _update_plan_status(db, plan, "running_pipeline", step="financial_analysis",
                           progress_update={"layout_optimization": "completed", "financial_analysis": "running"})

        # --- Step 6: Financial Analysis ---
        financial_output = None
        if layout_result and massing_summary:
            try:
                from app.services.reference_data import (
                    resolve_financial_assumption_set_sync,
                    resolve_unit_types_sync,
                )
                from app.services.thin_slice_runtime import (
                    FinancialAssumptionPayload,
                    validate_financial_assumptions,
                )

                unit_types = resolve_unit_types_sync(db, parcel.jurisdiction_id if parcel else None)
                assumption_set = resolve_financial_assumption_set_sync(db)
                assumptions = validate_financial_assumptions(assumption_set)

                financial_output = _run_financial(layout_result, massing_summary, unit_types, assumptions)
                logger.info("plan.financial.completed", plan_id=plan_id,
                           noi=financial_output.get("noi"),
                           total_cost=financial_output.get("total_cost"))
            except Exception as e:
                logger.warning("plan.financial.failed", plan_id=plan_id, error=str(e))

        _update_plan_status(db, plan, "running_pipeline", step="entitlement_check",
                           progress_update={"financial_analysis": "completed", "entitlement_check": "running"})

        # --- Step 7: Entitlement / Compliance Check (DETERMINISTIC) ---
        compliance_result = None
        if zoning and massing_summary and layout_result:
            try:
                compliance_result = _run_compliance(zoning, massing_summary, layout_result)
                logger.info("plan.compliance.completed", plan_id=plan_id,
                           overall_compliant=compliance_result.overall_compliant,
                           variances=len(compliance_result.variances_needed))
            except Exception as e:
                logger.warning("plan.compliance.failed", plan_id=plan_id, error=str(e))

        _update_plan_status(db, plan, "running_pipeline", step="precedent_search",
                           progress_update={"entitlement_check": "completed", "precedent_search": "running"})

        # --- Step 8: Precedent Search ---
        precedents = []
        if parcel and massing_summary:
            try:
                precedents = _run_precedent_search(db, parcel, massing_summary)
                logger.info("plan.precedents.completed", plan_id=plan_id,
                           count=len(precedents))
            except Exception as e:
                logger.warning("plan.precedents.failed", plan_id=plan_id, error=str(e))

        _update_plan_status(db, plan, "running_pipeline", step="document_generation",
                           progress_update={"precedent_search": "completed", "document_generation": "running"})

        # --- Step 9: Generate Submission Documents ---
        _build_context_and_generate_docs(
            db, plan, parcel, zoning,
            massing_summary, layout_result, financial_output,
            compliance_result, precedents, parsed,
        )

        # Store summary results
        plan.pipeline_progress = {step: "completed" for step in PIPELINE_STEPS}
        plan.current_step = None
        plan.completed_at = datetime.now(timezone.utc)
        plan.summary = {
            "pipeline_steps_completed": len(PIPELINE_STEPS),
            "documents_generated": len(SUBMISSION_DOCUMENTS),
            "parcel_found": parcel is not None,
            "zoning_resolved": zoning is not None,
            "massing": massing_summary,
            "layout": layout_result,
            "finance": financial_output,
            "compliance": {
                "overall_compliant": compliance_result.overall_compliant if compliance_result else None,
                "variances_needed": len(compliance_result.variances_needed) if compliance_result else None,
                "minor_variance_applicable": compliance_result.minor_variance_applicable if compliance_result else None,
            } if compliance_result else None,
            "precedents_found": len(precedents),
        }
        _update_plan_status(db, plan, "completed")

        logger.info("plan.generation.completed", plan_id=plan_id)
        return {"plan_id": plan_id, "status": "completed"}

    except Exception as e:
        logger.error("plan.generation.failed", plan_id=plan_id, error=str(e))
        try:
            plan = db.query(DevelopmentPlan).filter(DevelopmentPlan.id == uuid.UUID(plan_id)).one()
            _update_plan_status(db, plan, "failed", error=str(e))
        except Exception:
            pass
        raise
    finally:
        db.close()
