"""Tests for Pydantic models. Run: pytest tests/test_models.py -v"""

import json
import sys
import os

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.finding import Finding, FindingType, Severity
from models.review import Review


class TestFinding:
    def test_valid_finding(self):
        f = Finding(
            type="security", severity="P0",
            title="SQL Injection in get_user", line_range="23-25",
            flagged_code="f'SELECT {uid}'",
            explanation="Direct interpolation", fixed_code="parameterized",
        )
        assert f.type == FindingType.SECURITY
        assert f.severity == Severity.P0

    def test_single_line_range(self):
        f = Finding(
            type="performance", severity="P1", title="N+1 query",
            line_range="47", flagged_code="x", explanation="y", fixed_code="z",
        )
        assert f.line_range == "47"

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError):
            Finding(
                type="security", severity="P3", title="Test",
                line_range="1", flagged_code="x", explanation="y", fixed_code="z",
            )

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            Finding(
                type="style", severity="P2", title="Bad naming",
                line_range="1", flagged_code="x", explanation="y", fixed_code="z",
            )

    def test_invalid_line_range_rejected(self):
        with pytest.raises(ValidationError):
            Finding(
                type="security", severity="P0", title="Test",
                line_range="lines 23 to 25", flagged_code="x",
                explanation="y", fixed_code="z",
            )

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            Finding(
                type="security", severity="P0", title="",
                line_range="1", flagged_code="x", explanation="y", fixed_code="z",
            )

    def test_optional_fields_default_none(self):
        f = Finding(
            type="smell", severity="P2", title="Dead code",
            line_range="10-15", flagged_code="if False: pass",
            explanation="Unreachable", fixed_code="removed",
        )
        assert f.owasp_ref is None
        assert f.complexity_before is None

    def test_json_round_trip(self):
        original = Finding(
            type="performance", severity="P1", title="N+1 query",
            line_range="19-24", flagged_code="loop query",
            explanation="N queries", fixed_code="batch",
            complexity_before="O(n)", complexity_after="O(1)",
        )
        restored = Finding.model_validate_json(original.model_dump_json())
        assert restored == original


class TestReview:
    def _make_findings(self):
        return [
            Finding(type="security", severity="P0", title="SQL Injection",
                    line_range="14", flagged_code="x", explanation="y", fixed_code="z"),
            Finding(type="performance", severity="P1", title="N+1 Query",
                    line_range="19-24", flagged_code="x", explanation="y", fixed_code="z"),
            Finding(type="performance", severity="P1", title="O(n2) Loop",
                    line_range="27-32", flagged_code="x", explanation="y", fixed_code="z"),
            Finding(type="smell", severity="P2", title="Magic Numbers",
                    line_range="36-40", flagged_code="x", explanation="y", fixed_code="z"),
            Finding(type="architecture", severity="P1", title="God Class",
                    line_range="43-70", flagged_code="x", explanation="y", fixed_code="z"),
        ]

    def test_severity_counts(self):
        r = Review(repo="test/repo", findings=self._make_findings())
        assert r.p0_count == 1
        assert r.p1_count == 3
        assert r.p2_count == 1
        assert r.total_findings == 5
        assert r.has_critical is True

    def test_empty_review(self):
        r = Review(repo="test/clean")
        assert r.total_findings == 0
        assert r.has_critical is False

    def test_sort_findings(self):
        findings = self._make_findings()
        findings.reverse()
        r = Review(repo="test/repo", findings=findings)
        r.sort_findings()
        sevs = [f.severity for f in r.findings]
        assert sevs == [Severity.P0, Severity.P1, Severity.P1, Severity.P1, Severity.P2]

    def test_json_serialization(self):
        r = Review(
            repo="acme/backend", pr_number=42,
            findings=self._make_findings(),
            agents_completed=["security", "performance"],
        )
        data = json.loads(r.model_dump_json())
        assert data["p0_count"] == 1
        assert data["total_findings"] == 5
