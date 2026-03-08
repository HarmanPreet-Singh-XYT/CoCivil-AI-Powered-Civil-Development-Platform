import asyncio
import uuid
from datetime import datetime, timezone

import structlog

from app.database import get_sync_db
from app.models.plan import DevelopmentPlan, SubmissionDocument
from app.services.submission.readiness import evaluate_submission_readiness
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
    # ─── New AI-generated documents ───
    {
        "doc_type": "four_statutory_tests",
        "title": "Four Statutory Tests Analysis",
        "description": "Analysis of each minor variance test under Planning Act s.45(1)",
        "sort_order": 11,
    },
    {
        "doc_type": "approval_pathway_document",
        "title": "Approval Pathway Analysis",
        "description": "Classification of the approval route and estimated timeline",
        "sort_order": 12,
    },
    {
        "doc_type": "due_diligence_report",
        "title": "Due Diligence Report",
        "description": "Comprehensive risk assessment and constraint inventory",
        "sort_order": 13,
    },
    {
        "doc_type": "olt_appeal_brief",
        "title": "Ontario Land Tribunal Appeal Brief",
        "description": "Appeal brief for OLT proceedings with statutory test analysis",
        "sort_order": 14,
    },
    {
        "doc_type": "revised_rationale",
        "title": "Revised Planning Rationale",
        "description": "Updated rationale addressing refusal reasons point-by-point",
        "sort_order": 15,
    },
    {
        "doc_type": "mediation_strategy",
        "title": "Mediation Strategy",
        "description": "Strategy for resolving planning disputes through mediation",
        "sort_order": 16,
    },
    {
        "doc_type": "neighbour_support_letter",
        "title": "Neighbour Support Letter",
        "description": "Template letter for neighbouring property owners",
        "sort_order": 17,
    },
    {
        "doc_type": "pac_prep_package",
        "title": "Pre-Application Consultation Package",
        "description": "Package for pre-application consultation with city staff",
        "sort_order": 18,
    },
    {
        "doc_type": "submission_readiness_report",
        "title": "Submission Readiness Report",
        "description": "Assessment of submission package completeness",
        "sort_order": 19,
    },
    {
        "doc_type": "correction_response",
        "title": "Correction Response Letter",
        "description": "Response to corrections letter from planning department",
        "sort_order": 20,
    },
    {
        "doc_type": "compliance_review_report",
        "title": "Compliance Review Report",
        "description": "Self-review of generated submission package against requirements",
        "sort_order": 21,
    },
    {
        "doc_type": "variance_justification",
        "title": "Variance Justification Report",
        "description": "Per-variance justification for Committee of Adjustment application",
        "sort_order": 22,
    },
    # ─── Rule-based documents (deterministic, no AI cost) ───
    {
        "doc_type": "as_of_right_check",
        "title": "As-of-Right Compliance Check",
        "description": "Deterministic check of whether the proposal complies as-of-right",
        "sort_order": 23,
        "generation_method": "rule_based",
    },
    {
        "doc_type": "required_studies_checklist",
        "title": "Required Studies Checklist",
        "description": "Checklist of studies and reports required for the application",
        "sort_order": 24,
        "generation_method": "rule_based",
    },
    {
        "doc_type": "timeline_cost_estimate",
        "title": "Timeline & Cost Estimate",
        "description": "Estimated timeline and costs by approval pathway",
        "sort_order": 25,
        "generation_method": "rule_based",
    },
    {
        "doc_type": "building_permit_readiness_checklist",
        "title": "Building Permit Readiness Checklist",
        "description": "Checklist of building permit submission requirements",
        "sort_order": 26,
        "generation_method": "rule_based",
    },
    {
        "doc_type": "professional_referral_checklist",
        "title": "Professional Referral Checklist",
        "description": "Checklist of required professional consultants",
        "sort_order": 27,
        "generation_method": "rule_based",
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


def _fail_plan(db, plan, step, error):
    _update_plan_status(
        db,
        plan,
        "failed",
        step=step,
        progress_update={step: "failed"},
        error=error,
    )
    return {"plan_id": str(plan.id), "status": "failed", "error": error}


def _run_query_parsing(query: str) -> dict:
    """Run the async AI query parser from a sync context."""
    from app.ai.factory import get_ai_provider
    from app.ai.query_parser import parse_development_query

    provider = get_ai_provider()
    return asyncio.run(parse_development_query(provider, query))


def _run_parcel_lookup(db, parsed: dict) -> object | None:
    """Look up a parcel by address from parsed parameters."""
    from app.services.geospatial import resolve_active_parcel_by_address_sync

    address = parsed.get("address")
    if not address:
        logger.warning("plan.parcel_lookup.no_address")
        return None

    jurisdiction_id = parsed.get("jurisdiction_id")
    if jurisdiction_id:
        try:
            jurisdiction_id = uuid.UUID(str(jurisdiction_id))
        except (TypeError, ValueError):
            jurisdiction_id = None

    return resolve_active_parcel_by_address_sync(
        db,
        address,
        jurisdiction_id=jurisdiction_id,
    )


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
    """Search for real development applications near the parcel."""
    from sqlalchemy import func, select

    from app.models.entitlement import BuildingPermit, DevelopmentApplication
    from app.models.geospatial import Parcel

    parcel_geom_subq = (
        select(func.ST_Transform(Parcel.geom, 2952))
        .where(Parcel.id == parcel.id)
        .scalar_subquery()
    )

    # Subquery: count of building permits per application
    permit_count_subq = (
        select(
            BuildingPermit.development_application_id,
            func.count().label("permit_count"),
        )
        .group_by(BuildingPermit.development_application_id)
        .subquery()
    )

    try:
        rows = db.execute(
            select(
                DevelopmentApplication,
                func.ST_Distance(
                    func.ST_Transform(DevelopmentApplication.geom, 2952),
                    parcel_geom_subq,
                ).label("distance_m"),
                func.coalesce(permit_count_subq.c.permit_count, 0).label("permit_count"),
            )
            .outerjoin(
                permit_count_subq,
                permit_count_subq.c.development_application_id == DevelopmentApplication.id,
            )
            .where(DevelopmentApplication.jurisdiction_id == parcel.jurisdiction_id)
            .where(DevelopmentApplication.geom.isnot(None))
            .where(
                func.ST_DWithin(
                    func.ST_Transform(DevelopmentApplication.geom, 2952),
                    parcel_geom_subq,
                    2000,  # 2km radius
                )
            )
            .order_by("distance_m")
            .limit(50)
        ).all()
    except Exception:
        logger.warning("plan.precedent_search.spatial_query_failed", parcel_id=str(parcel.id))
        rows = []

    if not rows:
        return []

    from app.services.thin_slice_runtime import build_precedent_match_summary

    precedents = []
    for app, distance_m, permit_count in rows:
        try:
            summary = build_precedent_match_summary(
                app_id=app.id,
                app_number=app.app_number,
                address=app.address,
                app_type=app.app_type,
                decision=app.decision,
                proposed_height_m=app.proposed_height_m,
                proposed_units=app.proposed_units,
                proposed_fsi=app.proposed_fsi,
                distance_m=distance_m or 2000.0,
                permit_count=permit_count or 0,
            )
            precedents.append(summary)
        except Exception:
            continue

    # Sort by score descending, return top 10
    precedents.sort(key=lambda p: p.get("score", 0), reverse=True)
    return precedents[:10]


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
    policy_stack=None,
    overlays=None,
    generate_subset=None,
) -> list[SubmissionDocument]:
    """Build document context and generate all submission documents."""
    from app.ai.factory import get_ai_provider
    from app.services.compliance_engine import render_compliance_matrix_markdown
    from app.services.submission.context_builder import build_document_context
    from app.services.submission.generator import SubmissionPackageGenerator
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
        policy_stack=policy_stack.model_dump() if policy_stack else None,
        overlays=overlays.model_dump() if overlays else None,
        project_name=parsed.get("project_name", ""),
        organization_name="",
        parsed_parameters=parsed,
    )

    # Determine which docs to generate
    if generate_subset:
        # Explicit subset provided — use as-is
        docs_to_generate = [d for d in SUBMISSION_DOCUMENTS if d["doc_type"] in generate_subset]
    else:
        # Auto-select based on project context
        from app.services.submission.document_selector import select_documents_for_project

        selected_types, _reasons = select_documents_for_project(
            compliance_result=compliance_result,
            massing=massing_summary,
            layout=layout_result,
            overlays=overlays,
            precedents=precedents,
            parsed=parsed,
            financial_output=financial_output,
        )
        docs_to_generate = [d for d in SUBMISSION_DOCUMENTS if d["doc_type"] in selected_types]

    generated_documents: list[SubmissionDocument] = []

    # Set up AI generator with a single event loop
    loop = asyncio.new_event_loop()
    try:
        provider = get_ai_provider()
        generator = SubmissionPackageGenerator(provider)
    except Exception as e:
        logger.warning("plan.ai_provider.init_failed", error=str(e))
        provider = None
        generator = None

    try:
        for doc_spec in docs_to_generate:
            doc_type = doc_spec["doc_type"]
            content = None
            ai_provider_name = None
            ai_model_name = None
            content_json = None

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
            elif doc_spec.get("generation_method") == "rule_based" and generator:
                try:
                    result = generator.generate_rule_based_document(doc_type, context)
                    content = result["content_text"]
                except Exception as e:
                    logger.warning("plan.doc.rule_based_failed", doc_type=doc_type, error=str(e))
                    content = _build_grounded_content(doc_spec, context, SAFETY_PREAMBLE)
            elif generator:
                try:
                    result = loop.run_until_complete(
                        generator.generate_document(doc_type, context)
                    )
                    content = result["content_text"]
                    content_json = result.get("content_json")
                    metadata = result.get("metadata", {})
                    ai_provider_name = metadata.get("ai_provider")
                    ai_model_name = metadata.get("ai_model")
                except Exception as e:
                    logger.warning("plan.doc.ai_failed", doc_type=doc_type, error=str(e))
                    content = _build_grounded_content(doc_spec, context, SAFETY_PREAMBLE)

            # Final fallback if content is still None
            if content is None:
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
                content_json=content_json,
                ai_provider=ai_provider_name,
                ai_model=ai_model_name,
            )
            db.add(doc)
            generated_documents.append(doc)
    finally:
        loop.close()

    db.flush()
    return generated_documents


