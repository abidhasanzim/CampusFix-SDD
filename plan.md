# CampusFix Implementation Plan

**Authors:** Abid Hasan Zim, Zerin Shaima Meem

Sequences spec.md's acceptance criteria into ordered implementation
slices against the skeleton fixed in contracts.md. No implementation
code is written here. Every function/route named below exists in the
skeleton and currently raises `NotImplementedError` / returns HTTP 501.

## Test run (baseline, before any slice)

```
collected 5 items

tests/test_AC001_submit_request.py::test_AC001 FAILED
tests/test_AC003_assign_and_schedule.py::test_AC003 FAILED
tests/test_AC004_complete_work_order.py::test_AC004 FAILED
tests/test_AC012_incomplete_submission.py::test_AC012 FAILED
tests/test_AC012_incomplete_submission.py::test_AC012_control FAILED

5 failed in 0.77s
```

Every failure is the same shape (HTTP 501, `not_implemented`), from
`campusfix/http.py:api_view` catching `NotImplementedError`. Grouped by
acceptance criterion:

| AC | Failing tests | Route |
|---|---|---|
| AC-001 | `test_AC001` | `POST /api/requests` |
| AC-012 | `test_AC012`, `test_AC012_control` | `POST /api/requests` |
| AC-003 | `test_AC003` | `POST /api/work-orders/{wo}/assign` |
| AC-004 | `test_AC004` | `POST /api/work-orders/{wo}/complete` |

Only these 4 acceptance criteria have an actual pytest file (Project 2's
minimum deliverable is 2 implemented slices, not full coverage). Slices
1–4 below carry those tests; slices 5–9 group the remaining 44
acceptance criteria into coarser, lower-ceremony units — real backlog
items, but not expected to be implemented in this pass.

---

## Slices

### Slice 1 — Submit a request (thin end-to-end path)
- **Goal:** A resident (or front-desk staff on their behalf) submits a complete request and gets a tracking number; an incomplete one is rejected with nothing written.
- **Spec sources:** FR-001, FR-004 (entry-preference save only), FR-014 (suggestion saved, not yet reviewed), FR-019, NFR-02, NFR-10, NFR-14.
- **Criteria:** AC-001, AC-012, AC-019, AC-030, E14.
- **Tests that should turn green:** `tests/test_AC001_submit_request.py::test_AC001`, `tests/test_AC012_incomplete_submission.py::test_AC012`, `tests/test_AC012_incomplete_submission.py::test_AC012_control`.
- **Skeleton to fill in:** `housing.get_current_assignment`, `housing.get_room`, `campus_settings.get_config` (read path), `suggestions.suggest_category_and_priority`/`find_duplicate_candidates`, `maintenance.next_tracking_number`/`create_request`/`save_suggestion`, `entry.set_preference`, `audit.record_change`, `notifications.record_notification`, `intake.submit_request`/`submit_phone_report`, `accounts.get_staff_roles` (front-desk check); routes `POST /api/requests`, `POST /api/requests/phone-intake`.
- **Depends on:** none (first slice).
- **Done when:** the listed tests pass and no previously passing test fails.
- **Status:** not started.

### Slice 2 — Supervisor triage: confirm (status-transition engine)
- **Goal:** A supervisor confirms or overrides a request's category/priority, creating or re-linking its work order; two supervisors triaging at once leave exactly one winner.
- **Spec sources:** FR-006, FR-014 (decision/reviewer/time), NFR-02, NFR-15, FR-002 (ack notice).
- **Criteria:** AC-002, AC-013, AC-015, AC-018, AC-046, E3, E6, E8. (AC-037's Gherkin also requires `GET /api/requests/{tn}`, i.e. `access.get_viewable_request`/`audit.record_view` — Slice 7's job — so AC-037 itself is not fully verifiable until Slice 7 exists, and is listed there instead.)
- **Tests that should turn green:** none yet — test_plan.md rows of the same IDs.
- **Skeleton to fill in:** `maintenance.transition` — implemented here as the **complete** T1–T15 table with row locking and `ConcurrencyError`; every later slice only calls it. Also `maintenance.next_work_order_number`/`create_work_order`/`confirm_triage_decision`, `triage.get_triage_item`/`confirm_triage`; routes `GET /api/triage/{tn}`, `POST /api/triage/{tn}/confirm`.
- **Depends on:** Slice 1.
- **Done when:** the listed criteria pass per test_plan.md and Slice 1's tests still pass.
- **Status:** not started.

