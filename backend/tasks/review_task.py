"""
Review task — the Celery task that runs the full review pipeline.

Flow:
    1. Fetch changed files from the PR via GitHub API
    2. For each supported file: parse AST + run 4 agents in parallel
    3. Aggregate all findings across all files
    4. Deduplicate and sort by severity
    5. Format as a Markdown comment
    6. Post the comment on the PR

This runs in a Celery worker process, NOT in the FastAPI server.
The webhook enqueues this task and returns 202 immediately.
"""

import logging
import time

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="screvyn.review_pr",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def review_pr(self, owner: str, repo: str, pr_number: int, installation_id: str):
    """
    Run a full code review on a pull request.

    Args:
        owner: GitHub org/user (e.g. "Vatsalya2003")
        repo: Repository name (e.g. "screvyn_multi-agent-code-review-system")
        pr_number: PR number
        installation_id: GitHub App installation ID
    """
    start = time.time()
    task_id = self.request.id
    full_repo = f"{owner}/{repo}"

    logger.info(
        "Starting review task %s for %s#%d",
        task_id, full_repo, pr_number,
    )

    try:
        # Step 1: Get PR details (head SHA for fetching files)
        from core.github_client import (
            get_pr_details, get_pr_files, get_file_content,
            post_pr_comment, detect_language,
        )

        pr_info = get_pr_details(owner, repo, pr_number)
        head_sha = pr_info["head_sha"]
        logger.info("PR head SHA: %s", head_sha[:8])

        # Step 2: Fetch changed files
        changed_files = get_pr_files(owner, repo, pr_number)
        logger.info("Found %d changed files", len(changed_files))

        # Step 3: Filter to supported languages and fetch content
        files_to_review = []
        for f in changed_files:
            if f["status"] == "removed":
                continue
            lang = detect_language(f["filename"])
            if lang is None:
                continue
            try:
                content = get_file_content(owner, repo, f["filename"], head_sha)
                if content.strip():
                    files_to_review.append({
                        "filename": f["filename"],
                        "language": lang,
                        "content": content,
                    })
            except Exception as e:
                logger.warning("Could not fetch %s: %s", f["filename"], e)

        logger.info(
            "Reviewing %d files: %s",
            len(files_to_review),
            [f["filename"] for f in files_to_review],
        )

        if not files_to_review:
            logger.info("No reviewable files in PR — skipping")
            return {
                "status": "skipped",
                "reason": "no supported files",
                "duration": round(time.time() - start, 1),
            }

        # Step 4: Run the review pipeline on each file
        from agents.orchestrator import run_review
        from models.finding import Finding

        all_findings: list[Finding] = []
        all_agents_completed: list[str] = []
        all_agents_failed: list[str] = []

        for file_info in files_to_review:
            logger.info("Reviewing %s (%s)", file_info["filename"], file_info["language"])
            try:
                result = run_review(file_info["content"], file_info["language"])
                # Tag each finding with the filename so the PR comment
                # shows which file the issue is in
                for finding in result.get("all_findings", []):
                    finding.title = f"{file_info['filename']}: {finding.title}"
                all_findings.extend(result.get("all_findings", []))
                all_agents_completed.extend(result.get("agents_completed", []))
                all_agents_failed.extend(result.get("agents_failed", []))
            except Exception as e:
                logger.error("Review failed for %s: %s", file_info["filename"], e)
                all_agents_failed.append(f"error:{file_info['filename']}")

        # Step 5: Build the Review object and format the comment
        from models.review import Review
        from notifications.github_comment_formatter import format_review_comment

        review = Review(
            repo=full_repo,
            findings=all_findings,
            agents_completed=list(set(all_agents_completed)),
            agents_failed=list(set(all_agents_failed)),
            review_duration_seconds=round(time.time() - start, 1),
        )
        review.sort_findings()

        comment_body = format_review_comment(review)

        # Step 6: Post the comment on the PR
        post_pr_comment(owner, repo, pr_number, comment_body)

        duration = round(time.time() - start, 1)
        logger.info(
            "Review complete for %s#%d: %d findings in %ss",
            full_repo, pr_number, len(all_findings), duration,
        )

        return {
            "status": "completed",
            "repo": full_repo,
            "pr_number": pr_number,
            "findings_count": len(all_findings),
            "p0_count": review.p0_count,
            "p1_count": review.p1_count,
            "p2_count": review.p2_count,
            "agents_completed": review.agents_completed,
            "agents_failed": review.agents_failed,
            "duration": duration,
        }

    except Exception as exc:
        duration = round(time.time() - start, 1)
        logger.error(
            "Review task failed for %s#%d after %ss: %s",
            full_repo, pr_number, duration, exc,
        )
        raise self.retry(exc=exc)
