# API Reference

Base URL: `http://localhost:8000`

## Endpoints

### Health

`GET /health` — Returns service status and dependency health.

### Authentication

`POST /auth/register` — Create a new account.
`POST /auth/login` — Obtain a JWT access token.

### Profiles

`POST /profiles` — Create a profile with resume and GitHub username.
`GET /profiles/{profile_id}` — Retrieve a profile.
`PUT /profiles/{profile_id}` — Update a profile.
`DELETE /profiles/{profile_id}` — Delete a profile and associated data.

A profile accepts an optional `webhook_url` (on create or update) — the URL that
receives review notifications (see **Webhooks** below).

### Reviews

`POST /reviews` — Request a new portfolio review for a profile.
`GET /reviews/{review_id}` — Retrieve a completed review.
`GET /reviews` — List reviews for the authenticated user (paginated).
`GET /reviews/{review_id}/status` — Poll a review's status/progress.

## Webhooks

If a profile has a `webhook_url` set, PathReview sends an HTTP `POST` to that URL
when one of its reviews reaches a terminal state (`complete` or `failed`), so
clients don't have to poll `GET /reviews/{review_id}/status`.

**Payload:**

```json
{
  "event": "review.ready",
  "review_id": "9f8b...",
  "status": "complete",
  "overall_score": 8.5,
  "updated_at": "2026-08-02T12:34:56+00:00"
}
```

**Delivery semantics:**
- Only `http://` and `https://` URLs are delivered to; others are skipped.
- Transient failures (network errors, `5xx`) are retried with exponential
  backoff; a `4xx` is not retried.
- Delivery is best-effort: a webhook failure is logged but never fails the review.

**Configuration** (environment variables): `WEBHOOK_TIMEOUT_SECONDS` (default
`10.0`), `WEBHOOK_MAX_ATTEMPTS` (default `3`), `WEBHOOK_BACKOFF_FACTOR`
(default `1.0`).

**How to test locally:** point `webhook_url` at a request-capture service (e.g.
`https://webhook.site`) or a local listener, request a review, and watch the POST
arrive when it completes.

## Interactive Docs

When the API is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
