## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/87

**Issue title:** Implement a webhook system that notifies users when their review is ready

**Tier:** [ Tier 3 ]

**Problem summary:**

Users currently have no way to know when their review is complete. What is
missing is a mechanism to notify a user when their review is finished. A
successful fix would implement a webhook that updates the user in real time
when their review is ready. This change will touch the API (add a new route)
and core services (add a webhook service to handle delivery and retries).

**Branch name:** 87-ready-for-review-webhook

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/AdamElmaghraby/pathreview/commit/4e08d1b4626ce7c6e1300954094e5ee44338745b

**Reproduction summary:**
I wrote a failing unit test (`test_process_review_notifies_user_when_complete` in
`tests/unit/test_review_service.py`) that drives `process_review` all the way to
its success path — the captured logs show `review_processing_completed` — and then
asserts a notification collaborator was awaited. It fails with *"Awaited 0 times,"*
confirming that a review can finish successfully while the user is never notified.
The only existing way to learn a review is ready is to poll `GET /{review_id}/status`.

**PLAN.md link:** [PLAN.md](https://github.com/AdamElmaghraby/pathreview/blob/feat/87-ready-for-review-webhook/PLAN.md)

**Walkthrough video (recommended):** <!-- optional: paste your Loom link here, or leave blank -->

**Blockers or open questions:**
- Should a `failed` review also fire a webhook, or only a `complete` one?
- Where should webhook subscription URLs and delivery state (`notified_at`,
  attempt count) be stored — on `Review` or a separate table?
- Which async HTTP client does the project already depend on for outbound POSTs?

## Week 9 — Implementation & PR submission

### Mid-week check-in

**Progress:** Resolved the Week 8 open questions and built the feature.
- Store the destination as a nullable `webhook_url` column on `Profile` (mirrors
  `portfolio_url`); added Alembic migration `003`. Chosen over a subscription
  table because reviews are already per-profile and `process_review` already
  loads the profile.
- Threaded `webhook_url` through the profile schema/route/service so it can be
  set on create or update.
- Built `core/services/webhook_service.py` using the project's existing `httpx` +
  `tenacity` deps.
- Decided to notify on **both** `complete` and `failed` (not just complete).

**Design decisions made:** retry only transient failures (network + `5xx`), give
up immediately on `4xx`; delivery is best-effort and non-raising so a webhook
failure can never flip a completed review to `failed`; invalid/missing URLs are
skipped. Documented in [ADR-004](docs/adr/004-webhook-notifications.md).

**Still to do at mid-week:** finish edge-case tests, wire the notification into
all terminal paths of `process_review`, and documentation.

### Submission check-in

**PR link:** <!-- TODO: filled in after the PR is opened -->

**What I built:** An outbound webhook that notifies a profile's `webhook_url`
when a review reaches a terminal state. My Week 8 reproduction test now passes,
plus 10 new unit tests in `tests/unit/test_webhook_service.py` covering the URL
guards, the happy path, the non-raising swallow contract, the transient-vs-
permanent retry decision, and payload shaping. Docs: ADR-004 + an API.md
"Webhooks" section (payload, delivery semantics, how to test).

**Edge cases handled:** no webhook URL configured (skip), non-`http(s)` URL
(skip), subscriber returns `5xx`/times out (retry with backoff), subscriber
returns `4xx` (give up immediately), `failed` reviews (also notified), webhook
delivery failure (logged, never fails the review), missing profile before the
webhook URL is loaded (safe `None` default).

**Honest state / scoping:** My contribution is green and lint-clean (11/11 of my
tests pass; `webhook_service.py` passes ruff + black + mypy). The repository has
extensive *pre-existing* CI failures unrelated to issue #87 (~182 ruff errors,
~51 unformatted files, and pre-existing unit-test failures in modules I never
touched, plus a local Python 3.14 vs. CI 3.11 mismatch). I deliberately scoped
those out rather than bloating the PR with an unrelated repo-wide cleanup, and
cleaned only the files this PR touches.

**Follow-ups (out of scope):** HMAC payload signing so receivers can verify the
sender; delivery bookkeeping (`notified_at`, attempt count); a dedicated
subscription table if multiple subscribers per profile are ever needed.
