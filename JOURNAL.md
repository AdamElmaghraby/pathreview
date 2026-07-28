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

**Summary (short):**
During this week I reproduced the missing-user-notification behavior and began preparing the webhook implementation. I added a unit test that pre-defines the webhook call by patching `send_review_ready_notification` as an `AsyncMock` and updated `test_review_service.py` to assert the notification is awaited once when a review completes. This test will drive the upcoming implementation of the webhook delivery logic and the accompanying API changes.

**Reproduction commit link:** [link to commit documenting the reproduced issue]

**Reproduction summary:**
Reproduced by running the review processing path with mocked pipeline steps; observed that `process_review` completed the review but there was no notification call implemented.

**PLAN.md link:** [link to PLAN.md in your fork]
