"""
Tests for Firebase Firestore client.

Uses mocks — no real Firebase connection needed.
Run: pytest tests/test_firebase.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from models.finding import Finding, FindingType, Severity
from models.review import Review


def _make_review() -> Review:
    return Review(
        repo="test/repo",
        findings=[
            Finding(
                type=FindingType.SECURITY, severity=Severity.P0,
                title="SQL Injection", line_range="12",
                explanation="Bad query.", flagged_code="bad",
                fixed_code="good",
            ),
            Finding(
                type=FindingType.SMELL, severity=Severity.P2,
                title="Magic number", line_range="30",
                explanation="Use constant.", flagged_code="0.15",
                fixed_code="RATE = 0.15",
            ),
        ],
        agents_completed=["security", "smell"],
        review_duration_seconds=15.0,
    )


class TestSaveReview:

    def test_saves_to_firestore(self):
        from core.firebase_client import save_review

        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "abc123"

        mock_db = MagicMock()
        mock_db.collection.return_value.add.return_value = (None, mock_doc_ref)

        with patch("core.firebase_client._get_db", return_value=mock_db):
            doc_id = save_review(
                _make_review(),
                pr_number=42,
                pr_title="Add auth",
                pr_author="vatsalya",
            )

        assert doc_id == "abc123"
        mock_db.collection.assert_called_with("reviews")

    def test_saves_correct_fields(self):
        from core.firebase_client import save_review

        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "xyz"

        mock_collection = MagicMock()
        mock_collection.add.return_value = (None, mock_doc_ref)

        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with patch("core.firebase_client._get_db", return_value=mock_db):
            save_review(
                _make_review(),
                pr_number=42,
                pr_title="Add auth",
                pr_author="vatsalya",
                pr_url="https://github.com/test/repo/pull/42",
            )

        saved_data = mock_collection.add.call_args[0][0]
        assert saved_data["repo"] == "test/repo"
        assert saved_data["pr_number"] == 42
        assert saved_data["pr_title"] == "Add auth"
        assert saved_data["p0_count"] == 1
        assert saved_data["p2_count"] == 1
        assert saved_data["findings_count"] == 2
        assert len(saved_data["findings"]) == 2
        assert saved_data["findings"][0]["type"] == "security"
        assert saved_data["findings"][0]["severity"] == "P0"

    def test_returns_none_if_db_not_configured(self):
        from core.firebase_client import save_review
        with patch("core.firebase_client._get_db", return_value=None):
            result = save_review(_make_review())
        assert result is None

    def test_handles_firestore_error(self):
        from core.firebase_client import save_review
        mock_db = MagicMock()
        mock_db.collection.return_value.add.side_effect = Exception("Firestore down")

        with patch("core.firebase_client._get_db", return_value=mock_db):
            result = save_review(_make_review())
        assert result is None


class TestGetReviews:

    def test_returns_reviews_for_repo(self):
        from core.firebase_client import get_reviews_for_repo

        mock_doc = MagicMock()
        mock_doc.id = "doc1"
        mock_doc.to_dict.return_value = {"repo": "test/repo", "p0_count": 1}

        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]

        mock_db = MagicMock()
        mock_db.collection.return_value = mock_query

        with patch("core.firebase_client._get_db", return_value=mock_db):
            results = get_reviews_for_repo("test/repo")

        assert len(results) == 1
        assert results[0]["id"] == "doc1"
        assert results[0]["repo"] == "test/repo"

    def test_returns_empty_if_db_not_configured(self):
        from core.firebase_client import get_reviews_for_repo
        with patch("core.firebase_client._get_db", return_value=None):
            results = get_reviews_for_repo("test/repo")
        assert results == []


class TestGetReviewById:

    def test_returns_review(self):
        from core.firebase_client import get_review_by_id

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "abc"
        mock_doc.to_dict.return_value = {"repo": "test/repo"}

        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with patch("core.firebase_client._get_db", return_value=mock_db):
            result = get_review_by_id("abc")

        assert result["id"] == "abc"
        assert result["repo"] == "test/repo"

    def test_returns_none_for_missing_doc(self):
        from core.firebase_client import get_review_by_id

        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        with patch("core.firebase_client._get_db", return_value=mock_db):
            result = get_review_by_id("nonexistent")
        assert result is None


class TestRepoStats:

    def test_calculates_stats(self):
        from core.firebase_client import get_repo_stats

        mock_reviews = [
            {"findings_count": 5, "p0_count": 1, "p1_count": 2, "p2_count": 2, "duration_seconds": 20},
            {"findings_count": 3, "p0_count": 0, "p1_count": 1, "p2_count": 2, "duration_seconds": 15},
        ]

        with patch("core.firebase_client.get_reviews_for_repo", return_value=mock_reviews):
            stats = get_repo_stats("test/repo")

        assert stats["total_reviews"] == 2
        assert stats["total_findings"] == 8
        assert stats["total_p0"] == 1
        assert stats["avg_duration"] == 17.5

    def test_empty_repo_stats(self):
        from core.firebase_client import get_repo_stats
        with patch("core.firebase_client.get_reviews_for_repo", return_value=[]):
            stats = get_repo_stats("test/repo")
        assert stats["total_reviews"] == 0
        assert stats["total_findings"] == 0
