"""Tests for the citation verifier."""

from app.services.submission.citation_verifier import (
    CitationIssue,
    strip_unverified_citations,
    verify_citations,
)


class TestVerifyCitations:
    """Test citation verification in generated text."""

    def test_valid_section_not_flagged(self):
        """Known valid sections should not be flagged."""
        text = "Per §10.20 of By-law 569-2013, the maximum height is 10m."
        issues = verify_citations(text)
        assert len(issues) == 0

    def test_invalid_section_flagged(self):
        """Unknown sections should be flagged."""
        text = "Per §99.99.99 of the by-law, this is compliant."
        issues = verify_citations(text)
        assert len(issues) == 1
        assert issues[0].cited_section == "99.99.99"

    def test_multiple_issues(self):
        """Multiple bad citations should all be flagged."""
        text = (
            "Section 99.1 requires setbacks.\n"
            "Section 88.2 requires landscaping.\n"
        )
        issues = verify_citations(text)
        assert len(issues) == 2

    def test_valid_parking_section(self):
        """Parking section references should be valid."""
        text = "Per §200.5.10, the parking minimum is 0.3 spaces per unit."
        issues = verify_citations(text)
        assert len(issues) == 0

    def test_extra_valid_sections(self):
        """Extra valid sections from policy DB should be accepted."""
        text = "Per §42.99.1, the special provision applies."
        issues = verify_citations(text, extra_valid={"42.99.1"})
        assert len(issues) == 0

    def test_suggestion_provided(self):
        """Flagged citations should include a suggestion."""
        text = "Per §10.99 of the by-law."
        issues = verify_citations(text)
        assert len(issues) == 1
        assert issues[0].suggestion != ""


class TestStripUnverifiedCitations:
    """Test stripping bad citations from text."""

    def test_strips_bad_citation(self):
        text = "Per §99.99.99 of the by-law, this is compliant."
        issues = [
            CitationIssue(
                line_number=1,
                cited_section="99.99.99",
                context="Per §99.99.99 of the by-law",
                suggestion="",
            )
        ]
        result = strip_unverified_citations(text, issues)
        assert "99.99.99" not in result
        assert "[CITATION NEEDED" in result

    def test_no_issues_returns_unchanged(self):
        text = "This text has no issues."
        result = strip_unverified_citations(text, [])
        assert result == text

    def test_preserves_valid_content(self):
        text = "The building is 25m tall. Per §99.1, the maximum is 10m."
        issues = [
            CitationIssue(
                line_number=1,
                cited_section="99.1",
                context="Per §99.1",
                suggestion="",
            )
        ]
        result = strip_unverified_citations(text, issues)
        assert "25m tall" in result
        assert "99.1" not in result
