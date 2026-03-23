"""Review model — complete output of a code review."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, computed_field
from models.finding import Finding, Severity


class Review(BaseModel):
    repo: str
    pr_number: Optional[int] = None
    language: str = "python"
    findings: list[Finding] = Field(default_factory=list)
    review_duration_seconds: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agents_completed: list[str] = Field(default_factory=list)
    agents_failed: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def p0_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.P0)

    @computed_field
    @property
    def p1_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.P1)

    @computed_field
    @property
    def p2_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.P2)

    @computed_field
    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @computed_field
    @property
    def has_critical(self) -> bool:
        return self.p0_count > 0

    def sort_findings(self) -> None:
        severity_order = {Severity.P0: 0, Severity.P1: 1, Severity.P2: 2}
        self.findings.sort(key=lambda f: severity_order[f.severity])
