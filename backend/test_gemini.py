"""
Raw Gemini test — run this FIRST before building anything else.
Run: python test_gemini.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from core.llm_client import call_llm

VULNERABLE_CODE = """
import sqlite3
DB_PASSWORD = "super_secret_123"
API_KEY = "sk-1234567890abcdef"

def get_user(user_id):
    conn = sqlite3.connect('app.db')
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = conn.execute(query)
    return result.fetchone()
"""

SYSTEM_PROMPT = """
You are a senior security engineer reviewing code for vulnerabilities.
Analyze the provided code for:
- SQL injection, command injection
- Hardcoded credentials, API keys, secrets
- Other security issues

Respond ONLY with a JSON object in this exact format, no other text:
{
  "findings": [
    {
      "type": "security",
      "severity": "P0",
      "title": "Short issue name",
      "line_range": "10-12",
      "flagged_code": "the problematic code",
      "explanation": "Why this is dangerous",
      "fixed_code": "the corrected code"
    }
  ]
}

Return ONLY the JSON object. No markdown, no explanation, no code fences.
"""


def run_test(round_num: int) -> bool:
    print(f"\n{'='*50}")
    print(f"  Round {round_num}/5")
    print(f"{'='*50}")

    try:
        result = call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"Review this Python code:\n\n```python\n{VULNERABLE_CODE}\n```",
        )

        if "findings" not in result:
            print(f"  FAIL: Missing 'findings' key")
            return False

        findings = result["findings"]
        print(f"  Found {len(findings)} issues:")
        for f in findings:
            sev = f.get("severity", "??")
            title = f.get("title", "No title")
            print(f"    [{sev}] {title}")

        if len(findings) >= 2:
            print(f"  PASS")
            return True
        else:
            print(f"  WEAK: Only {len(findings)} issues (expected 2+)")
            return True

    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def main():
    print("=" * 50)
    print("  Screvyn - Gemini API Test")
    print("=" * 50)

    from core.config import settings
    key = settings.gemini_api_key
    print(f"\n  API key: {key[:8]}...{key[-4:]}")
    print(f"  Model: {settings.gemini_model}")

    successes = 0
    for i in range(1, 6):
        if run_test(i):
            successes += 1

    print(f"\n{'='*50}")
    print(f"  Results: {successes}/5 valid JSON responses")
    print(f"{'='*50}")

    if successes >= 4:
        print("\n  PASS - Proceed to Phase 1c.\n")
    elif successes >= 3:
        print("\n  ACCEPTABLE - Consider tightening the prompt.\n")
    else:
        print("\n  FAIL - Fix before continuing.")
        print("  Try: GEMINI_MODEL=gemini-1.5-flash in .env\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
