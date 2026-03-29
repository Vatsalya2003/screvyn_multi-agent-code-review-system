"""
GitHub PR comment formatter — renders findings as Markdown.

Improvements over v1:
  - Caps displayed findings (all P0s shown, then top P1/P2 up to MAX_SHOWN)
  - Truncates fix code to MAX_FIX_LINES (no full class implementations)
  - Tighter explanations (hard cap at 200 chars)
  - Summary count at top for quick scanning
  - Footer shows hidden count if any were trimmed
"""

import logging
from models.finding import Finding, Severity
from models.review import Review
from core.review_style import SEVERITY_PREFIX, CATEGORY_LABEL

logger = logging.getLogger(__name__)

# ── Display limits ────────────────────────────────────────────
MAX_SHOWN = 7          # max findings shown in full (all P0s always shown)
MAX_FIX_LINES = 8      # truncate fix code after this many lines
MAX_EXPLANATION = 200   # hard cap on explanation length (chars)


def _truncate_code(code: str, max_lines: int = MAX_FIX_LINES) -> str:
    """Truncate code blocks that are too long."""
    if not code or code in ("N/A", "No fix provided"):
        return ""
    lines = code.strip().split("\n")
    if len(lines) <= max_lines:
        return code.strip()
    truncated = "\n".join(lines[:max_lines])
    remaining = len(lines) - max_lines
    return f"{truncated}\n// ... {remaining} more lines"


def _truncate_explanation(text: str, max_len: int = MAX_EXPLANATION) -> str:
    """Truncate explanation to max length, cutting at sentence boundary."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rfind(".")
    if cut > 80:
        return text[:cut + 1]
    return text[:max_len].rstrip() + "..."


def _format_single_finding(finding: Finding, index: int) -> str:
    """
    Format one finding — compact, scannable, always has the fix.

    Output:
        ### blocking | Security: SQL Injection in get_user (line 12-14)

        User input goes directly into the SQL query. An attacker passes
        uid="1; DROP TABLE users" and your users table is gone.

        **Flagged code:**
        ```
        db.execute(f'SELECT * FROM users WHERE id = {user_id}')
        ```

        **Recommended fix:**
        ```
        db.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        ```
    """
    prefix = SEVERITY_PREFIX.get(finding.severity.value, "note")
    category = CATEGORY_LABEL.get(finding.type.value, finding.type.value)
    location = f"(line {finding.line_range})" if finding.line_range else ""

    lines = []

    # Header
    lines.append(f"### {prefix} | {category}: {finding.title} {location}")
    lines.append("")

    # Explanation — capped
    if finding.explanation:
        lines.append(_truncate_explanation(finding.explanation))
        lines.append("")

    # Flagged code
    if finding.flagged_code and finding.flagged_code != "N/A":
        lines.append("**Flagged code:**")
        lines.append(f"```\n{finding.flagged_code.strip()}\n```")
        lines.append("")

    # Recommended fix — truncated if too long
    fix = _truncate_code(finding.fixed_code)
    if fix:
        lines.append("**Recommended fix:**")
        lines.append(f"```\n{fix}\n```")
        lines.append("")

    # Extra context (one line)
    extras = []
    if finding.complexity_before and finding.complexity_after:
        extras.append(f"Complexity: {finding.complexity_before} → {finding.complexity_after}")
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

    Rules:
      - All P0 findings are ALWAYS shown (they block merge)
      - P1 + P2 shown up to MAX_SHOWN total
      - Remaining findings summarized in footer
    """
    if review.total_findings == 0:
        agents = ", ".join(review.agents_completed)
        return (
            "Reviewed this PR — no issues found across security, performance, "
            f"code quality, and architecture checks.\n\n"
            f"<sub>Reviewed by {agents} agents in "
            f"{review.review_duration_seconds:.0f}s | Screvyn</sub>"
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

    lines.append(f"Found {', '.join(parts)}.")
    lines.append("")

    if review.has_critical:
        lines.append("> **Blocking issues must be fixed before merge.**")
        lines.append("")

    # ── Select which findings to show ────────────────────
    p0 = [f for f in review.findings if f.severity == Severity.P0]
    p1 = [f for f in review.findings if f.severity == Severity.P1]
    p2 = [f for f in review.findings if f.severity == Severity.P2]

    # Always show all P0s. Fill remaining slots with P1 then P2.
    shown = list(p0)
    remaining_slots = max(0, MAX_SHOWN - len(shown))
    shown.extend(p1[:remaining_slots])
    remaining_slots = max(0, MAX_SHOWN - len(shown))
    shown.extend(p2[:remaining_slots])

    hidden_count = review.total_findings - len(shown)

    # ── Render findings ──────────────────────────────────
    lines.append("---")
    lines.append("")

    for i, finding in enumerate(shown):
        lines.append(_format_single_finding(finding, i))
        if i < len(shown) - 1:
            lines.append("---")
            lines.append("")

    # ── Footer ───────────────────────────────────────────
    lines.append("---")
    lines.append("")

    if hidden_count > 0:
        lines.append(f"*+{hidden_count} more findings not shown. "
                      f"Run Screvyn locally for the full report.*")
        lines.append("")

    agents = ", ".join(review.agents_completed)
    duration = f"{review.review_duration_seconds:.0f}s"
    lines.append(
        f"<sub>Reviewed by {agents} agents in {duration} | Screvyn Code Review</sub>"
    )

    return "\n".join(lines)


def format_review_comment_short(review: Review) -> str:
    """
    Compact version for Slack, Teams, and Email alerts.
    Shows: summary + top 3 findings with location and fix.
    """
    if review.total_findings == 0:
        return f"**{review.repo}** — clean. No issues found."

    lines = []

    # Summary
    parts = []
    if review.p0_count > 0:
        parts.append(f"**{review.p0_count} blocking**")
    if review.p1_count > 0:
        parts.append(f"{review.p1_count} important")
    if review.p2_count > 0:
        parts.append(f"{review.p2_count} nit{'s' if review.p2_count > 1 else ''}")

    lines.append(f"**{review.repo}** — {', '.join(parts)}.")
    if review.has_critical:
        lines.append("Blocking issues need to be fixed before merge.")
    lines.append("")

    # Top 3 findings
    top = review.findings[:3]
    for f in top:
        prefix = SEVERITY_PREFIX.get(f.severity.value, "note")
        category = CATEGORY_LABEL.get(f.type.value, f.type.value)
        loc = f"line {f.line_range}" if f.line_range else ""

        lines.append(f"**{prefix}** | {category}: {f.title} ({loc})")
        explanation = _truncate_explanation(f.explanation, 120)
        lines.append(f"  {explanation}")

        fix = _truncate_code(f.fixed_code, 3)
        if fix:
            first_line = fix.split("\n")[0]
            lines.append(f"  fix: `{first_line}`")
        lines.append("")

    remaining = review.total_findings - 3
    if remaining > 0:
        lines.append(f"...and {remaining} more")

    return "\n".join(lines)