### Slice 3 — Dispatch: assign and schedule, with the entry-notice rule
- **Goal:** A supervisor assigns a technician and visit window atomically; the window must satisfy the campus notice rule; a stale version loses the race; a No-Access work order can be rescheduled the same way.
- **Spec sources:** FR-008, FR-004 (notice rule), NFR-08, NFR-17, NFR-15.
- **Criteria:** AC-003, AC-006, AC-020, AC-034, AC-048, E4.
- **Tests that should turn green:** `tests/test_AC003_assign_and_schedule.py::test_AC003`.
- **Skeleton to fill in:** `entry.check_window`/`send_notice`/`cancel_notice`, `dispatch.assign_and_schedule`; route `POST /api/work-orders/{wo}/assign`.
- **Depends on:** Slice 2 (`transition`).
- **Done when:** `test_AC003` plus the rest of this slice's criteria pass per test_plan.md, and Slices 1–2's tests still pass.
- **Status:** not started.

### Slice 4 — Technician fieldwork: start, record entry, complete
- **Goal:** An assigned technician sees only their own assignments, starts a scheduled visit, records entry/failed-access, and completes a work order with required documentation, completing every linked request.
- **Spec sources:** FR-009, FR-010, FR-004 (entry recording).
- **Criteria:** AC-004, AC-017, AC-033, AC-035, E7 (the `complete_work_order` half; the `AC-012` half of E7 was already satisfied by Slice 1).
- **Tests that should turn green:** `tests/test_AC004_complete_work_order.py::test_AC004`.
- **Skeleton to fill in:** `entry.record_visit`, `fieldwork.list_my_assignments`/`start_work`/`record_entry`/`record_no_access`, `maintenance.record_work`, `fieldwork.complete_work_order`, `access.get_viewable_work_order`; routes `GET /api/technician/assignments`, `POST .../start`, `POST .../entries`, `POST .../complete`, `POST .../no-access`.
- **Depends on:** Slice 3.
- **Done when:** `test_AC004` plus the rest of this slice's criteria pass, and Slices 1–3's tests still pass.
- **Status:** not started.

### Slice 5 — Hold, transfer, and clear-hold
- **Goal:** A technician holds in-progress work or requests a transfer back to unassigned triage; a supervisor or the assigned technician clears a documented hold, resuming in place or rescheduling.
- **Spec sources:** FR-011, FR-016.
- **Criteria:** AC-005, AC-016, AC-021, AC-022, E5.
- **Skeleton to fill in:** `maintenance.create_hold_record`/`clear_hold_record`, `fieldwork.place_on_hold`/`request_transfer`/`clear_hold`; routes `.../hold`, `.../transfer`, `.../clear-hold`.
- **Depends on:** Slice 4.
- **Done when:** the listed criteria pass per test_plan.md and all prior slices' tests still pass.
- **Status:** not started.

### Slice 6 — Duplicates, pre-dispatch closure, reopen, and resident-side closure
- **Goal:** A supervisor merges/links duplicate reports without a second dispatch, or closes an invalid request before dispatch; a resident reopens their own completed request without touching shared siblings, adds information, and confirms (or auto-confirms) closure.
- **Spec sources:** FR-005, FR-007, FR-017, FR-018, FR-020, Non-goal 7.
- **Criteria:** AC-007, AC-008, AC-023, AC-024, AC-028, AC-029, AC-031, AC-032, AC-045, E11, E12, E13.
- **Skeleton to fill in:** `maintenance.link_request_to_work_order`, `triage.merge_duplicates`/`link_to_active_work_order`/`close_before_dispatch`, `intake.add_information`/`reopen_request`/`confirm_closure`/`expire_closure`; routes `/triage/merge`, `/triage/{tn}/link`, `/triage/{tn}/close`, `/requests/{tn}/updates`, `/requests/{tn}/reopen`, `/requests/{tn}/confirm-closure`.
- **Depends on:** Slice 2 (`transition`, `create_work_order`).
- **Done when:** the listed criteria pass per test_plan.md and all prior slices' tests still pass.
- **Status:** not started.