def _build_grounded_content(doc_spec: dict, context: dict, preamble: str) -> str:
    """Build grounded document content from context data.

    Uses real pipeline data to populate the document. Where AI generation
    is available, it will be invoked; otherwise, structured data is presented.
    """
    doc_type = doc_spec["doc_type"]
    title = doc_spec["title"]

    sections = [f"> {preamble}\n\n---\n\n# {title}\n"]

    if doc_type == "cover_letter":
        sections.append("**To**: City of Toronto Planning Department\n")
        sections.append(f"**Re**: Development Application — {context.get('address', 'N/A')}\n")
        sections.append(f"**Project**: {context.get('project_name', 'N/A')}\n\n")
        sections.append(f"This letter introduces a {context.get('development_type', 'development')} ")
        sections.append(f"application for the property at {context.get('address', 'N/A')}. ")
        sections.append(f"The proposal comprises a {context.get('building_type', 'building')} ")
        sections.append(f"of {context.get('storeys', 'N/A')} storeys ({context.get('height_m', 'N/A')}m) ")
        sections.append(f"containing {context.get('unit_count', 'N/A')} residential units ")
        sections.append(f"with a total GFA of {context.get('gross_floor_area_sqm', 'N/A')}.\n")

    elif doc_type == "planning_rationale":
        sections.append("## 1. Site Description\n\n")
        sections.append(f"The subject site is located at {context.get('address', 'N/A')}, ")
        sections.append(f"currently zoned {context.get('zoning_code', 'N/A')}.\n\n")
        sections.append("## 2. Policy Framework\n\n")
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
        sections.append("## Site Dimensions\n\n")
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


