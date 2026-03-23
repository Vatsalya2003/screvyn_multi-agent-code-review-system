"""Finding model — the atomic unit of a code review."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class FindingType(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    SMELL = "smell"
    ARCHITECTURE = "architecture"


class Severity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class Finding(BaseModel):
    type: FindingType
    severity: Severity
    title: str = Field(min_length=3, max_length=200)
    line_range: str = Field(pattern=r"^\d+(-\d+)?$")
    flagged_code: str
    explanation: str
    fixed_code: str
    owasp_ref: Optional[str] = None
    complexity_before: Optional[str] = None
    complexity_after: Optional[str] = None
    pattern_suggestion: Optional[str] = None
