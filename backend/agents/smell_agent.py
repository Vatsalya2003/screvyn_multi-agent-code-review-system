"""
Code Smell Agent — finds maintainability and readability problems.

Catches: dead code, god classes, long functions, magic numbers,
deep nesting, poor naming, redundant conditions.
"""

import logging
import re
from typing import Optional

from core.llm_client import call_llm
from models.finding import Finding, FindingType, Severity

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a senior developer doing a thorough code quality review.
You care about code that is easy to read, maintain, and extend.

Analyze the provided code for:
- Dead code and unreachable branches (code that never executes)
- God classes (classes doing too many unrelated things — more than 5 methods
  that serve different purposes indicates SRP violation)
- Functions over 40 lines (hard to read, test, and maintain)
- Magic numbers and unexplained constants (raw numbers without named constants)
- Redundant or inverted boolean conditions
- Deeply nested code (more than 3 levels of indentation)
- Naming that violates language conventions (e.g. camelCase in Python)
- Duplicated logic that should be extracted into a shared function

Respond with ONLY a JSON object using this EXACT structure:

{"findings": [{"type": "smell", "severity": "P2", "title": "God Class UserManager", "line_range": "43-70", "flagged_code": "class UserManager with 10 unrelated methods", "explanation": "This class handles user CRUD, email sending, report generation, database backups, payment processing, and image resizing. These are 6 different responsibilities in one class, making it impossible to test or modify one concern without risking the others.", "fixed_code": "Split into UserRepository, EmailService, ReportGenerator, BackupService, PaymentService, ImageProcessor"}]}

STRICT RULES:
- "type" must always be "smell"
- "severity" must be exactly "P0", "P1", or "P2" — NEVER "High"/"Medium"/"Low"
- "line_range" must be digits like "5" or "5-7"
- Return ONLY the JSON object — no markdown, no extra text

Severity guide:
- P0: Critical — never assign P0 for code smells (smells are not security/crash risks)
- P1: Functions over 50 lines, god classes with 6+ responsibilities, deeply nested logic
- P2: Magic numbers, dead code, minor naming issues, small duplications

If no code smells found, return: {"findings": []}
"""


def _normalize_severity(raw: str) -> str:
    severity_map = {
        "P0": "P0", "P1": "P1", "P2": "P2",
        "critical": "P0", "CRITICAL": "P0",
        "high": "P1", "HIGH": "P1",
        "medium": "P2", "MEDIUM": "P2",
        "low": "P2", "LOW": "P2",
    }
    return severity_map.get(raw, severity_map.get(raw.lower(), "P2"))


def _normalize_line_range(raw: str) -> str:
    numbers = re.findall(r"\d+", str(raw))
    if not numbers:
        return "1"
    if len(numbers) == 1:
        return numbers[0]
    return f"{numbers[0]}-{numbers[-1]}"


def _parse_findings(raw_findings: list[dict]) -> list[Finding]:
    findings = []
    for i, raw in enumerate(raw_findings):
        try:
            finding = Finding(
                type=FindingType.SMELL,
                severity=_normalize_severity(raw.get("severity", "P2")),
                title=raw.get("title", "Code Smell")[:200],
                line_range=_normalize_line_range(raw.get("line_range", "1")),
                flagged_code=raw.get("flagged_code", raw.get("code", "N/A")),
                explanation=raw.get("explanation", raw.get("description", "No explanation")),
                fixed_code=raw.get("fixed_code", raw.get("recommendation", "No fix")),
            )
            findings.append(finding)
        except Exception as e:
            logger.warning("Failed to parse smell finding %d: %s", i, str(e)[:100])
    return findings


def analyze_smell(
    code: str,
    language: str = "python",
    ast_context: Optional[str] = None,
) -> list[Finding]:
    """Analyze code for code smells. Never crashes."""
    user_prompt = f"Review this {language} code for code smells and maintainability issues:\n\n"
    user_prompt += f"```{language}\n{code}\n```"
    if ast_context:
        user_prompt += f"\n\nAST analysis:\n{ast_context}"

    try:
        raw_result = call_llm(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
        raw_findings = raw_result.get("findings", [])
        if not isinstance(raw_findings, list):
            return []
        findings = _parse_findings(raw_findings)
        severity_order = {"P0": 0, "P1": 1, "P2": 2}
        findings.sort(key=lambda f: severity_order.get(f.severity.value, 99))
        logger.info(
            "Smell agent found %d issues (P0=%d, P1=%d, P2=%d)",
            len(findings),
            sum(1 for f in findings if f.severity == Severity.P0),
            sum(1 for f in findings if f.severity == Severity.P1),
            sum(1 for f in findings if f.severity == Severity.P2),
        )
        return findings
    except Exception as e:
        logger.error("Smell agent failed: %s", str(e)[:200])
        return []
