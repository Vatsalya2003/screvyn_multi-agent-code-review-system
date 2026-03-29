"""
Severity Aggregator — deduplicates, merges, and ranks findings.

When 4 agents analyze the same code independently, they often flag
the same issue from different angles. For example:

  Security agent:     "SQL Injection in get_user" (lines 12-14)
  Architecture agent: "Missing input validation in get_user" (lines 12-14)
  Performance agent:  "Unclosed DB connection in get_user" (lines 10-15)

The first two are essentially the same issue (unsafe user input in a query).
The third overlaps in location but is a genuinely different problem.

This module decides:
  - Which findings are duplicates (merge them)
  - Which are distinct (keep both)
  - What severity the merged finding gets (highest wins)

Algorithm:
  For every pair of findings, check two conditions:
    1. Line range overlap > 50%
    2. Title similarity > 60%
  If BOTH conditions are true → merge (keep higher severity)
  If only one or neither → keep both as separate findings

Why this approach?
  - Line overlap alone catches location-based duplicates
  - Title similarity alone catches semantic duplicates
  - Requiring BOTH reduces false merges (high precision)
  - 50% and 60% thresholds are tuned from testing — not magic numbers

Performance: O(n^2) for n findings. With typical reviews (5-20 findings),
this takes <1ms. Even with 100 findings, it's under 10ms.
"""

import logging
from difflib import SequenceMatcher

from models.finding import Finding, Severity

logger = logging.getLogger(__name__)


# ─── Line Range Utilities ────────────────────────────────────


def _parse_line_range(line_range: str) -> tuple[int, int]:
    """
    Convert a line_range string to (start, end) tuple.

    Examples:
        "5"   → (5, 5)
        "5-7" → (5, 7)
        "12"  → (12, 12)
    """
    parts = line_range.split("-")
    start = int(parts[0])
    end = int(parts[-1])  # Same as start if no dash
    return (start, end)


def _line_overlap_ratio(range_a: str, range_b: str) -> float:
    """
    Calculate how much two line ranges overlap, from 0.0 to 1.0.

    The ratio is: overlap_size / size_of_smaller_range

    We divide by the SMALLER range because if a 2-line finding
    overlaps with a 20-line finding, the 2-line one is probably
    a more specific version of the same issue.

    Examples:
        "5-10" vs "7-12"  → overlap is 7-10 (4 lines)
                             smaller range is 6 lines → 4/6 = 0.67
        "5-7"  vs "5-7"   → perfect overlap → 1.0
        "1-3"  vs "10-15" → no overlap → 0.0
        "5"    vs "5"     → same line → 1.0
    """
    start_a, end_a = _parse_line_range(range_a)
    start_b, end_b = _parse_line_range(range_b)

    # Calculate overlap
    overlap_start = max(start_a, start_b)
    overlap_end = min(end_a, end_b)

    if overlap_start > overlap_end:
        return 0.0  # No overlap

    overlap_size = overlap_end - overlap_start + 1
    size_a = end_a - start_a + 1
    size_b = end_b - start_b + 1
    smaller_size = min(size_a, size_b)

    if smaller_size == 0:
        return 0.0

    return overlap_size / smaller_size


def _title_similarity(title_a: str, title_b: str) -> float:
    """
    Calculate how similar two finding titles are, from 0.0 to 1.0.

    Uses Python's SequenceMatcher which computes the ratio of
    matching characters. It's not perfect NLP, but it works well
    for our use case because findings about the same issue tend
    to share key words like the function name.

    Examples:
        "SQL Injection in get_user" vs "SQL Injection in get_user" → 1.0
        "SQL Injection in get_user" vs "Missing Validation in get_user" → ~0.6
        "SQL Injection in get_user" vs "God Class UserManager" → ~0.2
    """
    # Normalize: lowercase and strip whitespace
    a = title_a.lower().strip()
    b = title_b.lower().strip()

    return SequenceMatcher(None, a, b).ratio()


# ─── Severity Comparison ─────────────────────────────────────


# Lower number = higher severity (P0 is most critical)
_SEVERITY_RANK = {
    Severity.P0: 0,
    Severity.P1: 1,
    Severity.P2: 2,
}


def _higher_severity(sev_a: Severity, sev_b: Severity) -> Severity:
    """Return the more critical of two severities."""
    if _SEVERITY_RANK[sev_a] <= _SEVERITY_RANK[sev_b]:
        return sev_a
    return sev_b


