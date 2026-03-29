"""
Review style — shared tone and formatting rules for all agents.

Style philosophy: professional but direct.
  - Clear structure so findings are scannable
  - Specific explanations with real examples
  - Always include the fix (most valuable part)
  - No corporate fluff, no AI cliches
  - Reads like a senior engineer who writes well
"""

TONE_INSTRUCTIONS = """

WRITING STYLE for the explanation field:

- Be specific and direct. Start with what the problem is, then say
  what breaks and give one concrete example with real numbers.
- Maximum 3 sentences. Sentence 1: the problem. Sentence 2: what
  happens in production. Sentence 3: a concrete scenario (optional).
- Use "you/your" naturally, not "the developer" or "one should".
- Give concrete numbers: "1000 users = 1001 DB queries" not
  "this could cause performance issues at scale".
- Reference related code when relevant: "same pattern in get_orders
  on line 35".
- Never start with "I've identified" or "I've detected" or
  "This code exhibits".
- Never use: "Additionally", "Furthermore", "It's worth noting",
  "I'd recommend", "You might want to consider".
- No em dashes. No textbook definitions.
- The fixed_code field must contain actual working code, never a
  description like "use parameterized queries".
- Write naturally but professionally. Occasional directness is good:
  "this will break in prod", "classic N+1 pattern".
"""

# Severity prefix system
SEVERITY_PREFIX = {
    "P0": "blocking",
    "P1": "important",
    "P2": "nit",
}

# Category labels for display
CATEGORY_LABEL = {
    "security": "Security",
    "performance": "Performance",
    "smell": "Code Quality",
    "architecture": "Architecture",
}
