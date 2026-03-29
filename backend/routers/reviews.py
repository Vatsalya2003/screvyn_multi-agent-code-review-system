"""
Reviews router — updated for Phase 4 multi-agent orchestration.

Changes from Phase 2:
  - Now calls run_review() orchestrator instead of analyze_security() directly
  - All 4 agents run in parallel via LangGraph
  - Response includes findings from all agent categories
"""

import logging
import time

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agents.orchestrator import run_review
from models.review import Review

logger = logging.getLogger(__name__)


class ReviewRequest(BaseModel):
    code: str = Field(
        description="Source code to review",
        min_length=1,
        max_length=50000,
        examples=["def get_user(id):\n    return db.execute(f'SELECT * FROM users WHERE id={id}')"],
    )
    language: str = Field(
        default="python",
        description="Programming language of the code",
        examples=["python", "javascript", "java"],
    )


class ReviewResponse(BaseModel):
    repo: str
    language: str
    findings: list
    p0_count: int
    p1_count: int
    p2_count: int
    total_findings: int
    has_critical: bool
    review_duration_seconds: float
    agents_completed: list[str]
    agents_failed: list[str]


router = APIRouter()


@router.post(
    "/review",
    response_model=ReviewResponse,
    summary="Review code with 4 parallel AI agents",
    description=(
        "Submit source code and receive a comprehensive review from "
        "4 specialist agents (Security, Performance, Code Smell, Architecture) "
        "running in parallel. Findings are ranked P0 (critical) to P2 (medium)."
    ),
)
async def create_review(request: ReviewRequest):
    logger.info(
        "Review requested: language=%s, code_length=%d chars",
        request.language,
        len(request.code),
    )

    start_time = time.time()

    # Run all 4 agents through LangGraph orchestrator
    result = run_review(
        code=request.code,
        language=request.language,
    )

    elapsed = time.time() - start_time

    # Build the Review object
    review = Review(
        repo="paste/anonymous",
        language=request.language,
        findings=result["all_findings"],
        review_duration_seconds=round(elapsed, 2),
        agents_completed=result["agents_completed"],
        agents_failed=result["agents_failed"],
    )
    review.sort_findings()

    logger.info(
        "Review complete in %.1fs: %d findings (P0=%d, P1=%d, P2=%d) "
        "from agents: %s (failed: %s)",
        elapsed,
        review.total_findings,
        review.p0_count,
        review.p1_count,
        review.p2_count,
        review.agents_completed,
        review.agents_failed,
    )

    return review
