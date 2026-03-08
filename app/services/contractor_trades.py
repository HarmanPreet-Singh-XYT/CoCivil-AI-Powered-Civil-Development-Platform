"""Map compliance variances, doc types, and massing typology to Google Places search terms."""

# Doc type → trade search terms
_DOC_TYPE_TRADES: dict[str, str] = {
    "shadow_study": "architectural lighting consultant",
    "massing_summary": "structural engineer",
    "financial_feasibility": "quantity surveyor",
    "planning_rationale": "planning consultant",
    "compliance_matrix": "building code consultant",
}

# Massing typology → trade search terms
_TYPOLOGY_TRADES: dict[str, str] = {
    "midrise": "structural engineer",
    "highrise": "structural engineer",
    "tower_on_podium": "structural engineer",
    "point_tower": "structural engineer",
    "multiplex": "renovation contractor",
    "townhouse": "renovation contractor",
    "slab": "structural engineer",
    "mixed_use_midrise": "structural engineer",
}


def derive_trade_categories(
    doc_types: list[str] | None = None,
    massing: dict | None = None,
) -> list[str]:
    """Derive up to 4 Google Places search terms from plan outputs.

    Args:
        doc_types: List of generated document type strings.
        massing: Massing summary dict (expects 'typology' key).

    Returns:
        Unique list of trade search terms, max 4.
    """
    trades: list[str] = []
    seen: set[str] = set()

    def _add(term: str) -> None:
        if term not in seen and len(trades) < 4:
            seen.add(term)
            trades.append(term)

    # From doc types
    for dt in doc_types or []:
        if dt in _DOC_TYPE_TRADES:
            _add(_DOC_TYPE_TRADES[dt])

    # From typology
    typology = (massing or {}).get("typology", "")
    if typology in _TYPOLOGY_TRADES:
        _add(_TYPOLOGY_TRADES[typology])

    # Always include general contractor as fallback
    _add("general contractor")

    return trades
