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

**PR link:** https://github.com/AdamElmaghraby/pathreview/pull/1

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

## Week 10 — Iteration & reflection

### Reviewer feedback

**Feedback received:** [ ] Yes  [x] No — still awaiting review

**Summary of feedback:**
No reviewer feedback came in (per the Summer 2026 note, reviewer feedback isn't
provided this term). My PR (#1) is open with no comments or reviews as of
submission.

**How you responded:**
N/A — no feedback to respond to.

---

### Reflection

**What was harder than you expected?**
Working in what felt like a real production environment, not a clean tutorial
repo. The codebase already had a lot of bugs and broken CI before I wrote a
single line — around 182 ruff errors, ~51 unformatted files, and 53 failing unit
tests. The hardest part wasn't writing my feature; it was figuring out which
failures were *mine* and which were pre-existing. Early on I hit a confusing
`'coroutine' object has no attribute 'first'` error and had to learn it was a
Python 3.14-vs-CI-3.11 mismatch, not something I broke. Separating my own
responsibility from the repo's existing mess was a skill I didn't expect to need.

**What did you learn about working in a large codebase?**
Not to reinvent the wheel. Instead of inventing my own approach, the move was to
copy an existing pattern — I mirrored the `portfolio_url` field everywhere to add
`webhook_url`, which made my change predictable and easy to review. I also had to
follow conventions I didn't set: Conventional Commits with a scope, the Alembic
migration chain, writing an ADR to document *why*, and matching the project's
docstring/test style. Contributing to someone else's production code is less
about clever code and more about fitting in with how the project already works.

**How did AI tools help — and where did they fall short?**
AI was most useful for implementing — tracing an unfamiliar codebase quickly,
explaining testing and mocking, and scaffolding the service. Where it fell short
was wide-scope context and judgment: it couldn't make the decisions that were
actually mine to make — where to store the webhook URL, whether to notify on
`failed` as well as `complete`, whether to retry on `4xx`, and how ambitiously to
scope the PR. Those came down to my own judgment, and AI could lay out
trade-offs but not decide for me.

**What would you do differently if you started over?**
I'd pick a lower-tier issue. I chose a Tier-3 webhook system, and I ended up
spending most of my time learning testing and implementation details rather than
learning the thing this module was really about — how to contribute to a
production open-source project. A smaller issue would have let me spend more of
my energy on the contribution workflow (reviewing conventions, scoping, PR
hygiene) instead of on the mechanics of building the feature.

**What are you most proud of?**
I now actually understand how contributing works in a real engineering
environment — branching and PR conventions, writing tests and docs to a
project's standard, scoping a change so it stays reviewable, and being honest in
the PR about what does and doesn't pass CI instead of pretending everything is
green. That understanding is worth more to me than the feature itself.
