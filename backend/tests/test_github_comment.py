"""
Tests for GitHub PR comment formatter.
Run: pytest tests/test_github_comment.py -v
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.finding import Finding, Severity
from models.review import Review
from notifications.github_comment_formatter import (
    format_review_comment,
    format_review_comment_short,
    _format_single_finding,
)


def _make(
    finding_type: str = "security",
    severity: str = "P0",
    title: str = "SQL Injection in get_user",
    line_range: str = "12-14",
    flagged_code: str = "db.execute(f'SELECT * FROM users WHERE id={uid}')",
    explanation: str = "User input goes directly into the SQL query. An attacker passes uid=\"1; DROP TABLE users\" and your users table is gone.",
    fixed_code: str = "db.execute('SELECT * FROM users WHERE id = ?', (uid,))",
) -> Finding:
    return Finding(
        type=finding_type, severity=severity, title=title,
        line_range=line_range, flagged_code=flagged_code,
        explanation=explanation, fixed_code=fixed_code,
    )


class TestSingleFinding:

    def test_header_has_severity_and_category(self):
        finding = _make(severity="P0", finding_type="security")
        output = _format_single_finding(finding, 0)
        assert "### blocking | Security:" in output

    def test_header_has_performance_category(self):
        finding = _make(severity="P1", finding_type="performance", title="N+1 Query")
        output = _format_single_finding(finding, 0)
        assert "### important | Performance:" in output

    def test_header_has_smell_category(self):
        finding = _make(severity="P2", finding_type="smell", title="Magic Number")
        output = _format_single_finding(finding, 0)
        assert "### nit | Code Quality:" in output

    def test_header_has_architecture_category(self):
        finding = _make(severity="P1", finding_type="architecture", title="SRP Violation")
        output = _format_single_finding(finding, 0)
        assert "### important | Architecture:" in output

    def test_header_has_location(self):
        finding = _make(line_range="12-14")
        output = _format_single_finding(finding, 0)
        assert "(line 12-14)" in output

    def test_includes_explanation(self):
        finding = _make(explanation="This is a clear explanation of the problem.")
        output = _format_single_finding(finding, 0)
        assert "This is a clear explanation" in output

    def test_includes_flagged_code(self):
        finding = _make(flagged_code="bad_code()")
        output = _format_single_finding(finding, 0)
        assert "**Flagged code:**" in output
        assert "bad_code()" in output

    def test_includes_recommended_fix(self):
        finding = _make(fixed_code="good_code()")
        output = _format_single_finding(finding, 0)
        assert "**Recommended fix:**" in output
        assert "good_code()" in output

    def test_skips_na_code(self):
        finding = _make(flagged_code="N/A", fixed_code="N/A")
        output = _format_single_finding(finding, 0)
        assert "**Flagged code:**" not in output
        assert "**Recommended fix:**" not in output

    def test_shows_complexity(self):
        finding = Finding(
            type="performance", severity="P1", title="O(n^2) loop",
            line_range="20-25", flagged_code="nested loop",
            explanation="quadratic complexity", fixed_code="use a set",
            complexity_before="O(n^2)", complexity_after="O(n)",
        )
        output = _format_single_finding(finding, 0)
        assert "O(n^2)" in output
        assert "O(n)" in output

    def test_shows_pattern_suggestion(self):
        finding = Finding(
            type="architecture", severity="P1", title="SRP Violation",
            line_range="40-80", flagged_code="class Manager",
            explanation="too many responsibilities",
            fixed_code="split into services",
            pattern_suggestion="Repository Pattern",
        )
        output = _format_single_finding(finding, 0)
        assert "Consider: Repository Pattern" in output

    def test_shows_owasp_ref(self):
        finding = Finding(
            type="security", severity="P0", title="SQL Injection",
            line_range="12", flagged_code="f-string query",
            explanation="injection risk", fixed_code="parameterized",
            owasp_ref="A03:2021",
        )
        output = _format_single_finding(finding, 0)
        assert "A03:2021" in output

    def test_truncates_long_explanation(self):
        long_text = "This is a problem sentence. " * 25
        finding = _make(explanation=long_text)
        output = _format_single_finding(finding, 0)
        explanation_part = output.split("**Flagged code:**")[0]
        assert len(explanation_part) < 600


class TestFullReviewComment:

    def test_clean_review(self):
        review = Review(repo="test/repo", findings=[])
        output = format_review_comment(review)
        assert "no security issues" in output.lower() or "no issues" in output.lower()

    def test_summary_shows_counts(self):
        review = Review(
            repo="test/repo",
            findings=[
                _make(severity="P0"),
                _make(severity="P1", title="N+1", line_range="20"),
            ],
            agents_completed=["security", "performance"],
        )
        output = format_review_comment(review)
        assert "1 blocking" in output.lower()
        assert "1 important" in output

    def test_blocking_warning_for_p0(self):
        review = Review(
            repo="test/repo",
            findings=[_make(severity="P0")],
            agents_completed=["security"],
        )
        output = format_review_comment(review)
        assert "blocking issues" in output.lower()

    def test_no_warning_without_p0(self):
        review = Review(
            repo="test/repo",
            findings=[_make(severity="P2", title="Minor", line_range="50", finding_type="smell")],
            agents_completed=["smell"],
        )
        output = format_review_comment(review)
        assert "blocking issues" not in output.lower()

    def test_has_separators(self):
        review = Review(
            repo="test/repo",
            findings=[
                _make(severity="P0", line_range="5"),
                _make(severity="P1", title="Other Issue", line_range="20"),
            ],
            agents_completed=["security"],
        )
        output = format_review_comment(review)
        assert "---" in output

    def test_has_agent_attribution(self):
        review = Review(
            repo="test/repo",
            findings=[_make()],
            agents_completed=["security", "performance"],
            review_duration_seconds=14.2,
        )
        output = format_review_comment(review)
        assert "security, performance" in output
        assert "Screvyn" in output

    def test_no_pure_ai_patterns(self):
        review = Review(
            repo="test/repo",
            findings=[
                _make(severity="P0"),
                _make(severity="P1", title="N+1", line_range="20",
                      finding_type="performance",
                      explanation="Classic N+1. You hit the DB once per user.",
                      fixed_code="batch query"),
            ],
            agents_completed=["security", "performance"],
            review_duration_seconds=18.0,
        )
        output = format_review_comment(review)
        bad_patterns = [
            "I've identified", "I've detected",
            "It's worth noting", "Furthermore,",
            "## Summary", "## Findings",
            "Executive Summary",
        ]
        for pattern in bad_patterns:
            assert pattern not in output, f"AI pattern found: '{pattern}'"


class TestShortFormat:

    def test_clean_review(self):
        review = Review(repo="test/repo", findings=[])
        output = format_review_comment_short(review)
        assert "no issues" in output.lower()

    def test_shows_counts(self):
        review = Review(
            repo="test/repo",
            findings=[
                _make(severity="P0"),
                _make(severity="P1", title="N+1", line_range="20"),
                _make(severity="P2", title="Nit", line_range="50", finding_type="smell"),
            ],
        )
        output = format_review_comment_short(review)
        assert "1 blocking" in output
        assert "1 important" in output
        assert "1 nit" in output

    def test_includes_location(self):
        review = Review(
            repo="test/repo",
            findings=[_make(line_range="12-14")],
        )
        output = format_review_comment_short(review)
        assert "(line 12-14)" in output

    def test_includes_category(self):
        review = Review(
            repo="test/repo",
            findings=[_make(finding_type="security")],
        )
        output = format_review_comment_short(review)
        assert "Security" in output

    def test_includes_explanation(self):
        review = Review(
            repo="test/repo",
            findings=[_make(explanation="User input in SQL query. DB is exposed.")],
        )
        output = format_review_comment_short(review)
        assert "User input in SQL query" in output

    def test_includes_fix(self):
        review = Review(
            repo="test/repo",
            findings=[_make(fixed_code="db.execute('SELECT * WHERE id = ?', (uid,))")],
        )
        output = format_review_comment_short(review)
        assert "Fix:" in output
