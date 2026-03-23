"""
Integration test: Gemini output -> Pydantic models.
Run: pytest tests/test_gemini_integration.py -v -s
"""

import sys
import os
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.llm_client import call_llm
from models.finding import Finding
from models.review import Review

api_key = os.getenv("GEMINI_API_KEY", "")
skip_no_key = pytest.mark.skipif(
    not api_key or api_key == "your_gemini_api_key_here",
    reason="GEMINI_API_KEY not set",
)

SECURITY_PROMPT = """
You are a senior security engineer reviewing code.
Analyze for SQL injection, hardcoded credentials, and secrets.

Respond ONLY with JSON:
{
  "findings": [
    {
      "type": "security",
      "severity": "P0|P1|P2",
      "title": "Short name",
      "line_range": "23-25",
      "flagged_code": "the code",
      "explanation": "Why dangerous",
      "fixed_code": "the fix"
    }
  ]
}
No markdown fences, no extra text. ONLY the JSON object.
"""


def load_fixture(name):
    path = os.path.join(os.path.dirname(__file__), "fixtures", name)
    with open(path) as f:
        return f.read()


@skip_no_key
class TestGeminiToPydantic:
    def test_vulnerable_code_findings(self):
        code = load_fixture("vulnerable.py")
        start = time.time()
        raw = call_llm(
            system_prompt=SECURITY_PROMPT,
            user_prompt=f"Review this Python code:\n\n```python\n{code}\n```",
        )
        elapsed = time.time() - start
        print(f"\n  Gemini responded in {elapsed:.1f}s")

        assert "findings" in raw
        findings = []
        for item in raw["findings"]:
            try:
                findings.append(Finding.model_validate(item))
            except Exception as e:
                print(f"  Parse error: {e}")

        assert len(findings) > 0
        review = Review(
            repo="test/vulnerable", findings=findings,
            review_duration_seconds=elapsed, agents_completed=["security"],
        )
        review.sort_findings()
        print(f"  P0={review.p0_count} P1={review.p1_count} P2={review.p2_count}")

    def test_clean_code_few_findings(self):
        code = load_fixture("clean.py")
        raw = call_llm(
            system_prompt=SECURITY_PROMPT,
            user_prompt=f"Review this Python code:\n\n```python\n{code}\n```",
        )
        assert "findings" in raw
        findings = []
        for item in raw["findings"]:
            try:
                findings.append(Finding.model_validate(item))
            except Exception:
                pass
        print(f"\n  Clean code findings: {len(findings)}")
        assert len(findings) <= 2
