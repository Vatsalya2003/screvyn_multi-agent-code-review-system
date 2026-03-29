"""
Firebase Firestore client — stores review history for the dashboard.

Collections:
    reviews/{auto_id}
        - repo: "owner/repo"
        - pr_number: 42
        - findings_count: 11
        - p0_count: 3
        - p1_count: 3
        - p2_count: 5
        - findings: [...serialized Finding objects...]
        - agents_completed: ["security", "performance", ...]
        - agents_failed: []
        - duration_seconds: 24.5
        - created_at: timestamp
        - pr_title: "Add user auth"
        - pr_author: "vatsalya"

This data powers the Phase 8 Next.js dashboard:
    - Review history list
    - Severity trend charts
    - Per-repo stats
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore

from core.config import settings
from models.review import Review

logger = logging.getLogger(__name__)

# Singleton — initialized once, reused everywhere
_db = None


def _get_db():
    """Get or initialize the Firestore client (singleton)."""
    global _db
    if _db is not None:
        return _db

    if not settings.firebase_credentials_path or not settings.firebase_project_id:
        logger.warning("Firebase not configured — storage disabled")
        return None

    try:
        # Only initialize if not already done
        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(cred, {
                "projectId": settings.firebase_project_id,
            })

        _db = firestore.client()
        logger.info("Firebase Firestore connected")
        return _db
    except Exception as e:
        logger.error("Firebase initialization failed: %s", e)
        return None


def save_review(
    review: Review,
    pr_number: int = 0,
    pr_title: str = "",
    pr_author: str = "",
    pr_url: str = "",
) -> Optional[str]:
    """
    Save a completed review to Firestore.

    Returns the document ID if saved, None if storage is disabled or failed.
    Never raises — failures are logged and swallowed.
    """
    db = _get_db()
    if db is None:
        return None

    try:
        # Serialize findings to dicts
        findings_data = []
        for f in review.findings:
            findings_data.append({
                "type": f.type.value,
                "severity": f.severity.value,
                "title": f.title,
                "line_range": f.line_range,
                "explanation": f.explanation,
                "flagged_code": f.flagged_code or "",
                "fixed_code": f.fixed_code or "",
                "owasp_ref": f.owasp_ref or "",
                "complexity_before": f.complexity_before or "",
                "complexity_after": f.complexity_after or "",
                "pattern_suggestion": f.pattern_suggestion or "",
            })

        doc_data = {
            "repo": review.repo,
            "pr_number": pr_number,
            "pr_title": pr_title,
            "pr_author": pr_author,
            "pr_url": pr_url,
            "findings_count": review.total_findings,
            "p0_count": review.p0_count,
            "p1_count": review.p1_count,
            "p2_count": review.p2_count,
            "findings": findings_data,
            "agents_completed": review.agents_completed,
            "agents_failed": review.agents_failed,
            "duration_seconds": review.review_duration_seconds,
            "created_at": datetime.now(timezone.utc),
        }

        doc_ref = db.collection("reviews").add(doc_data)
        doc_id = doc_ref[1].id
        logger.info("Saved review to Firestore: %s (doc: %s)", review.repo, doc_id)
        return doc_id

    except Exception as e:
        logger.error("Firestore save failed: %s", e)
        return None


def get_reviews_for_repo(repo: str, limit: int = 20) -> list[dict]:
    """
    Fetch recent reviews for a repo (used by the dashboard).

    Returns a list of review dicts, newest first.
    """
    db = _get_db()
    if db is None:
        return []

    try:
        docs = (
            db.collection("reviews")
            .where("repo", "==", repo)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]

    except Exception as e:
        logger.error("Firestore query failed: %s", e)
        return []


def get_review_by_id(doc_id: str) -> Optional[dict]:
    """Fetch a single review by its Firestore document ID."""
    db = _get_db()
    if db is None:
        return None

    try:
        doc = db.collection("reviews").document(doc_id).get()
        if doc.exists:
            return {"id": doc.id, **doc.to_dict()}
        return None
    except Exception as e:
        logger.error("Firestore get failed: %s", e)
        return None


def get_repo_stats(repo: str) -> dict:
    """
    Get aggregate stats for a repo (used by the dashboard).

    Returns: total reviews, total findings, avg duration, severity breakdown.
    """
    reviews = get_reviews_for_repo(repo, limit=100)

    if not reviews:
        return {
            "repo": repo,
            "total_reviews": 0,
            "total_findings": 0,
            "total_p0": 0,
            "total_p1": 0,
            "total_p2": 0,
            "avg_duration": 0,
        }

    return {
        "repo": repo,
        "total_reviews": len(reviews),
        "total_findings": sum(r.get("findings_count", 0) for r in reviews),
        "total_p0": sum(r.get("p0_count", 0) for r in reviews),
        "total_p1": sum(r.get("p1_count", 0) for r in reviews),
        "total_p2": sum(r.get("p2_count", 0) for r in reviews),
        "avg_duration": round(
            sum(r.get("duration_seconds", 0) for r in reviews) / len(reviews), 1
        ),
    }
