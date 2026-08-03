"""Webhook delivery service.

Notifies a user's registered webhook URL when one of their reviews reaches a
terminal state (``complete`` or ``failed``). Delivery is best-effort: failures
are logged and swallowed so that a webhook problem can never fail the review
that triggered it.
"""

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from core.config import settings
from core.models.review import Review

log = structlog.get_logger()


def _build_payload(review: Review) -> dict:
    """Build the JSON body delivered to the subscriber's webhook URL."""
    return {
        "event": "review.ready",
        "review_id": str(review.id),
        "status": review.status,
        "overall_score": review.overall_score,
        "updated_at": review.updated_at.isoformat() if review.updated_at else None,
    }


def _is_retryable(exc: BaseException) -> bool:
    """Retry only transient failures: network errors and 5xx responses.

    A 4xx means the request itself is wrong (bad URL, rejected payload); retrying
    would fail identically, so we give up immediately.
    """
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


@retry(
    stop=stop_after_attempt(settings.webhook_max_attempts),
    wait=wait_exponential(multiplier=settings.webhook_backoff_factor, min=1, max=10),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def _post_with_retry(webhook_url: str, payload: dict) -> None:
    """POST the payload, retrying on network errors and non-2xx responses.

    Raises the last exception if every attempt fails (``reraise=True``); the
    caller is responsible for turning that into a swallowed failure.
    """
    async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()


async def send_review_ready_notification(webhook_url: str | None, review: Review) -> bool:
    """Deliver a webhook notification for a review that reached a terminal state.

    Best-effort and non-raising: a delivery failure is logged and reported via
    the return value, never propagated to the caller.

    Args:
        webhook_url: The subscriber's URL, or ``None`` if none is configured.
        review: The review whose terminal state is being announced.

    Returns:
        ``True`` if the webhook was delivered (2xx); ``False`` if it was skipped
        (no/invalid URL) or every delivery attempt failed.
    """
    if not webhook_url:
        log.info("webhook_skipped_no_url", review_id=str(review.id))
        return False

    if not webhook_url.startswith(("http://", "https://")):
        log.warning(
            "webhook_skipped_invalid_url",
            review_id=str(review.id),
            webhook_url=webhook_url,
        )
        return False

    try:
        await _post_with_retry(webhook_url, _build_payload(review))
        log.info("webhook_delivered", review_id=str(review.id), status=review.status)
        return True
    except Exception as exc:
        log.error(
            "webhook_delivery_failed",
            review_id=str(review.id),
            error=str(exc),
        )
        return False