def run_plan_generation(plan_id: str, query: str, auto_run: bool = True, generate_subset: list[str] | None = None):
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
            return _fail_plan(db, plan, "parcel_lookup", "Parcel lookup failed: no parcel matched the parsed address")

        _update_plan_status(db, plan, "running_pipeline", step="policy_resolution",
                           progress_update={"parcel_lookup": "completed", "policy_resolution": "running"})

        # --- Step 3: Policy Resolution + Zoning Analysis ---
        zoning = None
        policy_stack = None
        overlays = None
        if parcel:
            try:
                from app.services.overlay_service import get_parcel_overlays_response_sync
                from app.services.policy_stack import get_policy_stack_response_sync

                zoning = _run_zoning_analysis(db, parcel)
                policy_stack = get_policy_stack_response_sync(db, parcel)
                overlays = get_parcel_overlays_response_sync(db, parcel)
                logger.info("plan.policy_resolution.completed", plan_id=plan_id,
                           zone=zoning.zone_string, category=zoning.standards.category if zoning.standards else None,
                           policy_clauses=len(policy_stack.applicable_policies),
                           overlays=len(overlays.overlays))
            except Exception as e:
                logger.warning("plan.policy_resolution.failed", plan_id=plan_id, error=str(e))
                return _fail_plan(db, plan, "policy_resolution", f"Policy resolution failed: {e}")

        _update_plan_status(db, plan, "running_pipeline", step="massing_generation",
                           progress_update={"policy_resolution": "completed", "massing_generation": "running"})

        # --- Step 4: Massing Generation ---
        massing_summary = None
        massing_compliance = None
        if parcel:
            try:
                from app.services.thin_slice_runtime import resolve_template

                _template, template_payload = resolve_template(db)

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
                return _fail_plan(db, plan, "massing_generation", f"Massing generation failed: {e}")

        _update_plan_status(db, plan, "running_pipeline", step="layout_optimization",
                           progress_update={"massing_generation": "completed", "layout_optimization": "running"})

        # --- Step 5: Layout Optimization ---
        layout_result = None
        if massing_summary:
            try:
                from app.services.thin_slice_runtime import resolve_template, resolve_unit_types

                _template, template_payload = resolve_template(db)
                unit_types = resolve_unit_types(db, jurisdiction_id=parcel.jurisdiction_id if parcel else None)

                layout_result = _run_layout(massing_summary, template_payload, unit_types)
                logger.info("plan.layout.completed", plan_id=plan_id,
                           total_units=layout_result.get("total_units"))
            except Exception as e:
                logger.warning("plan.layout.failed", plan_id=plan_id, error=str(e))
                return _fail_plan(db, plan, "layout_optimization", f"Layout optimization failed: {e}")

        _update_plan_status(db, plan, "running_pipeline", step="financial_analysis",
                           progress_update={"layout_optimization": "completed", "financial_analysis": "running"})

        # --- Step 6: Financial Analysis ---
        financial_output = None
        if layout_result and massing_summary:
            try:
                from app.services.thin_slice_runtime import (
                    resolve_assumption_set,
                    resolve_unit_types,
                )

                unit_types = resolve_unit_types(db, jurisdiction_id=parcel.jurisdiction_id if parcel else None)
                _assumption_set, assumptions = resolve_assumption_set(db)

                financial_output = _run_financial(layout_result, massing_summary, unit_types, assumptions)
                logger.info("plan.financial.completed", plan_id=plan_id,
                           noi=financial_output.get("noi"),
                           total_cost=financial_output.get("total_cost"))
            except Exception as e:
                logger.warning("plan.financial.failed", plan_id=plan_id, error=str(e))
                return _fail_plan(db, plan, "financial_analysis", f"Financial analysis failed: {e}")

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
                return _fail_plan(db, plan, "entitlement_check", f"Entitlement check failed: {e}")

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
                return _fail_plan(db, plan, "precedent_search", f"Precedent search failed: {e}")

        _update_plan_status(db, plan, "running_pipeline", step="document_generation",
                           progress_update={"precedent_search": "completed", "document_generation": "running"})

        # --- Step 9: Generate Submission Documents ---
        generated_documents = _build_context_and_generate_docs(
            db, plan, parcel, zoning,
            massing_summary, layout_result, financial_output,
            compliance_result, precedents, parsed,
            policy_stack=policy_stack,
            overlays=overlays,
            generate_subset=generate_subset,
        )

        # Store summary results
        plan.pipeline_progress = {step: "completed" for step in PIPELINE_STEPS}
        plan.current_step = None
        plan.completed_at = datetime.now(timezone.utc)
        plan.summary = {
            "pipeline_steps_completed": len(PIPELINE_STEPS),
            "documents_generated": len(generated_documents),
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
        plan.summary["submission_readiness"] = evaluate_submission_readiness(plan, generated_documents)
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
