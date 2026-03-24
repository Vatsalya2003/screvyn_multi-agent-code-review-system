"""
Security Agent — scans code for vulnerabilities.

This is the FIRST of 4 agents. The pattern you build here will be
copied for performance_agent, smell_agent, and architecture_agent
in Phase 4. So getting this right matters.

How an agent works:
  1. Receives code + language as input
  2. Builds a detailed system prompt (the agent's "expertise")
  3. Builds a user prompt (the actual code to analyze)
  4. Calls Gemini via call_llm() and gets raw JSON back
  5. Normalizes the raw JSON (fix field names, map severities)
  6. Validates each finding through the Pydantic Finding model
  7. Returns a list of validated Finding objects

Why a separate agent file instead of putting this in the API route?
  - Separation of concerns: the route handles HTTP, the agent handles analysis
  - Reusability: the agent can be called from the API, from Celery tasks,
    from CLI tools, or from tests — it doesn't care who's calling it
  - Testability: you can test the agent without starting a web server
"""

import logging
import re
from typing import Optional

from core.llm_client import call_llm
from models.finding import Finding, FindingType, Severity

logger = logging.getLogger(__name__)


# ─── The System Prompt ───────────────────────────────────────
#
# This is the agent's "brain". It tells Gemini what role to play,
# what to look for, and exactly how to format the response.
#
# Key principles for good agent prompts:
# 1. Be specific about the role ("senior security engineer")
# 2. List exactly what to look for (OWASP, secrets, etc.)
# 3. Give ONE concrete JSON example with the exact field names
# 4. Explicitly ban unwanted formats ("never use High/Medium/Low")
# 5. Tell it what to do when there's nothing to report
#
SYSTEM_PROMPT = """
You are a senior security engineer at a top tech company, reviewing code
for security vulnerabilities. You have 15 years of experience with OWASP,
penetration testing, and secure code review.

Analyze the provided code for:
- SQL injection, command injection, code injection
- Hardcoded credentials, API keys, passwords, secrets, tokens
- Cross-site scripting (XSS) vulnerabilities
- Insecure deserialization
- Path traversal / directory traversal
- Missing input validation on user-facing endpoints
- Authentication and authorization bypasses
- Sensitive data exposure in logs or error messages
- Use of known-vulnerable functions or libraries

For each vulnerability found, respond with ONLY a JSON object using
this EXACT structure. Do not rename any fields:

{"findings": [{"type": "security", "severity": "P0", "title": "SQL Injection in get_user", "line_range": "5-7", "flagged_code": "db.execute(f'SELECT * FROM users WHERE id={uid}')", "explanation": "User input is directly interpolated into the SQL query string. An attacker can pass uid=1; DROP TABLE users to destroy data or uid=1 OR 1=1 to bypass authentication and access all records.", "fixed_code": "db.execute('SELECT * FROM users WHERE id = ?', (uid,))"}]}

STRICT RULES:
- "type" must always be "security"
- "severity" must be exactly "P0", "P1", or "P2" — NEVER use "High", "Medium", "Low", "Critical"
- "line_range" must be digits only like "5" or "5-7" — not "lines 5-7" or "line 5 to 7"
- "flagged_code" must be the actual code snippet, not a description
- "fixed_code" must be working corrected code, not a description of the fix
- Return ONLY the JSON object — no markdown fences, no explanation before or after

Severity guide:
- P0 (critical): SQL injection, RCE, hardcoded secrets, auth bypass — exploitable immediately
- P1 (high): Missing input validation on public endpoints, XSS, path traversal
- P2 (medium): Sensitive data in logs, weak crypto, missing rate limiting

If no security issues are found, return: {"findings": []}
"""


def _normalize_severity(raw_severity: str) -> str:
    """
    Convert whatever the LLM returns into P0/P1/P2.

    Why this exists: Despite our prompt saying "never use High/Medium/Low",
    Gemini sometimes ignores that instruction. Instead of failing, we map
    common alternatives to our severity scale. This makes the agent robust
    against LLM non-determinism.

    Examples:
        "P0" → "P0"  (already correct)
        "High" → "P1"
        "Critical" → "P0"
        "low" → "P2"
        "Medium" → "P2"
    """
    severity_map = {
        # Already correct
        "P0": "P0", "P1": "P1", "P2": "P2",
        # Common LLM alternatives
        "critical": "P0", "CRITICAL": "P0",
        "high": "P1", "HIGH": "P1",
        "medium": "P2", "MEDIUM": "P2",
        "low": "P2", "LOW": "P2",
        # Sometimes LLMs return these
        "severe": "P0", "important": "P1", "minor": "P2",
    }
    return severity_map.get(raw_severity, severity_map.get(raw_severity.lower(), "P1"))


