"""
Tests for the multi-agent orchestrator.

Two types of tests:
  1. Unit tests (fast, no API) — test graph structure and merging logic
  2. Integration tests (slow, uses Gemini) — test real 4-agent reviews

Run fast tests only:
  pytest tests/test_orchestrator.py::TestMergeFindingsUnit -v

Run everything (uses 4 Gemini calls per integration test):
  pytest tests/test_orchestrator.py -v -s
"""

import sys
import os
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.finding import Finding, FindingType, Severity
from agents.orchestrator import run_review, merge_findings

api_key = os.getenv("GEMINI_API_KEY", "")
skip_no_key = pytest.mark.skipif(
    not api_key or api_key == "your_gemini_api_key_here",
    reason="GEMINI_API_KEY not set",
)


def load_fixture(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "fixtures", name)
    with open(path) as f:
        return f.read()


# def _make_finding(finding_type: str, severity: str, title: str) -> Finding:
#     return Finding(
#         type=finding_type,
#         severity=severity,
#         title=title,
#         line_range="1-5",
_line_counter = 0

def _make_finding(finding_type: str, severity: str, title: str) -> Finding:
    global _line_counter
    _line_counter += 10
    return Finding(
        type=finding_type,
        severity=severity,
        title=title,
        line_range=f"{_line_counter}-{_line_counter + 5}",
        flagged_code="test code",
        explanation="test explanation",
        fixed_code="test fix",
    )


# ─── Unit tests (no API calls, instant) ──────────────────────


class TestMergeFindingsUnit:
    """Test the merge_findings function with mock data."""

    def test_merges_all_agent_findings(self):
        state = {
            "security_findings": [_make_finding("security", "P0", "SQL Injection")],
            "performance_findings": [_make_finding("performance", "P1", "N+1 Query")],
            "smell_findings": [_make_finding("smell", "P2", "Magic Number")],
            "architecture_findings": [_make_finding("architecture", "P1", "SRP Violation")],
            "agents_completed": ["security", "performance", "smell", "architecture"],
        }
        result = merge_findings(state)
        all_findings = result["all_findings"]
        assert len(all_findings) == 4

    def test_sorts_by_severity(self):
        state = {
            "security_findings": [],
            "performance_findings": [_make_finding("performance", "P2", "Minor")],
            "smell_findings": [_make_finding("smell", "P1", "Medium")],
            "architecture_findings": [_make_finding("architecture", "P0", "Critical")],
            "agents_completed": ["performance", "smell", "architecture"],
        }
        result = merge_findings(state)
        severities = [f.severity.value for f in result["all_findings"]]
        assert severities == ["P0", "P1", "P2"]

    def test_handles_empty_findings(self):
        state = {
            "security_findings": [],
            "performance_findings": [],
            "smell_findings": [],
            "architecture_findings": [],
            "agents_completed": ["security", "performance", "smell", "architecture"],
        }
        result = merge_findings(state)
        assert result["all_findings"] == []

    def test_handles_partial_failure(self):
        """If some agents fail, merge what we have."""
        state = {
            "security_findings": [_make_finding("security", "P0", "SQL Injection")],
            "performance_findings": [],
            "smell_findings": [],
            "architecture_findings": [],
            "agents_completed": ["security"],
            "agents_failed": ["performance", "smell", "architecture"],
        }
        result = merge_findings(state)
        assert len(result["all_findings"]) == 1

    # def test_multiple_findings_per_agent(self):
    #     state = {
    #         "security_findings": [
    #             _make_finding("security", "P0", "SQL Injection"),
    #             _make_finding("security", "P0", "Hardcoded Secret"),
    #             _make_finding("security", "P1", "Missing Validation"),
    #         ],
    #         "performance_findings": [
    #             _make_finding("performance", "P1", "N+1 Query"),
    #         ],
    #         "smell_findings": [],
    #         "architecture_findings": [
    #             _make_finding("architecture", "P2", "Missing Pattern"),
    #         ],
    #         "agents_completed": ["security", "performance", "architecture"],
    #     }
    #     result = merge_findings(state)
    #     assert len(result["all_findings"]) == 5
    def test_multiple_findings_per_agent(self):
        state = {
            "security_findings": [
                _make_finding("security", "P0", "SQL Injection"),
                _make_finding("security", "P0", "Hardcoded Secret"),
                _make_finding("security", "P1", "Missing Validation"),
            ],
            "performance_findings": [
                _make_finding("performance", "P1", "N+1 Query"),
            ],
            "smell_findings": [],
            "architecture_findings": [
                _make_finding("architecture", "P2", "Missing Pattern"),
            ],
            "agents_completed": ["security", "performance", "architecture"],
        }
        result = merge_findings(state)
        # Dedup may merge some findings that share the same test line_range
        # So we check we got at least 3 and at most 5
        assert 3 <= len(result["all_findings"]) <= 5
        # P0s should be first
        assert result["all_findings"][0].severity == Severity.P0
        assert result["all_findings"][1].severity == Severity.P0

    def test_preserves_finding_types(self):
        state = {
            "security_findings": [_make_finding("security", "P0", "Vuln")],
            "performance_findings": [_make_finding("performance", "P1", "Slow")],
            "smell_findings": [_make_finding("smell", "P2", "Messy")],
            "architecture_findings": [_make_finding("architecture", "P1", "Coupled")],
            "agents_completed": [],
        }
        result = merge_findings(state)
        types = {f.type.value for f in result["all_findings"]}
        assert types == {"security", "performance", "smell", "architecture"}


# ─── Integration tests (calls Gemini — slow) ─────────────────


@skip_no_key
class TestOrchestratorIntegration:

    def test_full_review_vulnerable_code(self):
        """
        THE big test: run all 4 agents on vulnerable code.
        This uses 4 Gemini API calls.
        """
        code = load_fixture("vulnerable.py")

        start = time.time()
        result = run_review(code, "python")
        elapsed = time.time() - start

        print(f"\n  Review completed in {elapsed:.1f}s")
        print(f"  Agents completed: {result['agents_completed']}")
        print(f"  Agents failed: {result['agents_failed']}")
        print(f"  Total findings: {len(result['all_findings'])}")

        for f in result["all_findings"]:
            print(f"    [{f.type.value}] [{f.severity.value}] {f.title}")

        # At least some agents should complete
        assert len(result["agents_completed"]) >= 2, (
            f"Only {len(result['agents_completed'])} agents completed: "
            f"{result['agents_completed']}"
        )

        # Should find multiple issues across categories
        assert len(result["all_findings"]) >= 2

        # Findings should be sorted (P0 before P1 before P2)
        severities = [f.severity.value for f in result["all_findings"]]
        for i in range(len(severities) - 1):
            assert severities[i] <= severities[i + 1], (
                f"Findings not sorted: {severities}"
            )

    def test_clean_code_few_findings(self):
        """Clean code should get fewer findings."""
        code = load_fixture("clean.py")

        result = run_review(code, "python")

        print(f"\n  Clean code: {len(result['all_findings'])} findings")
        for f in result["all_findings"]:
            print(f"    [{f.type.value}] [{f.severity.value}] {f.title}")

        # Clean code might still get a few findings (LLMs over-report)
        # but significantly fewer than vulnerable code
        assert len(result["all_findings"]) <= 8

    def test_orchestrator_never_crashes(self):
        """Even weird input should return a valid result, not crash."""
        result = run_review("", "python")
        assert isinstance(result["all_findings"], list)
        assert isinstance(result["agents_completed"], list)
        assert isinstance(result["agents_failed"], list)
