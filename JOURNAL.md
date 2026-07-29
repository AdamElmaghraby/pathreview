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

**Reproduction commit link:** https://github.com/AdamElmaghraby/pathreview/commit/0eca64edef216e7c30c2ebe84c4ceb3e843ce2e4

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
