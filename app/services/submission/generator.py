import structlog

from app.ai.base import AIProvider
from app.services.submission.citation_verifier import strip_unverified_citations, verify_citations
from app.services.submission.templates import DOCUMENT_TEMPLATES, SAFETY_PREAMBLE

logger = structlog.get_logger()


class SubmissionPackageGenerator:
    """Generates a complete government submission package from pipeline results.

    Takes the results from each pipeline stage (parcel data, policy stack,
    massing, layout, finance, entitlement, precedents) and generates
    professional submission documents using AI + structured templates.

    Every document is prepended with the SAFETY_PREAMBLE and post-processed
    through citation verification.
    """

    def __init__(self, ai_provider: AIProvider):
        self.ai = ai_provider

    async def generate_document(self, doc_type: str, context: dict) -> dict:
        """Generate a single submission document.

        Args:
            doc_type: Type of document (planning_rationale, compliance_matrix, etc.)
            context: Pipeline results and parameters (from context_builder)

        Returns:
            dict with 'content_text', 'content_json', and 'metadata'
        """
        template = DOCUMENT_TEMPLATES.get(doc_type)
        if not template:
            raise ValueError(f"Unknown document type: {doc_type}")

        logger.info("submission.generating", doc_type=doc_type)

        system_prompt = template["system_prompt"]
        user_prompt = template["user_prompt_template"].format(**self._safe_format(context))

        response = await self.ai.generate(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=template.get("max_tokens", 4096),
        )

        content = response.content

        # Post-process: verify citations in AI-generated text
        citation_issues = verify_citations(content)
        if citation_issues:
            logger.warning(
                "submission.citation_issues",
                doc_type=doc_type,
                issue_count=len(citation_issues),
                sections=[i.cited_section for i in citation_issues],
            )
            content = strip_unverified_citations(content, citation_issues)

        # Prepend safety preamble to all generated content
        content = f"> {SAFETY_PREAMBLE}\n\n---\n\n{content}"

        # For compliance_matrix, the table is already in the context —
        # append it after the AI narrative if not already present
        if doc_type == "compliance_matrix":
            compliance_table = context.get("compliance_summary", "")
            if compliance_table and compliance_table not in content:
                content = f"{content}\n\n## Compliance Matrix\n\n{compliance_table}"

        # For structured documents, also generate JSON
        content_json = None
        if template.get("structured_output"):
            try:
                content_json = await self.ai.generate_structured(
                    prompt=f"Convert this document into structured JSON:\n\n{content}",
                    schema=template["structured_output"],
                    system="Extract the key data points into the provided JSON schema.",
                )
            except Exception as e:
                logger.warning("submission.json_extraction_failed", doc_type=doc_type, error=str(e))

        return {
            "content_text": content,
            "content_json": content_json,
            "metadata": {
                "ai_provider": "configured",
                "ai_model": response.model,
                "input_tokens": response.usage.get("input_tokens", 0),
                "output_tokens": response.usage.get("output_tokens", 0),
                "citation_issues": len(citation_issues),
                "safety_preamble_included": True,
            },
        }

    async def generate_full_package(self, context: dict) -> list[dict]:
        """Generate all submission documents for a development plan.

        Args:
            context: Complete pipeline results (from context_builder)

        Returns:
            List of document dicts with doc_type, content_text, content_json
        """
        documents = []
        for doc_type in DOCUMENT_TEMPLATES:
            try:
                result = await self.generate_document(doc_type, context)
                documents.append({"doc_type": doc_type, **result})
            except Exception as e:
                logger.error("submission.document_failed", doc_type=doc_type, error=str(e))
                documents.append({
                    "doc_type": doc_type,
                    "content_text": (
                        f"> {SAFETY_PREAMBLE}\n\n---\n\n"
                        f"Error generating {doc_type}: {e}"
                    ),
                    "content_json": None,
                    "metadata": {"error": str(e), "safety_preamble_included": True},
                })
        return documents

    def generate_rule_based_document(self, doc_type: str, context: dict) -> dict:
        """Generate a deterministic document without AI.

        Args:
            doc_type: Type of rule-based document.
            context: Pipeline results and parameters.

        Returns:
            dict with 'content_text' and 'metadata'.
        """
        render_map = {
            "as_of_right_check": self._render_as_of_right_check,
            "required_studies_checklist": self._render_required_studies,
            "timeline_cost_estimate": self._render_timeline_cost,
            "building_permit_readiness_checklist": self._render_building_permit_checklist,
            "professional_referral_checklist": self._render_professional_referral,
        }

        renderer = render_map.get(doc_type)
        if not renderer:
            raise ValueError(f"No rule-based renderer for: {doc_type}")

        content = f"> {SAFETY_PREAMBLE}\n\n---\n\n{renderer(context)}"
        return {
            "content_text": content,
            "content_json": None,
            "metadata": {"generation_method": "rule_based", "ai_provider": None},
        }

    @staticmethod
    def _render_as_of_right_check(ctx: dict) -> str:
        lines = ["# As-of-Right Compliance Check\n"]
        lines.append(f"**Address**: {ctx.get('address', 'N/A')}\n")
        lines.append(f"**Zoning**: {ctx.get('zoning_code', 'N/A')}\n\n")

        lines.append("## Compliance Summary\n")
        lines.append(f"{ctx.get('compliance_summary', 'No compliance data available.')}\n\n")

        lines.append("## Variances Required\n")
        lines.append(f"{ctx.get('variance_summary', 'None required.')}\n\n")

        lines.append("## Approval Pathway\n")
        lines.append(f"{ctx.get('approval_pathway_summary', 'Unable to determine.')}\n\n")

        # Bill 60 eligibility note
        lines.append("## Bill 60 (2025) As-of-Right Provisions\n")
        lines.append(
            "Bill 60 introduces as-of-right permissions for prescribed residential "
            "deviations from zoning by-laws, removing the need for a Committee of "
            "Adjustment application in qualifying cases. Verify whether the proposed "
            "variances fall within prescribed deviation limits.\n"
        )
        return "".join(lines)

    @staticmethod
    def _render_required_studies(ctx: dict) -> str:
        lines = ["# Required Studies Checklist\n"]
        lines.append(f"**Address**: {ctx.get('address', 'N/A')}\n\n")

        height_str = ctx.get("height_m", "0")
        try:
            height = float(str(height_str).replace(",", "").replace(" m", "").replace("m", ""))
        except (ValueError, TypeError):
            height = 0

        unit_str = ctx.get("unit_count", "0")
        try:
            units = int(str(unit_str).replace(",", "").replace("[NOT AVAILABLE", "0").split("]")[0] or "0")
        except (ValueError, TypeError):
            units = 0

        studies = []
        studies.append(("Planning Rationale", True, "Required for all applications"))
        studies.append(("Survey / Topographic Plan", True, "Required for all applications"))
        if height > 10:
            studies.append(("Shadow Study", True, "Required: height > 10m"))
        if height > 20:
            studies.append(("Wind Study", True, "Required: height > 20m"))
        if units > 50:
            studies.append(("Traffic Impact Study (TIS)", True, "Required: > 50 units"))
        else:
            studies.append(("Traffic Impact Study (TIS)", False, "Not required: ≤ 50 units"))

        # Check for overlays in due diligence flags
        dd_flags = ctx.get("due_diligence_flags", "")
        if "heritage" in dd_flags.lower() or "Heritage" in dd_flags:
            studies.append(("Heritage Impact Assessment (HIA)", True, "Heritage overlay detected"))
        if "trca" in dd_flags.lower() or "conservation" in dd_flags.lower():
            studies.append(("Environmental Impact Study (EIS)", True, "Conservation authority overlay"))

        studies.append(("Servicing Report", True, "Required for most applications"))
        studies.append(("Arborist Report", True, "Required if trees on site"))
        studies.append(("Phase 1 Environmental Site Assessment", True, "Recommended for all sites"))

        lines.append("| Study | Required | Rationale |\n")
        lines.append("|-------|----------|----------|\n")
        for name, required, rationale in studies:
            status = "YES" if required else "NO"
            lines.append(f"| {name} | {status} | {rationale} |\n")

        return "".join(lines)

    @staticmethod
    def _render_timeline_cost(ctx: dict) -> str:
        lines = ["# Timeline & Cost Estimate\n"]
        lines.append(f"**Address**: {ctx.get('address', 'N/A')}\n\n")

        pathway = ctx.get("approval_pathway_summary", "")

        if "As-of-Right" in pathway:
            lines.append("## Approval Pathway: As-of-Right\n\n")
            lines.append("| Phase | Estimated Duration | Estimated Cost |\n")
            lines.append("|-------|-------------------|----------------|\n")
            lines.append("| Site Plan Approval | 3-6 months | $5,000-$15,000 |\n")
            lines.append("| Building Permit | 2-4 months | $2,000-$10,000 |\n")
            lines.append("| **Total** | **5-10 months** | **$7,000-$25,000** |\n")
        elif "Minor Variance" in pathway or "Committee of Adjustment" in pathway:
            lines.append("## Approval Pathway: Minor Variance (CoA)\n\n")
            lines.append("| Phase | Estimated Duration | Estimated Cost |\n")
            lines.append("|-------|-------------------|----------------|\n")
            lines.append("| Application Preparation | 2-4 weeks | $3,000-$8,000 |\n")
            lines.append("| CoA Hearing | 4-8 weeks | $2,500-$5,000 (filing fee) |\n")
            lines.append("| Appeal Period | 20 days | — |\n")
            lines.append("| Site Plan Approval | 3-6 months | $5,000-$15,000 |\n")
            lines.append("| Building Permit | 2-4 months | $2,000-$10,000 |\n")
            lines.append("| **Total** | **7-14 months** | **$12,500-$38,000** |\n")
        else:
            lines.append("## Approval Pathway: Zoning By-law Amendment (ZBA)\n\n")
            lines.append("| Phase | Estimated Duration | Estimated Cost |\n")
            lines.append("|-------|-------------------|----------------|\n")
            lines.append("| Pre-Application Consultation | 1-2 months | $5,000-$10,000 |\n")
            lines.append("| Application Preparation | 2-4 months | $15,000-$50,000 |\n")
            lines.append("| City Review & Public Hearing | 6-12 months | $10,000-$30,000 (filing fee) |\n")
            lines.append("| OLT Appeal (if appealed) | 6-18 months | $20,000-$100,000 |\n")
            lines.append("| Site Plan Approval | 3-6 months | $5,000-$15,000 |\n")
            lines.append("| Building Permit | 2-4 months | $2,000-$10,000 |\n")
            lines.append("| **Total** | **14-46 months** | **$57,000-$215,000** |\n")

        lines.append("\n*Estimates are indicative only. Actual costs depend on project complexity, "
                     "consultant fees, and municipal charges.*\n")
        return "".join(lines)

    @staticmethod
    def _render_building_permit_checklist(ctx: dict) -> str:
        lines = ["# Building Permit Readiness Checklist\n"]
        lines.append(f"**Address**: {ctx.get('address', 'N/A')}\n\n")

        categories = [
            ("Architectural", [
                "Floor plans for all levels",
                "Building elevations (all sides)",
                "Building sections (longitudinal and cross)",
                "Wall sections and construction details",
                "Door and window schedules",
                "Room finish schedules",
                "Accessibility compliance (AODA / OBC Part 3.8)",
            ]),
            ("Structural", [
                "Foundation plan",
                "Framing plans for all levels",
                "Structural details and connections",
                "Geotechnical report",
                "Structural engineer's seal and signature",
            ]),
            ("Mechanical", [
                "HVAC layout and equipment schedules",
                "Plumbing layout and riser diagrams",
                "Fire suppression system (if required)",
                "Energy efficiency compliance (SB-10 / SB-12)",
            ]),
            ("Electrical", [
                "Electrical layout and panel schedules",
                "Lighting plans",
                "Fire alarm system design",
                "Emergency power (if required)",
            ]),
            ("Site Servicing", [
                "Site plan with grading",
                "Stormwater management plan",
                "Sanitary and storm sewer connections",
                "Water service connection",
            ]),
        ]

        for category, items in categories:
            lines.append(f"## {category}\n\n")
            for item in items:
                lines.append(f"- [ ] {item}\n")
            lines.append("\n")

        return "".join(lines)

    @staticmethod
    def _render_professional_referral(ctx: dict) -> str:
        lines = ["# Professional Referral Checklist\n"]
        lines.append(f"**Address**: {ctx.get('address', 'N/A')}\n\n")

        height_str = ctx.get("height_m", "0")
        try:
            height = float(str(height_str).replace(",", "").replace(" m", "").replace("m", ""))
        except (ValueError, TypeError):
            height = 0

        storeys_str = ctx.get("storeys", "0")
        try:
            storeys = int(str(storeys_str).replace(",", ""))
        except (ValueError, TypeError):
            storeys = 0

        unit_str = ctx.get("unit_count", "0")
        try:
            units = int(str(unit_str).replace(",", "").replace("[NOT AVAILABLE", "0").split("]")[0] or "0")
        except (ValueError, TypeError):
            units = 0

        gfa_str = ctx.get("gross_floor_area_sqm", "0")
        try:
            gfa = float(str(gfa_str).replace(",", "").replace(" m²", "").replace("m²", ""))
        except (ValueError, TypeError):
            gfa = 0

        professionals = []
        professionals.append(("Registered Professional Planner (RPP)", True,
                              "Required for all planning applications"))
        professionals.append(("Ontario Land Surveyor (OLS)", True,
                              "Required for survey and legal description"))

        if gfa > 600 or storeys > 3:
            professionals.append(("Ontario Association of Architects (OAA)", True,
                                  f"Required: GFA > 600m² or > 3 storeys"))
        else:
            professionals.append(("Ontario Association of Architects (OAA)", False,
                                  "Not required for small projects (< 600m², ≤ 3 storeys)"))

        professionals.append(("Professional Engineer — Structural (P.Eng.)", True,
                              "Required for structural design"))
        professionals.append(("Professional Engineer — Mechanical (P.Eng.)", True,
                              "Required for HVAC and plumbing design"))
        professionals.append(("Professional Engineer — Electrical (P.Eng.)", True,
                              "Required for electrical design"))

        if units > 50:
            professionals.append(("Traffic Engineer", True,
                                  f"Required: > 50 units (TIS needed)"))
        else:
            professionals.append(("Traffic Engineer", False,
                                  "Not required: ≤ 50 units"))

        professionals.append(("Geotechnical Engineer", True,
                              "Required for foundation design"))
        professionals.append(("Landscape Architect", True,
                              "Required for site plan applications"))
        professionals.append(("Arborist (ISA Certified)", True,
                              "Required if trees on site"))

        lines.append("| Professional | Required | Rationale |\n")
        lines.append("|-------------|----------|----------|\n")
        for name, required, rationale in professionals:
            status = "YES" if required else "OPTIONAL"
            lines.append(f"| {name} | {status} | {rationale} |\n")

        return "".join(lines)

    @staticmethod
    def _safe_format(context: dict) -> dict:
        """Return a defaultdict-like mapping that returns placeholder for missing keys."""
        class SafeDict(dict):
            def __missing__(self, key):
                return f"[{key} — data pending]"
        return SafeDict(context)
