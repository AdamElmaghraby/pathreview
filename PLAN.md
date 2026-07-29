## Solution plan

**Issue:** [#87 — Implement a webhook system that notifies users when their review is ready](https://github.com/ascherj/pathreview/issues/87)

### Understand

**Root cause.** When a review finishes processing, the system updates its own
database and writes a server log line, but it never reaches outward to the user.
In [`core/services/review_service.py`](core/services/review_service.py), the
`process_review` background task sets `review.status = "complete"`
([line 168](core/services/review_service.py#L168)), stores the sections/score,
commits, and emits `log.info("review_processing_completed", ...)`
([line 176](core/services/review_service.py#L176)) — a server-side log the user
never sees. There is no push mechanism of any kind.

**Expected vs. actual.**
- *Expected:* When a review transitions to `complete` (or `failed`), the user is
  notified in near real time via a webhook, without having to poll.
- *Actual:* The only way a client learns a review is ready is by repeatedly
  calling `GET /{review_id}/status`
  ([`api/routes/reviews.py:139`](api/routes/reviews.py#L139)) and checking
  whether `status == "complete"`. Nothing is delivered to the user.

**Reproduction.** `tests/unit/test_review_service.py::test_process_review_notifies_user_when_complete`
drives `process_review` all the way to `review_processing_completed` and asserts
a notification collaborator was awaited. It fails with *"Awaited 0 times,"*
proving a review can complete successfully while the user is never told.

### Map

Files/modules I expect to touch:

- **`core/services/review_service.py`** — after the success commit
  (~[line 174](core/services/review_service.py#L174)) call the new notification
  function; likely also on the `failed` paths
  ([line 151](core/services/review_service.py#L151),
  [line 189](core/services/review_service.py#L189)).
- **`core/services/webhook_service.py`** *(new)* — the delivery service:
  send an HTTP POST to the subscriber's URL, with retry/backoff on failure.
- **`core/models/review.py`** and/or **`core/models/`** *(new model)* — persist
  where to deliver (a webhook subscription URL per profile/user) and, optionally,
  delivery bookkeeping (e.g. `notified_at`, attempt count, last status).
- **`api/routes/reviews.py`** — currently only `GET /status`; may add an endpoint
  to register/manage a webhook subscription URL for a profile.
- **`alembic/versions/003_*.py`** *(new migration)* — schema for the new
  webhook/subscription fields or table (follows the existing
  `001_initial_schema.py` / `002_add_error_message_to_reviews.py` pattern).
- **`tests/unit/test_review_service.py`** — the failing reproduction test (already
  added); extend with webhook-service unit tests as the feature lands.

### Plan

1. **Define the delivery target.** Add a model/field for a per-profile (or
   per-user) webhook subscription URL, plus an Alembic migration. Decide whether
   delivery state (`notified_at`, attempts) lives on `Review` or a separate table.
2. **Build `webhook_service.py`.** A `send_review_ready_notification(review, url)`
   coroutine that POSTs a JSON payload (review id, status, score, timestamp) to
   the subscriber URL, with a timeout + a small retry/backoff loop and structured
   logging on each attempt.
3. **Wire it into `process_review`.** After the success commit, look up the
   subscription URL and `await send_review_ready_notification(...)`. Handle the
   case where no URL is registered (skip cleanly). Decide failure-path behavior.
4. **Expose subscription management** in `api/routes/reviews.py` so a client can
   register the URL to be notified at.
5. **Turn the reproduction green + add coverage.** Confirm the existing failing
   test passes once wired, and add unit tests for the webhook service itself
   (success, retry, non-2xx response, no-URL-registered).

### Inputs & outputs

- **Input:** a completed (or failed) `Review`, and a registered destination URL
  for the owning profile/user.
- **Output:** an outbound HTTP POST to that URL carrying the review outcome
  (id, status, overall_score, timestamp); persisted delivery state
  (`notified_at` / attempt count); structured log lines for each attempt.
- **No change** to the existing `GET /{review_id}/status` behavior — the webhook
  is additive, so polling clients keep working.

### Risks & unknowns

- **Retries & idempotency.** Naive retries could double-notify. Need a bounded
  backoff and ideally an idempotency signal so the same review isn't delivered
  twice. Unsure yet where to store delivery state.
- **Blocking the background task.** `process_review` runs as a FastAPI
  `background_tasks` job ([`api/routes/reviews.py:43`](api/routes/reviews.py#L43)).
  A slow/hanging webhook endpoint could stall it — need a strict timeout and to
  decide whether delivery should be fire-and-forget.
- **Security.** Outbound POSTs to user-supplied URLs raise SSRF concerns and may
  need a signing secret so receivers can verify authenticity. Unsure how much of
  this is in scope for the issue.
- **Failure-path policy.** Open question: should a `failed` review also fire a
  webhook, or only `complete`? (The failed paths at lines 151 and 189 are where
  that would hook in.)
- **HTTP client choice.** Need to confirm which async HTTP client the project
  already depends on rather than adding a new one.

### Edge cases

- No webhook URL registered for the profile → skip delivery, don't crash the
  review.
- Subscriber returns non-2xx or times out → retry with backoff, then give up and
  log; never fail the review itself because notification failed.
- Review ends in `failed` rather than `complete` → defined, deliberate behavior
  (notify or not — see open question).
- Duplicate / re-run processing for the same review → don't double-notify.
- Malformed or unreachable subscriber URL → validated at registration and handled
  gracefully at send time.
