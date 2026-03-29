"""
Tests for agents.

Key concept: testing AI systems is different from testing normal code.
You CAN'T assert exact outputs because the LLM gives slightly different
responses each time. Instead, you test PROPERTIES:
  - "At least 1 finding" (not "exactly 3 findings")
  - "All findings have valid severity" (not "first finding is P0")
  - "Clean code has fewer findings" (not "clean code has 0 findings")

These tests call the real Gemini API, so they're slow (~10s each).
Run: pytest tests/test_agents.py -v -s
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.security_agent import (
    analyze_security,
    _normalize_severity,
    _normalize_line_range,
)
from models.finding import FindingType, Severity

api_key = os.getenv("GEMINI_API_KEY", "")
skip_no_key = pytest.mark.skipif(
    not api_key or api_key == "your_gemini_api_key_here",
    reason="GEMINI_API_KEY not set",
)


def load_fixture(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "fixtures", name)
    with open(path) as f:
        return f.read()


# ─── Unit tests (no API calls, instant) ─────────────────────


class TestNormalization:
    """Test the helper functions that clean up LLM output."""

    def test_severity_p0_passthrough(self):
        assert _normalize_severity("P0") == "P0"

    def test_severity_p1_passthrough(self):
        assert _normalize_severity("P1") == "P1"

    def test_severity_p2_passthrough(self):
        assert _normalize_severity("P2") == "P2"

    def test_severity_high_maps_to_p1(self):
        assert _normalize_severity("High") == "P1"

    def test_severity_critical_maps_to_p0(self):
        assert _normalize_severity("Critical") == "P0"
        assert _normalize_severity("critical") == "P0"
        assert _normalize_severity("CRITICAL") == "P0"

    def test_severity_medium_maps_to_p2(self):
        assert _normalize_severity("Medium") == "P2"

    def test_severity_low_maps_to_p2(self):
        assert _normalize_severity("Low") == "P2"

    def test_severity_unknown_defaults_to_p1(self):
        assert _normalize_severity("something_weird") == "P1"

    def test_line_range_simple(self):
        assert _normalize_line_range("5-7") == "5-7"

    def test_line_range_single(self):
        assert _normalize_line_range("42") == "42"

    def test_line_range_with_text(self):
        assert _normalize_line_range("lines 5-7") == "5-7"

    def test_line_range_with_spaces(self):
        assert _normalize_line_range("5 - 7") == "5-7"

    def test_line_range_with_comma(self):
        assert _normalize_line_range("5, 7") == "5-7"

    def test_line_range_empty_defaults(self):
        assert _normalize_line_range("") == "1"

    def test_line_range_no_numbers(self):
        assert _normalize_line_range("no numbers here") == "1"


# ─── Integration tests (calls Gemini, slow) ──────────────────


@skip_no_key
class TestSecurityAgent:

    def test_finds_vulnerabilities_in_bad_code(self):
        """Vulnerable code should produce at least 1 finding."""
        code = load_fixture("vulnerable.py")
        findings = analyze_security(code, "python")

        print(f"\n  Found {len(findings)} issues:")
        for f in findings:
            print(f"    [{f.severity.value}] {f.title}")

        # Must find something
        assert len(findings) >= 1, "Should find at least 1 vulnerability"

        # All findings should be security type
        for f in findings:
            assert f.type == FindingType.SECURITY

        # All findings should have valid severity
        for f in findings:
            assert f.severity in (Severity.P0, Severity.P1, Severity.P2)

    def test_clean_code_has_few_findings(self):
        """Clean code should produce very few findings."""
        code = load_fixture("clean.py")
        findings = analyze_security(code, "python")

        print(f"\n  Clean code findings: {len(findings)}")
        for f in findings:
            print(f"    [{f.severity.value}] {f.title}")

        # Clean code might get 0-2 minor findings (LLMs over-report sometimes)
        assert len(findings) <= 3, f"Too many findings for clean code: {len(findings)}"

    def test_never_crashes_on_weird_input(self):
        """Agent should return empty list, not crash, on weird input."""
        # Empty code
        findings = analyze_security("", "python")
        assert isinstance(findings, list)

        # Nonsense
        findings = analyze_security("asdfjkl;", "python")
        assert isinstance(findings, list)

    def test_findings_are_sorted_by_severity(self):
        """P0 findings should appear before P1 and P2."""
        code = load_fixture("vulnerable.py")
        findings = analyze_security(code, "python")

        if len(findings) >= 2:
            severity_values = [f.severity.value for f in findings]
            # P0 should come before P1, P1 before P2
            p0_indices = [i for i, s in enumerate(severity_values) if s == "P0"]
            p1_indices = [i for i, s in enumerate(severity_values) if s == "P1"]
            p2_indices = [i for i, s in enumerate(severity_values) if s == "P2"]

            if p0_indices and p1_indices:
                assert max(p0_indices) < min(p1_indices), "P0 should come before P1"
            if p1_indices and p2_indices:
                assert max(p1_indices) < min(p2_indices), "P1 should come before P2"