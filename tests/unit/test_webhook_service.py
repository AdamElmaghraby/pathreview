"""Tests for webhook_service.py"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest

from core.services.webhook_service import (
    _build_payload,
    _is_retryable,
    send_review_ready_notification,
)


def _make_review(status="complete", overall_score=9.0, updated_at=None):
    """Build a Mock review with the attributes the webhook service reads."""
    review = Mock()
    review.id = uuid4()
    review.status = status
    review.overall_score = overall_score
    review.updated_at = updated_at or datetime(2026, 1, 1, tzinfo=UTC)
    return review


def _http_status_error(status_code):
    """Build an httpx.HTTPStatusError carrying the given response status code."""
    response = Mock()
    response.status_code = status_code
    return httpx.HTTPStatusError("error", request=Mock(), response=response)


@pytest.mark.unit
class TestBuildPayload:
    """The JSON body sent to a subscriber."""

    def test_includes_expected_fields(self):
        review = _make_review(status="complete", overall_score=8.5)
        payload = _build_payload(review)

        assert payload["event"] == "review.ready"
        assert payload["review_id"] == str(review.id)
        assert payload["status"] == "complete"
        assert payload["overall_score"] == 8.5
        assert payload["updated_at"] == review.updated_at.isoformat()

    def test_handles_none_score_and_timestamp(self):
        review = _make_review(status="failed", overall_score=None, updated_at=None)
        review.updated_at = None
        payload = _build_payload(review)

        assert payload["overall_score"] is None
        assert payload["updated_at"] is None


@pytest.mark.unit
class TestIsRetryable:
    """Only transient failures (network errors, 5xx) should be retried."""

    def test_network_error_is_retryable(self):
        assert _is_retryable(httpx.ConnectError("connection refused")) is True

    def test_5xx_is_retryable(self):
        assert _is_retryable(_http_status_error(503)) is True

    def test_4xx_is_not_retryable(self):
        assert _is_retryable(_http_status_error(404)) is False

    def test_unrelated_exception_is_not_retryable(self):
        assert _is_retryable(ValueError("boom")) is False


@pytest.mark.unit
class TestSendReviewReadyNotification:
    """The public entry point: guards, delivery, and the non-raising contract."""

    @pytest.mark.asyncio
    async def test_returns_false_and_skips_when_no_url(self):
        with patch("core.services.webhook_service._post_with_retry") as mock_post:
            result = await send_review_ready_notification(None, _make_review())

        assert result is False
        mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_false_and_skips_for_invalid_url(self):
        with patch("core.services.webhook_service._post_with_retry") as mock_post:
            result = await send_review_ready_notification("not-a-url", _make_review())

        assert result is False
        mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_true_on_successful_delivery(self):
        with patch("core.services.webhook_service._post_with_retry", new=AsyncMock()) as mock_post:
            result = await send_review_ready_notification(
                "https://example.com/hook", _make_review()
            )

        assert result is True
        mock_post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_false_and_swallows_delivery_failure(self):
        # A persistent failure must NOT raise into the caller (process_review).
        with patch(
            "core.services.webhook_service._post_with_retry",
            new=AsyncMock(side_effect=httpx.ConnectError("down")),
        ):
            result = await send_review_ready_notification(
                "https://example.com/hook", _make_review()
            )

        assert result is False
