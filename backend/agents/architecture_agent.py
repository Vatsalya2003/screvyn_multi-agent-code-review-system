"""
Architecture Agent — finds design and structural problems.

Catches: SOLID violations, tight coupling, missing patterns,
circular dependencies, business logic in wrong layers.
"""

import logging
import re
from typing import Optional

from core.llm_client import call_llm
from models.finding import Finding, FindingType, Severity

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a principal engineer reviewing code architecture and system design.
You think about how code will evolve over 2-3 years with a growing team.

Analyze the provided code for:
- SOLID principle violations:
  - SRP: class or function doing more than one job
  - OCP: code that requires modification instead of extension for new cases
  - LSP: subclasses that break parent contract
  - ISP: interfaces forcing unused method implementations
  - DIP: high-level modules depending on low-level details instead of abstractions
- Tight coupling between modules (direct instantiation instead of injection)
- Missing design patterns where they would help (Factory, Strategy, Observer, etc.)
- Business logic mixed into controllers, views, or route handlers
- Circular dependencies between modules
- Missing abstraction layers (talking directly to DB from route handlers)

Respond with ONLY a JSON object using this EXACT structure:

{"findings": [{"type": "architecture", "severity": "P1", "title": "SRP Violation in UserManager", "line_range": "43-70", "flagged_code": "class UserManager with CRUD, email, reports, payments", "explanation": "UserManager violates Single Responsibility Principle by handling 6 unrelated concerns. When the email logic changes, you risk breaking payment processing. Each concern should be a separate service class that can be tested and deployed independently.", "fixed_code": "class UserRepository (CRUD only), class EmailService, class PaymentService", "pattern_suggestion": "Repository Pattern + Service Layer"}]}

STRICT RULES:
- "type" must always be "architecture"
- "severity" must be exactly "P0", "P1", or "P2" — NEVER "High"/"Medium"/"Low"
- "line_range" must be digits like "5" or "5-7"
- Include "pattern_suggestion" when a design pattern would help
- Return ONLY the JSON object — no markdown, no extra text

Severity guide:
- P0: Circular dependencies that prevent deployment, critical coupling
- P1: SOLID violations, missing abstraction layers, business logic in controllers
- P2: Missing patterns that would help but code works without them

If no architecture issues found, return: {"findings": []}
"""


def _normalize_severity(raw: str) -> str:
    severity_map = {
        "P0": "P0", "P1": "P1", "P2": "P2",
        "critical": "P0", "CRITICAL": "P0",
        "high": "P1", "HIGH": "P1",
        "medium": "P2", "MEDIUM": "P2",
        "low": "P2", "LOW": "P2",
    }
    return severity_map.get(raw, severity_map.get(raw.lower(), "P1"))


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
                type=FindingType.ARCHITECTURE,
                severity=_normalize_severity(raw.get("severity", "P1")),
                title=raw.get("title", "Architecture Issue")[:200],
                line_range=_normalize_line_range(raw.get("line_range", "1")),
                flagged_code=raw.get("flagged_code", raw.get("code", "N/A")),
                explanation=raw.get("explanation", raw.get("description", "No explanation")),
                fixed_code=raw.get("fixed_code", raw.get("recommendation", "No fix")),
                pattern_suggestion=raw.get("pattern_suggestion"),
            )
            findings.append(finding)
        except Exception as e:
            logger.warning("Failed to parse architecture finding %d: %s", i, str(e)[:100])
    return findings


def analyze_architecture(
    code: str,
    language: str = "python",
    ast_context: Optional[str] = None,
) -> list[Finding]:
    """Analyze code for architecture issues. Never crashes."""
    user_prompt = f"Review this {language} code for architecture and design issues:\n\n"
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
            "Architecture agent found %d issues (P0=%d, P1=%d, P2=%d)",
            len(findings),
            sum(1 for f in findings if f.severity == Severity.P0),
            sum(1 for f in findings if f.severity == Severity.P1),
            sum(1 for f in findings if f.severity == Severity.P2),
        )
        return findings
    except Exception as e:
        logger.error("Architecture agent failed: %s", str(e)[:200])
        return []
