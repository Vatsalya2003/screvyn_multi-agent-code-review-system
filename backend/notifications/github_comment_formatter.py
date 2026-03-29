"""
GitHub PR comment formatter — renders findings as Markdown.

Balanced style: structured enough to scan quickly, natural enough
to read like a real engineer's review. Every finding shows:
  - Category + severity + title + location (scannable header)
  - Clear explanation (2-3 sentences)
  - The problematic code
  - The recommended fix (always included)
"""

import logging
from models.finding import Finding, Severity
from models.review import Review
from core.review_style import SEVERITY_PREFIX, CATEGORY_LABEL

logger = logging.getLogger(__name__)


def _severity_emoji(severity: str) -> str:
    """Map severity to a simple indicator for PR comments."""
    return {"P0": "P0 Critical", "P1": "P1 High", "P2": "P2 Medium"}.get(severity, severity)


def _format_single_finding(finding: Finding, index: int) -> str:
    """
    Format one finding for a GitHub PR comment.

    Output example:
        ### blocking | Security: SQL Injection in `get_user` (line 12-14)

        This f-string puts user input directly into the SQL query.
        An attacker passes `uid = "1; DROP TABLE users"` and your
        users table is gone.

        **Flagged code:**
        ```python
        db.execute(f'SELECT * FROM users WHERE id = {user_id}')
        ```

        **Recommended fix:**
        ```python
        db.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        ```
    """
    prefix = SEVERITY_PREFIX.get(finding.severity.value, "note")
    category = CATEGORY_LABEL.get(finding.type.value, finding.type.value)
    location = f"(line {finding.line_range})"

    lines = []

    # Header — scannable: severity | category: issue (location)
    lines.append(f"### {prefix} | {category}: {finding.title} {location}")
    lines.append("")

    # Explanation — clear and specific
    explanation = finding.explanation.strip()
    if len(explanation) > 400:
        cut = explanation[:400].rfind(".")
        if cut > 100:
            explanation = explanation[: cut + 1]
    lines.append(explanation)
    lines.append("")

    # Flagged code
    if finding.flagged_code and finding.flagged_code != "N/A":
        lines.append("**Flagged code:**")
        lines.append("```")
        lines.append(finding.flagged_code.strip())
        lines.append("```")
        lines.append("")

    # Recommended fix — ALWAYS include this
    if finding.fixed_code and finding.fixed_code not in ("N/A", "No fix provided"):
        lines.append("**Recommended fix:**")
        lines.append("```")
        lines.append(finding.fixed_code.strip())
        lines.append("```")
        lines.append("")

    # Extra context where available
    extras = []
    if finding.complexity_before and finding.complexity_after:
        extras.append(
            f"Complexity: {finding.complexity_before} → {finding.complexity_after}"
        )
    if finding.pattern_suggestion:
        extras.append(f"Consider: {finding.pattern_suggestion}")
    if finding.owasp_ref:
        extras.append(f"Ref: {finding.owasp_ref}")

    if extras:
        lines.append(" | ".join(extras))
        lines.append("")

    return "\n".join(lines)


def format_review_comment(review: Review) -> str:
    """
    Format a complete review as a GitHub PR Markdown comment.

    Structure:
      1. Summary line with counts
      2. Blocking warning (if P0 exists)
      3. Each finding with full detail
      4. Subtle agent attribution at the bottom
    """
    if review.total_findings == 0:
        return (
            "Reviewed this PR — no security issues, performance concerns, "
            "or code quality problems found. Good to merge. :white_check_mark:"
        )

    lines = []

    # ── Summary ──────────────────────────────────────────
    parts = []
    if review.p0_count > 0:
        parts.append(f"**{review.p0_count} blocking**")
    if review.p1_count > 0:
        parts.append(f"{review.p1_count} important")
    if review.p2_count > 0:
        parts.append(f"{review.p2_count} nit{'s' if review.p2_count > 1 else ''}")

    summary = ", ".join(parts)
    lines.append(f"Reviewed this PR. Found {summary}.")
    lines.append("")

    if review.has_critical:
        lines.append(
            "> :rotating_light: **There are blocking issues that need "
            "to be fixed before merge.**"
        )
        lines.append("")

    lines.append("---")
    lines.append("")

    # ── Findings grouped by severity ─────────────────────
    p0 = [f for f in review.findings if f.severity == Severity.P0]
    p1 = [f for f in review.findings if f.severity == Severity.P1]
    p2 = [f for f in review.findings if f.severity == Severity.P2]

    all_ordered = p0 + p1 + p2

    for i, finding in enumerate(all_ordered):
        lines.append(_format_single_finding(finding, i))
        if i < len(all_ordered) - 1:
            lines.append("---")
            lines.append("")

    # ── Footer ───────────────────────────────────────────
    lines.append("---")
    lines.append("")

    agent_names = ", ".join(review.agents_completed)
    duration = f"{review.review_duration_seconds:.0f}s"
    lines.append(
        f"<sub>Reviewed by {agent_names} agents in {duration} | "
        f"Screvyn Code Review</sub>"
    )

    return "\n".join(lines)


def format_review_comment_short(review: Review) -> str:
    """
    Compact version for Slack, Teams, and Email alerts.
    Shows: summary + each finding with location, explanation, and fix.
    """
    if review.total_findings == 0:
        return "Clean review — no issues found. Good to merge."

    lines = []

    # Summary
    lines.append(
        f"Found {review.total_findings} issues: "
        f"{review.p0_count} blocking, {review.p1_count} important, "
        f"{review.p2_count} nits"
    )
    if review.has_critical:
        lines.append("Blocking issues need to be fixed before merge.")
    lines.append("")

    # Each finding: category + title + location + explanation + fix
    for f in review.findings:
        prefix = SEVERITY_PREFIX.get(f.severity.value, "note")
        category = CATEGORY_LABEL.get(f.type.value, f.type.value)

        lines.append(f"[{prefix} | {category}] {f.title} (line {f.line_range})")

        # Short explanation — first two sentences
        explanation = f.explanation.strip()
        sentences = explanation.split(". ")
        short_explanation = ". ".join(sentences[:2])
        if not short_explanation.endswith("."):
            short_explanation += "."
        if len(short_explanation) > 200:
            short_explanation = short_explanation[:200].rstrip() + "..."
        lines.append(f"  {short_explanation}")

        # Fix — always include
        if f.fixed_code and f.fixed_code not in ("N/A", "No fix provided"):
            fix_lines = f.fixed_code.strip().split("\n")
            if len(fix_lines) == 1 and len(fix_lines[0]) <= 100:
                lines.append(f"  Fix: {fix_lines[0]}")
            else:
                lines.append(f"  Fix: {fix_lines[0][:100]}...")

        lines.append("")

    return "\n".join(lines)