### Slice 7 — Privacy, photos, drafts, settings, and entry-preference changes
- **Goal:** A resident views their own request history privately (another resident's tracking number is indistinguishable from nonexistent); uploads/serves photos under campus limits; changes entry preference mid-flow; drafts survive; an administrator edits one campus's settings without touching the other.
- **Spec sources:** FR-001 (banner/draft/photo), FR-003, FR-004 (change-preference), FR-017 (photo), NFR-01, NFR-02, NFR-09, NFR-11, NFR-13, NFR-14 (read-access-preserved half).
- **Criteria:** AC-010, AC-014, AC-036, AC-037, AC-039, AC-040, AC-041, AC-043, E1, E2, E10.
- **Skeleton to fill in:** `access.get_viewable_request`/`get_viewable_photo`, `audit.record_view`, `maintenance.get_status_history`, `notifications.list_my_notifications`, `intake.get_request_detail`/`save_draft`/`get_draft`/`change_entry_preference`, `photos.upload_unattached`/`link_to_request`/`link_to_work_record`/`serve_photo`, `campus_settings.update_config`; routes `GET /api/requests/{tn}`, `GET /api/notifications`, `GET`/`PUT /api/requests/draft`, `PUT /api/requests/{tn}/entry-preference`, `POST /api/photos`, `GET /api/photos/{id}`, `PUT /api/campus-settings/{code}`.
- **Depends on:** Slice 1 (and Slice 3 for the "pending notice" case in AC-014).
- **Done when:** the listed criteria pass per test_plan.md and all prior slices' tests still pass.
- **Status:** not started.

### Slice 8 — Escalations and administrator reports
- **Goal:** CampusFix raises exactly one escalation per overdue urgent/on-hold period; an administrator sees filtered aggregate reports and replacement candidates, with no rule invented when a threshold is unconfigured.
- **Spec sources:** FR-012, FR-013, FR-015.
- **Criteria:** AC-009, AC-011, AC-025, AC-026, AC-027, E9.
- **Skeleton to fill in:** `accounts.get_campus_for_supervisor`, `triage.run_escalation_check`/`list_escalations`, `maintenance.get_equipment_work_history`, `fieldwork.link_equipment`, `access.can_administer`, `reports.get_operational_report`/`get_replacement_candidates`; routes `/triage/escalations`, `.../equipment`, `/reports/operational`, `/reports/replacement-candidates`.
- **Depends on:** Slice 5 (on-hold work orders), Slice 1 (config thresholds).
- **Done when:** the listed criteria pass per test_plan.md and all prior slices' tests still pass.
- **Status:** not started.

### Slice 9 — Platform wiring: notification retry, retention, SSO, scheduled jobs
- **Goal:** A saved event's notification survives an email outage and is never sent twice; photos/entry records are purged at retention; production SSO replaces the dev stub; one cron command runs every periodic check.
- **Spec sources:** NFR-16, FR-002, NFR-07, NFR-10, Domain Model (external systems), Decision 3, Decision 9.
- **Criteria:** AC-042, AC-047. (No AC exercises the SSO redirect/callback itself — AC-043's auth-required check is already satisfied in Slice 1 against the dev stub header.)
- **Skeleton to fill in:** `notifications.send_pending`, `photos.purge_expired`, `entry.purge_expired`, `accounts.start_sso_login`/`complete_sso_login`, `housing.refresh_from_export`, `jobs.run_scheduled_checks`/`refresh_housing`; routes `GET /api/auth/login`, `GET /api/auth/callback`.
- **Depends on:** Slice 4 (notification to retry), Slice 7 (photos to purge), Slice 3 (entry records to purge).
- **Done when:** the listed criteria pass per test_plan.md and all prior slices' tests still pass.
- **Status:** not started.

---

## Coverage notes

- **Criteria that fit no slice:** AC-038 (accessibility) and AC-044 (mobile layout) — test_plan.md defers both to a UI-level audit once templates exist; contracts.md defines no template-rendering function or page route for either, only JSON API routes.
- **Functions/routes with no slice:** none — every function in contracts.md section 1 and every route in section 2 appears in exactly one slice above.
- **Design questions:** none — every slice uses only modules/functions/routes already named in architecture.md and contracts.md.
- **Test issues:** AC-036's test_plan.md row names a third surface ("the submit-form metadata") with no corresponding route in contracts.md section 2. Slice 7 implements the emergency-contacts block only on the two routes that do exist; this gap is flagged rather than resolved, since test_plan.md (not spec.md's AC-036 Gherkin) is the only place it's named.

