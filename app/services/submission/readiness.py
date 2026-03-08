from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.models.plan import DevelopmentPlan, SubmissionDocument

NOT_AVAILABLE_MARKER = "[NOT AVAILABLE"

ESSENTIAL_DOCUMENT_TYPES: dict[str, str] = {
    "cover_letter": "Cover letter",
    "planning_rationale": "Planning rationale",
    "compliance_matrix": "Compliance matrix",
    "site_plan_data": "Site plan data summary",
    "massing_summary": "Massing and built form summary",
    "unit_mix_summary": "Unit mix and layout summary",
    "financial_feasibility": "Financial feasibility summary",
}

EXTENDED_ESSENTIAL_TYPES: dict[str, str] = {
    **ESSENTIAL_DOCUMENT_TYPES,
    "approval_pathway_document": "Approval pathway document",
    "as_of_right_check": "As-of-right compliance check",
    "required_studies_checklist": "Required studies checklist",
}

ESSENTIAL_INPUTS: dict[str, str] = {
    "address": "Confirm the subject property address or parcel PIN.",
    "project_name": "Provide the official project name used on the submission package.",
    "development_type": "Confirm the proposed development type.",
    "building_type": "Confirm the proposed building form.",
}


def document_has_unresolved_placeholders(content: str | None) -> bool:
    return bool(content and NOT_AVAILABLE_MARKER in content)


def evaluate_submission_readiness(
    plan: DevelopmentPlan,
    documents: Iterable[SubmissionDocument],
) -> dict[str, Any]:
    parsed = plan.parsed_parameters or {}
    summary = plan.summary or {}
    documents = list(documents)

    blocking_issues: list[dict[str, str]] = []
    review_issues: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    next_actions: list[str] = []

    for field_name, action in ESSENTIAL_INPUTS.items():
        value = parsed.get(field_name)
        if value in (None, "", []):
            blocking_issues.append(
                {
                    "code": f"missing_{field_name}",
                    "severity": "blocking",
                    "message": f"Missing required submission input: {field_name.replace('_', ' ')}.",
                    "action": action,
                }
            )

    if not summary.get("parcel_found"):
        blocking_issues.append(
            {
                "code": "parcel_unresolved",
                "severity": "blocking",
                "message": "The parcel could not be matched confidently.",
                "action": "Confirm the municipal address or parcel identifier before submission.",
            }
        )

    if not summary.get("zoning_resolved"):
        blocking_issues.append(
            {
                "code": "zoning_unresolved",
                "severity": "blocking",
                "message": "Applicable zoning could not be resolved.",
                "action": "Resolve zoning and applicable policy controls before using the package for submission.",
            }
        )

    pipeline_requirements = {
        "massing": "Generate a buildable massing summary for the proposal.",
        "layout": "Generate a layout and unit-mix result.",
        "finance": "Generate a financial feasibility summary.",
        "compliance": "Run the deterministic compliance check.",
    }
    for key, action in pipeline_requirements.items():
        if not summary.get(key):
            blocking_issues.append(
                {
                    "code": f"missing_{key}",
                    "severity": "blocking",
                    "message": f"Missing required pipeline output: {key}.",
                    "action": action,
                }
            )

    parse_confidence = plan.parse_confidence
    if parse_confidence is None or parse_confidence < 0.75:
        review_issues.append(
            {
                "code": "low_parse_confidence",
                "severity": "review",
                "message": "The original request was parsed with low confidence.",
                "action": "Review the extracted proposal parameters against the source request before submission.",
            }
        )

    compliance = summary.get("compliance") or {}
    if compliance.get("variances_needed"):
        warnings.append(
                {
                    "code": "variances_required",
                    "severity": "warning",
                    "message": "The current proposal appears to require one or more variances.",
                    "action": (
                        "Confirm whether the package is intended for as-of-right approval, "
                        "minor variance, or rezoning."
                    ),
                }
            )

    if not summary.get("precedents_found"):
        warnings.append(
            {
                "code": "no_precedents_found",
                "severity": "warning",
                "message": "No supporting precedent applications were found in the current data set.",
                "action": "Add precedent support manually if the submission strategy depends on comparable approvals.",
            }
        )

    document_statuses: list[dict[str, Any]] = []
    docs_by_type = {document.doc_type: document for document in documents}
    # Use extended essential types if plan was generated with new pipeline (>10 docs)
    essential_types = EXTENDED_ESSENTIAL_TYPES if len(docs_by_type) > 10 else ESSENTIAL_DOCUMENT_TYPES
    for doc_type, title in essential_types.items():
        document = docs_by_type.get(doc_type)
        if document is None:
            blocking_issues.append(
                {
                    "code": f"missing_document_{doc_type}",
                    "severity": "blocking",
                    "message": f"Required document is missing: {title}.",
                    "action": f"Generate the {title.lower()} before submission.",
                }
            )
            document_statuses.append(
                {
                    "doc_type": doc_type,
                    "title": title,
                    "status": "missing",
                    "review_status": "missing",
                    "ready": False,
                    "has_placeholders": False,
                }
            )
            continue

        has_placeholders = document_has_unresolved_placeholders(document.content_text)
        ready = document.status == "completed" and document.review_status == "approved" and not has_placeholders
        document_statuses.append(
            {
                "doc_type": document.doc_type,
                "title": document.title,
                "status": document.status,
                "review_status": document.review_status,
                "ready": ready,
                "has_placeholders": has_placeholders,
            }
        )

        if document.status != "completed":
            blocking_issues.append(
                {
                    "code": f"incomplete_document_{doc_type}",
                    "severity": "blocking",
                    "message": f"{title} is not fully generated.",
                    "action": f"Complete generation of the {title.lower()} before submission.",
                }
            )
        if has_placeholders:
            blocking_issues.append(
                {
                    "code": f"placeholder_document_{doc_type}",
                    "severity": "blocking",
                    "message": f"{title} still contains unresolved placeholders or missing manual inputs.",
                    "action": f"Replace all placeholder values in the {title.lower()} before review.",
                }
            )
        if document.review_status != "approved":
            review_issues.append(
                {
                    "code": f"unapproved_document_{doc_type}",
                    "severity": "review",
                    "message": f"{title} has not been approved in the review workflow.",
                    "action": f"Complete review and approval for the {title.lower()}.",
                }
            )

    for issue_group in (blocking_issues, review_issues):
        for issue in issue_group:
            action = issue["action"]
            if action not in next_actions:
                next_actions.append(action)

    ready_for_submission = not blocking_issues and not review_issues
    return {
        "ready_for_submission": ready_for_submission,
        "blocking_issues": blocking_issues,
        "review_issues": review_issues,
        "warnings": warnings,
        "next_actions": next_actions,
        "documents": document_statuses,
    }