# ─── Merge Logic ─────────────────────────────────────────────


def _merge_two_findings(primary: Finding, duplicate: Finding) -> Finding:
    """
    Merge two duplicate findings into one.

    Strategy:
      - Keep the higher severity
      - Keep the primary's title (usually more specific)
      - Combine explanations (the duplicate may add useful context)
      - Use the wider line range (covers both)
      - Keep primary's fixed_code (usually more actionable)
    """
    # Determine the wider line range
    start_p, end_p = _parse_line_range(primary.line_range)
    start_d, end_d = _parse_line_range(duplicate.line_range)
    merged_start = min(start_p, start_d)
    merged_end = max(end_p, end_d)

    if merged_start == merged_end:
        merged_range = str(merged_start)
    else:
        merged_range = f"{merged_start}-{merged_end}"

    # Combine explanations if they're different enough
    combined_explanation = primary.explanation
    if _title_similarity(primary.explanation, duplicate.explanation) < 0.8:
        combined_explanation = (
            f"{primary.explanation} "
            f"Additionally: {duplicate.explanation}"
        )

    return Finding(
        type=primary.type,
        severity=_higher_severity(primary.severity, duplicate.severity),
        title=primary.title,
        line_range=merged_range,
        flagged_code=primary.flagged_code,
        explanation=combined_explanation,
        fixed_code=primary.fixed_code,
        owasp_ref=primary.owasp_ref or duplicate.owasp_ref,
        complexity_before=primary.complexity_before or duplicate.complexity_before,
        complexity_after=primary.complexity_after or duplicate.complexity_after,
        pattern_suggestion=primary.pattern_suggestion or duplicate.pattern_suggestion,
    )


# ─── Main Dedup Function ────────────────────────────────────


# Thresholds — tuned from testing
LINE_OVERLAP_THRESHOLD = 0.5   # 50% line overlap required
TITLE_SIMILARITY_THRESHOLD = 0.6  # 60% title similarity required


def deduplicate_findings(
    findings: list[Finding],
    line_overlap_threshold: float = LINE_OVERLAP_THRESHOLD,
    title_similarity_threshold: float = TITLE_SIMILARITY_THRESHOLD,
) -> list[Finding]:
    """
    Remove duplicate findings by merging those that overlap.

    Algorithm:
      1. Mark all findings as "not merged"
      2. For each pair (i, j) where j > i:
         - If line overlap > threshold AND title similarity > threshold:
           merge j into i, mark j as merged
      3. Return only non-merged findings, sorted by severity

    This is O(n^2) but n is small (typically 5-20 findings).

    Args:
        findings: List of findings from all agents
        line_overlap_threshold: Min line overlap ratio (0.0-1.0) to consider duplicate
        title_similarity_threshold: Min title similarity (0.0-1.0) to consider duplicate

    Returns:
        Deduplicated list of findings, sorted by severity (P0 first)
    """
    if len(findings) <= 1:
        return findings

    # Track which findings have been merged into another
    merged_into = {}  # index → index it was merged into
    result = list(findings)  # Working copy

    for i in range(len(result)):
        if i in merged_into:
            continue  # Already merged into something else

        for j in range(i + 1, len(result)):
            if j in merged_into:
                continue  # Already merged into something else

            # Check both conditions
            line_overlap = _line_overlap_ratio(
                result[i].line_range, result[j].line_range
            )
            title_sim = _title_similarity(
                result[i].title, result[j].title
            )

            if (line_overlap >= line_overlap_threshold
                    and title_sim >= title_similarity_threshold):
                # Merge j into i
                logger.info(
                    "Dedup: merging '%s' into '%s' "
                    "(line_overlap=%.2f, title_sim=%.2f)",
                    result[j].title,
                    result[i].title,
                    line_overlap,
                    title_sim,
                )
                result[i] = _merge_two_findings(result[i], result[j])
                merged_into[j] = i

    # Filter out merged findings
    deduped = [
        result[i] for i in range(len(result))
        if i not in merged_into
    ]

    # Sort by severity: P0 first, then P1, then P2
    deduped.sort(key=lambda f: _SEVERITY_RANK.get(f.severity, 99))

    if len(findings) != len(deduped):
        logger.info(
            "Dedup: %d findings → %d after merge (%d duplicates removed)",
            len(findings),
            len(deduped),
            len(findings) - len(deduped),
        )

    return deduped
