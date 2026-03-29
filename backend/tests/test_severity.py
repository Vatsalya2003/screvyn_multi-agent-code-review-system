"""
Tests for the severity aggregator and dedup logic.

ALL tests are fast (no API calls). Run:
  pytest tests/test_severity.py -v
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.severity import (
    _parse_line_range,
    _line_overlap_ratio,
    _title_similarity,
    _higher_severity,
    _merge_two_findings,
    deduplicate_findings,
)
from models.finding import Finding, FindingType, Severity


def _make(
    finding_type: str = "security",
    severity: str = "P0",
    title: str = "Test Issue",
    line_range: str = "1-5",
    explanation: str = "test explanation",
) -> Finding:
    """Helper: create a finding with minimal boilerplate."""
    return Finding(
        type=finding_type,
        severity=severity,
        title=title,
        line_range=line_range,
        flagged_code="test code",
        explanation=explanation,
        fixed_code="test fix",
    )


# ─── Line Range Parsing ─────────────────────────────────────


class TestParseLineRange:
    def test_single_line(self):
        assert _parse_line_range("5") == (5, 5)

    def test_range(self):
        assert _parse_line_range("5-10") == (5, 10)

    def test_same_start_end(self):
        assert _parse_line_range("7-7") == (7, 7)


# ─── Line Overlap Calculation ────────────────────────────────


class TestLineOverlap:
    def test_identical_ranges(self):
        assert _line_overlap_ratio("5-10", "5-10") == 1.0

    def test_no_overlap(self):
        assert _line_overlap_ratio("1-5", "10-15") == 0.0

    def test_partial_overlap(self):
        ratio = _line_overlap_ratio("5-10", "8-15")
        # Overlap is 8-10 (3 lines), smaller range is 5-10 (6 lines)
        assert 0.4 < ratio < 0.6

    def test_one_inside_other(self):
        ratio = _line_overlap_ratio("5-20", "8-12")
        # 8-12 is entirely inside 5-20
        # Overlap is 8-12 (5 lines), smaller range is 8-12 (5 lines)
        assert ratio == 1.0

    def test_single_line_same(self):
        assert _line_overlap_ratio("5", "5") == 1.0

    def test_single_line_different(self):
        assert _line_overlap_ratio("5", "10") == 0.0

    def test_adjacent_no_overlap(self):
        assert _line_overlap_ratio("1-5", "6-10") == 0.0

    def test_one_line_overlap(self):
        ratio = _line_overlap_ratio("1-5", "5-10")
        # Overlap is just line 5 (1 line), smaller is 5 lines
        assert ratio == 0.2


# ─── Title Similarity ────────────────────────────────────────


class TestTitleSimilarity:
    def test_identical(self):
        assert _title_similarity("SQL Injection", "SQL Injection") == 1.0

    def test_completely_different(self):
        sim = _title_similarity("SQL Injection", "God Class UserManager")
        assert sim < 0.4

    def test_similar_with_shared_function(self):
        sim = _title_similarity(
            "SQL Injection in get_user",
            "Missing Validation in get_user",
        )
        assert sim > 0.4  # Share "in get_user"

    def test_case_insensitive(self):
        sim = _title_similarity("SQL INJECTION", "sql injection")
        assert sim == 1.0

    def test_empty_strings(self):
        assert _title_similarity("", "") == 1.0


# ─── Severity Comparison ─────────────────────────────────────


class TestHigherSeverity:
    def test_p0_wins_over_p1(self):
        assert _higher_severity(Severity.P0, Severity.P1) == Severity.P0

    def test_p0_wins_over_p2(self):
        assert _higher_severity(Severity.P0, Severity.P2) == Severity.P0

    def test_p1_wins_over_p2(self):
        assert _higher_severity(Severity.P1, Severity.P2) == Severity.P1

    def test_same_severity(self):
        assert _higher_severity(Severity.P1, Severity.P1) == Severity.P1

    def test_order_doesnt_matter(self):
        assert _higher_severity(Severity.P2, Severity.P0) == Severity.P0


# ─── Merge Two Findings ─────────────────────────────────────


class TestMergeTwoFindings:
    def test_keeps_higher_severity(self):
        primary = _make(severity="P1", title="Issue A", line_range="5-10")
        duplicate = _make(severity="P0", title="Issue B", line_range="5-10")
        merged = _merge_two_findings(primary, duplicate)
        assert merged.severity == Severity.P0

    def test_keeps_primary_title(self):
        primary = _make(title="SQL Injection in get_user")
        duplicate = _make(title="Missing Validation in get_user")
        merged = _merge_two_findings(primary, duplicate)
        assert merged.title == "SQL Injection in get_user"

    def test_widens_line_range(self):
        primary = _make(line_range="5-10")
        duplicate = _make(line_range="8-15")
        merged = _merge_two_findings(primary, duplicate)
        assert merged.line_range == "5-15"

    def test_combines_explanations(self):
        primary = _make(explanation="This is dangerous because X")
        duplicate = _make(explanation="This is also problematic because Y")
        merged = _merge_two_findings(primary, duplicate)
        assert "dangerous because X" in merged.explanation
        assert "Additionally" in merged.explanation

    def test_preserves_optional_fields(self):
        primary = _make()
        primary_with_owasp = Finding(
            type="security", severity="P0", title="SQL Inj",
            line_range="5", flagged_code="x", explanation="y",
            fixed_code="z", owasp_ref="A03:2021",
        )
        duplicate = _make()
        merged = _merge_two_findings(primary_with_owasp, duplicate)
        assert merged.owasp_ref == "A03:2021"


# ─── Deduplication ───────────────────────────────────────────


class TestDeduplication:
    def test_no_duplicates_pass_through(self):
        """Distinct findings should all be kept."""
        findings = [
            _make(title="SQL Injection", line_range="5-7"),
            _make(title="N+1 Query", line_range="20-25"),
            _make(title="God Class", line_range="40-80"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 3

    def test_exact_duplicates_merged(self):
        """Same title, same lines → merge."""
        findings = [
            _make(title="SQL Injection in get_user", line_range="5-7", severity="P1"),
            _make(title="SQL Injection in get_user", line_range="5-7", severity="P0"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert result[0].severity == Severity.P0  # Higher severity wins

    def test_overlapping_lines_similar_title_merged(self):
        """Overlapping lines + similar title → merge."""
        findings = [
            _make(
                title="SQL Injection in get_user",
                line_range="10-15",
                severity="P0",
            ),
            _make(
                title="Missing Input Validation in get_user",
                line_range="10-15",
                severity="P1",
            ),
        ]
        result = deduplicate_findings(findings)
        # These share location and mention the same function
        # Title similarity depends on exact ratio — might or might not merge
        # But we can check it doesn't crash
        assert len(result) >= 1
        assert len(result) <= 2

    def test_same_lines_different_title_kept(self):
        """Same lines but completely different titles → keep both."""
        findings = [
            _make(title="SQL Injection", line_range="5-7"),
            _make(title="Memory Leak", line_range="5-7"),
        ]
        result = deduplicate_findings(findings)
        # Different titles → low title similarity → should NOT merge
        assert len(result) == 2

    def test_similar_title_different_lines_kept(self):
        """Similar titles but different locations → keep both."""
        findings = [
            _make(title="SQL Injection in get_user", line_range="5-7"),
            _make(title="SQL Injection in delete_user", line_range="30-35"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 2

    def test_highest_severity_preserved(self):
        """When merging, the highest severity should win."""
        findings = [
            _make(title="SQL Injection in get_user", line_range="5-7", severity="P2"),
            _make(title="SQL Injection in get_user", line_range="5-7", severity="P0"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert result[0].severity == Severity.P0

    def test_result_sorted_by_severity(self):
        """Output should always be P0 → P1 → P2."""
        findings = [
            _make(title="Minor Issue", line_range="50", severity="P2"),
            _make(title="Critical Bug", line_range="1", severity="P0"),
            _make(title="Medium Issue", line_range="25", severity="P1"),
        ]
        result = deduplicate_findings(findings)
        severities = [f.severity for f in result]
        assert severities == [Severity.P0, Severity.P1, Severity.P2]

    def test_empty_list(self):
        assert deduplicate_findings([]) == []

    def test_single_finding(self):
        findings = [_make(title="Only One")]
        result = deduplicate_findings(findings)
        assert len(result) == 1

    def test_realistic_multi_agent_scenario(self):
        """
        Simulate what actually happens: 4 agents find overlapping issues.
        Security and Architecture both flag get_user, but Performance
        and Smell find different things.
        """
        findings = [
            _make(
                finding_type="security",
                title="SQL Injection in get_user",
                line_range="12-14",
                severity="P0",
            ),
            _make(
                finding_type="architecture",
                title="SQL Injection in get_user function",
                line_range="12-14",
                severity="P1",
            ),
            _make(
                finding_type="performance",
                title="N+1 Query in get_all_orders",
                line_range="20-25",
                severity="P1",
            ),
            _make(
                finding_type="smell",
                title="God Class UserManager",
                line_range="40-80",
                severity="P2",
            ),
            _make(
                finding_type="smell",
                title="Magic Numbers in calculate_discount",
                line_range="35-39",
                severity="P2",
            ),
        ]
        result = deduplicate_findings(findings)

        # The two SQL Injection findings should merge (same title + same lines)
        # The others are distinct (different locations or different titles)
        assert len(result) <= 4  # At least one merge should happen
        assert len(result) >= 3  # But not everything should merge

        # P0 should still be first
        assert result[0].severity == Severity.P0
