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
