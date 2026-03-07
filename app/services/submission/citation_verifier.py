"""Post-generation citation verification.

Scans AI-generated text for by-law section references and flags any
that don't match known valid sections from toronto_zoning.py + policy DB.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.data.toronto_zoning import VALID_BYLAW_SECTIONS


@dataclass(frozen=True)
class CitationIssue:
    """A flagged citation that doesn't match known valid sections."""

    line_number: int
    cited_section: str
    context: str
    suggestion: str


# Regex to find by-law section references in text
# Matches patterns like: §10.20, Section 10.20, 569-2013 §40.10.40.10
_SECTION_PATTERN = re.compile(
    r"(?:§|Section\s+|section\s+|By-law\s+569-2013\s+§?)"
    r"([\d]+(?:\.[\d]+)*(?:\.[\d]+)*)",
    re.IGNORECASE,
)

# Also match standalone references like "10.20.40.1"
_STANDALONE_SECTION = re.compile(
    r"\b(\d{1,3}\.\d{1,3}(?:\.\d{1,3}){0,3})\b"
)


def verify_citations(text: str, extra_valid: set[str] | None = None) -> list[CitationIssue]:
    """Scan generated text for by-law section references.

    Flags any that don't match VALID_BYLAW_SECTIONS.

    Args:
        text: The generated document text to scan.
        extra_valid: Additional valid sections from the policy DB.

    Returns:
        List of CitationIssue objects with line numbers and suggestions.
    """
    valid = VALID_BYLAW_SECTIONS.copy()
    if extra_valid:
        valid.update(extra_valid)

    issues: list[CitationIssue] = []
    seen: set[str] = set()

    for line_num, line in enumerate(text.splitlines(), start=1):
        # Check explicit section references
        for match in _SECTION_PATTERN.finditer(line):
            section = match.group(1)
            if section not in valid and section not in seen:
                seen.add(section)
                context = line.strip()[:120]
                issues.append(CitationIssue(
                    line_number=line_num,
                    cited_section=section,
                    context=context,
                    suggestion=_suggest_correction(section, valid),
                ))

    return issues


def strip_unverified_citations(text: str, issues: list[CitationIssue]) -> str:
    """Replace unverified citations with a warning marker.

    Substitutes each flagged section with '[CITATION NEEDED — verify before submission]'.
    """
    if not issues:
        return text

    bad_sections = {issue.cited_section for issue in issues}
    result = text

    for section in bad_sections:
        # Replace §section and Section section patterns
        patterns = [
            re.compile(rf"§{re.escape(section)}\b"),
            re.compile(rf"(?:Section|section)\s+{re.escape(section)}\b"),
            re.compile(rf"569-2013\s+§?{re.escape(section)}\b"),
        ]
        replacement = "[CITATION NEEDED — verify before submission]"
        for pattern in patterns:
            result = pattern.sub(replacement, result)

    return result


def _suggest_correction(section: str, valid: set[str]) -> str:
    """Suggest the closest valid section number."""
    parts = section.split(".")
    if not parts:
        return "Unable to suggest correction"

    # Try progressively shorter prefixes
    for length in range(len(parts), 0, -1):
        prefix = ".".join(parts[:length])
        matches = [s for s in valid if s.startswith(prefix)]
        if matches:
            closest = min(matches, key=lambda s: abs(len(s) - len(section)))
            return f"Did you mean §{closest}?"

    # Try matching just the chapter number
    chapter = parts[0]
    matches = [s for s in valid if s.startswith(chapter + ".")]
    if matches:
        return f"Valid sections in Chapter {chapter}: {', '.join(sorted(matches)[:5])}"

    return "Section not found in By-law 569-2013 reference data — verify manually"
