"""
Performance Agent — finds slow code and wasteful patterns.

Catches: N+1 queries, O(n^2) loops, memory leaks, blocking calls,
missing caching, unnecessary repeated computation.

Same pattern as security_agent.py — if you understand one, you
understand all four. The only difference is the system prompt.
"""

import logging
from typing import Optional

from core.llm_client import call_llm
from models.finding import Finding, FindingType, Severity

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a staff performance engineer at a top tech company. You specialize
in finding code that will be slow, waste memory, or break at scale.

Analyze the provided code for:
- N+1 database queries (a DB call inside a loop — each iteration hits the DB)
- Algorithmic complexity issues (O(n^2) or worse on potentially large inputs)
- Memory leaks (unclosed files/connections, growing lists, circular references)
- Blocking synchronous calls where async would prevent thread starvation
- Unnecessary repeated computation (values that could be cached or memoized)
- Inefficient data structures (using a list where a set/dict lookup would be O(1))
- Resource exhaustion (opening connections without closing, unbounded queues)

Respond with ONLY a JSON object using this EXACT structure:

{"findings": [{"type": "performance", "severity": "P1", "title": "N+1 Query in get_orders", "line_range": "19-24", "flagged_code": "for uid in ids: db.query(uid)", "explanation": "This executes N separate database queries inside a loop. With 1000 users, that is 1001 round trips to the database instead of 1 batch query. At scale this causes timeouts and database connection exhaustion.", "fixed_code": "db.query('SELECT * FROM orders WHERE user_id IN (?)', ids)", "complexity_before": "O(n)", "complexity_after": "O(1)"}]}

STRICT RULES:
- "type" must always be "performance"
- "severity" must be exactly "P0", "P1", or "P2" — NEVER "High"/"Medium"/"Low"
- "line_range" must be digits like "5" or "5-7"
- Include "complexity_before" and "complexity_after" when applicable
- "explanation" must include a concrete example with numbers (e.g. "1000 users = 1001 queries")
- Return ONLY the JSON object — no markdown, no extra text

Severity guide:
- P0: Unbounded memory growth, resource leaks that crash the process
- P1: N+1 queries, O(n^2) on large inputs, blocking calls in async context
- P2: Missing caching, suboptimal data structure choice, minor inefficiency

If no performance issues found, return: {"findings": []}
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
    import re
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
                type=FindingType.PERFORMANCE,
                severity=_normalize_severity(raw.get("severity", "P1")),
                title=raw.get("title", "Performance Issue")[:200],
                line_range=_normalize_line_range(raw.get("line_range", "1")),
                flagged_code=raw.get("flagged_code", raw.get("code", "N/A")),
                explanation=raw.get("explanation", raw.get("description", "No explanation")),
                fixed_code=raw.get("fixed_code", raw.get("recommendation", "No fix")),
                complexity_before=raw.get("complexity_before"),
                complexity_after=raw.get("complexity_after"),
            )
            findings.append(finding)
        except Exception as e:
            logger.warning("Failed to parse performance finding %d: %s", i, str(e)[:100])
    return findings


def analyze_performance(
    code: str,
    language: str = "python",
    ast_context: Optional[str] = None,
) -> list[Finding]:
    """Analyze code for performance issues. Never crashes — returns empty list on failure."""
    user_prompt = f"Review this {language} code for performance issues:\n\n"
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
            "Performance agent found %d issues (P0=%d, P1=%d, P2=%d)",
            len(findings),
            sum(1 for f in findings if f.severity == Severity.P0),
            sum(1 for f in findings if f.severity == Severity.P1),
            sum(1 for f in findings if f.severity == Severity.P2),
        )
        return findings
    except Exception as e:
        logger.error("Performance agent failed: %s", str(e)[:200])
        return []