def _normalize_line_range(raw_range: str) -> str:
    """
    Clean up the line_range field to match our regex pattern: ^\d+(-\d+)?$

    Why this exists: The LLM sometimes returns "lines 5-7" or "5 - 7" or
    "line 5" instead of the clean "5-7" format our Pydantic model requires.
    Instead of rejecting the finding, we clean it up.

    Examples:
        "5-7" → "5-7"     (already correct)
        "lines 5-7" → "5-7"
        "5 - 7" → "5-7"
        "line 5" → "5"
        "5, 7" → "5-7"
    """
    # Extract all numbers from the string
    numbers = re.findall(r"\d+", str(raw_range))
    if not numbers:
        return "1"  # Fallback: if no numbers found, default to line 1
    if len(numbers) == 1:
        return numbers[0]
    # Use first and last number as the range
    return f"{numbers[0]}-{numbers[-1]}"


def _parse_findings(raw_findings: list[dict]) -> list[Finding]:
    """
    Convert raw JSON dicts from the LLM into validated Finding objects.

    Why a separate function? Because LLM output is messy. Fields might be
    missing, named differently, or have wrong types. This function handles
    all that normalization in one place instead of scattering try/except
    blocks everywhere.

    Strategy: try to salvage every finding. Only skip a finding if it's
    truly unparseable. A review with 4 out of 5 findings is better than
    crashing with 0 findings because one was malformed.
    """
    findings = []
    for i, raw in enumerate(raw_findings):
        try:
            # Normalize fields that the LLM commonly gets wrong
            finding = Finding(
                type=FindingType.SECURITY,
                severity=_normalize_severity(raw.get("severity", "P1")),
                title=raw.get("title", "Security Issue")[:200],
                line_range=_normalize_line_range(raw.get("line_range", "1")),
                flagged_code=raw.get("flagged_code", raw.get("code", "N/A")),
                explanation=raw.get("explanation", raw.get("description", "No explanation provided")),
                fixed_code=raw.get("fixed_code", raw.get("recommendation", "No fix provided")),
                owasp_ref=raw.get("owasp_ref"),
            )
            findings.append(finding)
        except Exception as e:
            # Log the error but don't crash — other findings may be fine
            logger.warning(
                "Failed to parse security finding %d: %s. Raw: %s",
                i, str(e)[:100], str(raw)[:200],
            )
    return findings


def analyze_security(
    code: str,
    language: str = "python",
    ast_context: Optional[str] = None,
) -> list[Finding]:
    """
    Analyze code for security vulnerabilities.

    This is the main entry point — the function every other part of the
    system calls. It's designed to NEVER raise an exception. If Gemini
    fails, if JSON parsing fails, if everything breaks — it returns an
    empty list. The caller always gets a valid result.

    Args:
        code: The source code to analyze (string)
        language: Programming language ("python", "javascript", etc.)
        ast_context: Optional AST information (Phase 3 — not used yet)

    Returns:
        List of Finding objects, sorted by severity (P0 first)
    """
    # Build the user prompt with the code and metadata
    user_prompt = f"Review this {language} code for security vulnerabilities:\n\n"
    user_prompt += f"```{language}\n{code}\n```"

    # If we have AST context (Phase 3+), include it
    if ast_context:
        user_prompt += f"\n\nAST analysis:\n{ast_context}"

    try:
        # Call Gemini through our wrapper
        raw_result = call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # Extract the findings array
        raw_findings = raw_result.get("findings", [])
        if not isinstance(raw_findings, list):
            logger.warning("Gemini returned 'findings' as %s, not list", type(raw_findings))
            return []

        # Parse and validate each finding
        findings = _parse_findings(raw_findings)

        # Sort by severity: P0 first, then P1, then P2
        severity_order = {"P0": 0, "P1": 1, "P2": 2}
        findings.sort(key=lambda f: severity_order.get(f.severity.value, 99))

        logger.info(
            "Security agent found %d issues (P0=%d, P1=%d, P2=%d)",
            len(findings),
            sum(1 for f in findings if f.severity == Severity.P0),
            sum(1 for f in findings if f.severity == Severity.P1),
            sum(1 for f in findings if f.severity == Severity.P2),
        )
        return findings

    except Exception as e:
        # NEVER crash — always return a valid (possibly empty) result
        logger.error("Security agent failed: %s", str(e)[:200])
        return []