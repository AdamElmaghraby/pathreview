# ADR-004: Webhook Notifications for Review Completion

## Status
Accepted

## Context
When a review finished processing, `process_review` updated the review's status
in the database and wrote a server-side log line, but nothing reached the user.
The only way for a client to learn a review was ready was to poll
`GET /reviews/{review_id}/status` repeatedly (issue #87). We needed a way to
notify users when a review reaches a terminal state, without introducing new
infrastructure (message brokers, WebSocket servers) that the project doesn't
already run.

We considered three delivery mechanisms:
1. **Outbound webhook** — POST to a URL the user registers. Uses `httpx` and
   `tenacity`, both already dependencies.
2. **WebSocket / server-sent events** — real-time push to the frontend. Requires
   new infrastructure and a persistent connection.
3. **Polling only** — keep the status quo and document it.

And where to store the destination URL:
- A column on `Profile` (reviews are already scoped per-profile).
- A dedicated `webhook_subscriptions` table.
- A column on `User`.

## Decision
Implement an **outbound webhook** delivered from a new
`core/services/webhook_service.py`, and store the destination as a nullable
`webhook_url` column on **`Profile`** (mirroring `portfolio_url`).

- A review firing a webhook happens on **both terminal states**, `complete` and
  `failed`, so users learn either outcome.
- Delivery uses `httpx.AsyncClient` with a `tenacity` retry policy that retries
  **only transient failures** (network errors and `5xx`), giving up immediately
  on `4xx` (a permanent client error that won't succeed on retry).
- Delivery is **best-effort and non-raising**: any failure is logged and
  returned as `False`, never propagated — a webhook problem must never flip a
  successfully completed review to `failed`.
- An invalid or missing URL is skipped (guarded at send time).

`Profile` was chosen over a subscription table because reviews are already
per-profile and `process_review` already loads the profile, so no extra query or
schema surface is needed — the smallest change that fully solves #87.

## Consequences
- No new infrastructure; reuses `httpx` + `tenacity`.
- Polling (`GET /status`) still works — the webhook is purely additive.
- One URL per profile; a use case needing multiple subscribers or per-event
  routing would require migrating to a dedicated subscription table.
- No payload signing (HMAC) yet, so receivers can't cryptographically verify the
  sender. This is a deliberate scope cut for a first iteration and a natural
  follow-up.
- A slow webhook endpoint adds latency to the background task (bounded by
  `webhook_timeout_seconds` and the capped retry count).
