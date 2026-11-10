# CampusFix Contracts

**Authors:** Abid Hasan Zim, Zerin Shaima Meem

This document fixes the calling contract between tests and the CampusFix
skeleton, before any business logic is written. Section 1 lists every
public function in every module from architecture.md section 2. Section 2
lists every REST route and the single function it calls.

Every function raises `NotImplementedError` in Project 2. "Injected"
identifies values a caller must supply rather than a function computing
for itself (the server clock, an external system, a sequence) — the same
values a test replaces to make behavior deterministic.

Two cross-cutting types recur below and are not re-defined per function:
- **ConcurrencyError** — raised by `maintenance.transition()` and any
  function that forwards an `expected_version` when the stored version has
  moved (NFR-15: "the second user is told the record has changed").
- **LookupError** — raised by `access.*` and anything that delegates to it
  for both "does not exist" and "exists but you may not see it" (NFR-01,
  Decision 12): the two cases are deliberately indistinguishable.

## 1. Module function contracts

### `accounts` — apps/accounts/services.py
Sign users in through SSO and identify each user's staff role.

#### `start_sso_login(return_url: str) -> str`
- Success: returns the provider's authorization URL as a string.
- Failure: none defined here; a misconfigured provider is a deployment error.
- Spec rule: NFR-10 (university SSO authenticates every user).
- Injected: the SSO provider client (SAML/OIDC, whichever UNO ITS supplies; C5).

#### `complete_sso_login(sso_assertion: dict, now: datetime) -> Person`
- Success: returns the Person for the asserted SSO identity, creating it on first sign-in.
- Failure: raises `PermissionError` if the assertion cannot be validated.
- Spec rule: NFR-10; AC-043.
- Injected: the SSO provider client; `now` for recording first-seen time.

#### `get_staff_roles(person: Person) -> list[StaffRole]`
- Success: returns a (possibly empty) list of StaffRole rows.
- Failure: none defined here.
- Spec rule: Domain Model Actors; consumed by `access` for permission checks.
- Injected: none.

#### `get_campus_for_supervisor(person: Person) -> Campus`
- Success: returns the Campus tied to the supervisor's StaffRole.
- Failure: raises `LookupError` if `person` holds no supervisor role.
- Spec rule: NFR-13 (campus-scoped configuration and queues).
- Injected: none.

### `housing` — apps/housing/services.py
Read-only local copy of campuses, buildings, rooms, and current room assignments.

#### `get_current_assignment(sso_subject: str, as_of_date: date) -> RoomAssignment | None`
- Success: returns the RoomAssignment covering `as_of_date`, or `None`.
- Failure: none; absence of a current assignment is a normal result, not an error.
- Spec rule: FR-001, FR-019 (building/room read-only from housing data); NFR-14.
- Injected: none; reads the local copy, not the university system.

#### `get_room(building: Building, room_number: str) -> Room`
- Success: returns the matching Room.
- Failure: raises `Room.DoesNotExist` if no such room exists.
- Spec rule: FR-001, FR-019.
- Injected: none.

#### `refresh_from_export(export_rows: list[dict], now: datetime) -> dict`
- Success: returns a summary dict of rows created/updated/ended.
- Failure: raises `ValueError` if the export is malformed.
- Spec rule: Domain Model (external systems); Non-goal 6.
- Injected: the university housing export (format TBD, C7); `now`.

### `campus_settings` — apps/campus_settings/services.py
Per-campus configuration values, editable only by authorized administrators.

#### `get_config(campus: Campus) -> CampusConfig`
- Success: returns the campus's CampusConfig.
- Failure: raises `CampusConfig.DoesNotExist` if never configured.
- Spec rule: Configuration values table; NFR-13.
- Injected: none.

#### `update_config(administrator: Person, campus: Campus, changes: dict, now: datetime) -> CampusConfig`
- Success: returns the updated CampusConfig; one campus's change never affects the other's row.
- Failure: raises `PermissionError` if unauthorized; raises `ValueError` if `min_entry_notice` would drop below 24h.
- Spec rule: NFR-13; Decision 15.
- Injected: `now` for the audit trail (via `audit`).

### `audit` — apps/audit/services.py
Append-only view/change log. No update/delete function exists (NFR-02).

#### `record_view(actor: Person, record_type: str, record_id: str, now: datetime) -> AuditEntry`
- Success: returns the created AuditEntry (action="VIEW").
- Failure: none defined.
- Spec rule: NFR-02.
- Injected: `now` as the recorded time.

#### `record_change(actor: Person, record_type: str, record_id: str, changed_fields: list[str], now: datetime) -> AuditEntry`
- Success: returns the created AuditEntry (action="CHANGE") listing `changed_fields`.
- Failure: none defined.
- Spec rule: NFR-02; FR-006, FR-014 (suggestion overrides logged).
- Injected: `now` as the recorded time.

### `maintenance` — apps/maintenance/services.py
Owns requests, work orders, holds, work, parts, equipment, and suggestions.
`transition()` is the only function anywhere in CampusFix that changes
`request_state` or `work_order_status`.

#### `next_tracking_number(year: int) -> str`
- Success: returns a unique `"CF-<year>-<5-digit sequence>"` string.
- Failure: none; the underlying sequence cannot collide.
- Spec rule: Domain Model (trackingNumber format/uniqueness).
- Injected: the per-year PostgreSQL sequence (Decision 11); `year` from the caller's Central-time clock read.

#### `next_work_order_number() -> str`
- Success: returns a unique `"WO-<n>"` string.
- Failure: none.
- Spec rule: Domain Model (workOrderNumber uniqueness).
- Injected: a dedicated PostgreSQL sequence (Decision 11).

#### `create_request(owner, recorded_by, building, room, area_type, exact_location, description, onset, resident_urgency, now) -> MaintenanceRequest`
- Success: returns the created MaintenanceRequest, request_state="SUBMITTED" (T1).
- Failure: raises `ValueError` if a required field is missing or `owner` has no current room assignment.
- Spec rule: FR-001, FR-019; T1.
- Injected: `now` for created_at/updated_at and the T1 history row.

#### `create_work_order(requests, category, priority, prior_work_order, now) -> WorkOrder`
- Success: returns the created WorkOrder, status="ACKNOWLEDGED", linked to every request given (T2 or T14).
- Failure: raises `ValueError` if `requests` is empty or not all in the same building.
- Spec rule: FR-006, FR-007, FR-014; T2, T14.
- Injected: `now` for created_at/updated_at and the history row.

#### `link_request_to_work_order(request, work_order, now) -> WorkOrder`
- Success: returns `work_order` with `request` added to its linked requests.
- Failure: raises `ValueError` if different buildings, or `work_order` is "Completed".
- Spec rule: FR-007.
- Injected: `now` for the request's T2 history row.

#### `transition(record, transition_id, to_status, trigger, actor, now, expected_version) -> MaintenanceRequest | WorkOrder`
- Success: returns the record with its status updated and `version` incremented by one.
- Failure: raises `ValueError` if the (from-status, transition_id, to-status) triple is not one of T1-T15; raises `ConcurrencyError` on a stale `expected_version`.
- Spec rule: Status lifecycle ("MUST reject other state changes"); NFR-15.
- Injected: `now` as the status-history/audit timestamp; row locks via `SELECT ... FOR UPDATE` (work order, then linked requests by id).

#### `record_work(work_order, technician, diagnosis, work_performed, labor_hours, parts, tested_confirmed, now) -> WorkRecord`
- Success: returns the created WorkRecord with its Part rows.
- Failure: raises `ValueError` if diagnosis/work_performed/tested_confirmed is missing when completion is intended.
- Spec rule: FR-010.
- Injected: `now` for created_at/completed_at.

#### `create_hold_record(work_order, technician, reason, part_name, next_action, now) -> HoldRecord`
- Success: returns the created HoldRecord, `cleared_at` unset.
- Failure: raises `ValueError` if `reason="WAITING_FOR_PART"` and `part_name` is blank.
- Spec rule: FR-011.
- Injected: `now` as started_at.

#### `clear_hold_record(hold_record, cleared_by, now) -> HoldRecord`
- Success: returns `hold_record` with `cleared_at`/`cleared_by` set.
- Failure: raises `ValueError` if already cleared.
- Spec rule: FR-016.
- Injected: `now` as cleared_at.

#### `save_suggestion(request, suggested_category, suggested_priority, duplicate_candidate_tracking_numbers, now) -> Suggestion`
- Success: returns the created Suggestion row with final_* fields unset.
- Failure: none defined.
- Spec rule: FR-014.
- Injected: `now`.

#### `confirm_triage_decision(suggestion, final_category, final_priority, reviewer, now) -> Suggestion`
- Success: returns `suggestion` with final_category, final_priority, reviewer, decided_at set.
- Failure: raises `ValueError` if `final_category` or `final_priority` is blank.
- Spec rule: FR-006, FR-014.
- Injected: `now` as decided_at.

#### `get_status_history(record_type: str, record_id: int) -> list[StatusHistoryEntry]`
- Success: returns StatusHistoryEntry rows ordered by `changed_at`.
- Failure: none; unknown id returns an empty list.
- Spec rule: FR-003.
- Injected: none.

#### `get_equipment_work_history(equipment: Equipment) -> list[WorkOrder]`
- Success: returns WorkOrder rows ordered by creation time.
- Failure: none.
- Spec rule: FR-013.
- Injected: none.

### `access` — apps/access/services.py
Decides whether a user may see or act on a record; logs each permitted view.

#### `get_viewable_request(actor: Person, tracking_number: str, now: datetime) -> MaintenanceRequest`
- Success: returns the MaintenanceRequest and records an audit "VIEW" entry.
- Failure: raises `LookupError` for both nonexistent and not-visible.
- Spec rule: NFR-01; AC-010, AC-033, AC-037; Decision 12.
- Injected: `now` for the audit entry.

#### `get_viewable_work_order(actor: Person, work_order_number: str, now: datetime) -> WorkOrder`
- Success: returns the WorkOrder and records an audit "VIEW" entry.
- Failure: raises `LookupError` for both nonexistent and not-visible.
- Spec rule: NFR-01; AC-033, AC-037; Decision 12.
- Injected: `now`.

#### `get_viewable_photo(actor: Person, photo_id: int, now: datetime) -> Photograph`
- Success: returns the Photograph and records an audit "VIEW" entry.
- Failure: raises `LookupError` for both nonexistent and not-visible.
- Spec rule: NFR-01; AC-033.
- Injected: `now`.

#### `can_administer(actor: Person, campus) -> bool`
- Success: returns True or False; never raises for a valid actor.
- Failure: none.
- Spec rule: NFR-01 (administrators see aggregates only).
- Injected: none.

### `notifications` — apps/notifications/services.py
Records and delivers notifications, retrying failed email.

#### `record_notification(recipient, event, tracking_number, channel, content, now) -> Notification`
- Success: returns the created Notification, status="PENDING".
- Failure: none defined; caller must call this only after the event is itself saved.
- Spec rule: FR-002.
- Injected: `now` as created_at.

#### `send_pending(now: datetime) -> int`
- Success: returns the count sent; each sent row's status becomes "SENT".
- Failure: a row stays "PENDING" (not an exception) if UNO email is unavailable.
- Spec rule: NFR-16; AC-047.
- Injected: `now` as sent_at; the UNO SMTP relay (C6).

#### `list_my_notifications(person: Person) -> list[Notification]`
- Success: returns Notification rows addressed to `person`, newest first.
- Failure: none.
- Spec rule: FR-002, FR-003.
- Injected: none.

### `photos` — apps/photos/services.py
Validate, store, and serve photographs privately.

#### `upload_unattached(owner, file_bytes, content_type, campus, now) -> Photograph`
- Success: returns the created Photograph, linked=False.
- Failure: raises `ValueError` if not JPG/PNG by content check, or over `maxPhotoBytes`.
- Spec rule: FR-001; Decision 13.
- Injected: `now`; the campus's `maxPhotoBytes` (via `campus_settings`).

#### `link_to_request(photo, request, campus, now) -> Photograph`
- Success: returns `photo` with linked=True and `request` set.
- Failure: raises `ValueError` if the request already has `maxPhotosPerRequest` linked photos.
- Spec rule: FR-001, FR-017; Decision 13.
- Injected: the campus's `maxPhotosPerRequest`.

#### `link_to_work_record(photo, work_record) -> Photograph`
- Success: returns `photo` with linked=True and `work_record` set.
- Failure: raises `ValueError` if already linked.
- Spec rule: FR-010.
- Injected: none.

#### `serve_photo(actor, photo, now) -> bytes`
- Success: returns the file's bytes.
- Failure: raises `LookupError` if `actor` may not view the linked record.
- Spec rule: NFR-01.
- Injected: `now` for the audit "VIEW" entry.

#### `purge_expired(retention_period: timedelta, now: datetime) -> int`
- Success: returns the count of photographs purged.
- Failure: none.
- Spec rule: NFR-07.
- Injected: `now` as the reference point for age.

### `entry` — apps/entry/services.py
Entry preferences, notices, visits, and the notice rule.

#### `set_preference(request, preference, time_slots, now) -> EntryPreference`
- Success: returns the EntryPreference; any pending EntryNotice for the request's work order is cancelled in the same save.
- Failure: raises `ValueError` if preference="PREFERRED_TIME_SLOTS" with no slots.
- Spec rule: FR-004; AC-014.
- Injected: `now` as updated_at.

#### `check_window(campus_config, visit_window_start, notice_given_at, repair_order_filed) -> bool`
- Success: returns True if elapsed time meets `min_entry_notice` (or `repair_order_notice` when filed and configured); exactly-at-the-limit passes.
- Failure: returns False (does not raise) when short.
- Spec rule: FR-004; NFR-08; NFR-17; Decision 8; AC-006, AC-034, AC-048.
- Injected: none; both timestamps are supplied by the caller.

#### `send_notice(work_order, visit_window_start, notice_given_at, repair_order_exception_used, now) -> EntryNotice`
- Success: returns the created EntryNotice.
- Failure: raises `ValueError` if `check_window` would fail for these inputs.
- Spec rule: FR-004; NFR-08; Decision 8.
- Injected: `now` as the notice's creation stamp.

#### `cancel_notice(entry_notice, now) -> EntryNotice`
- Success: returns `entry_notice` with cancelled=True.
- Failure: raises `ValueError` if already cancelled.
- Spec rule: FR-004; AC-014.
- Injected: `now`.

#### `record_visit(work_order, person, resident_present, knock_and_announce_confirmed, outcome, now) -> VisitRecord`
- Success: returns the created VisitRecord.
- Failure: raises `ValueError` if outcome="ENTERED" without knock-and-announce confirmed.
- Spec rule: FR-004, FR-011; NFR-08; AC-035.
- Injected: `now` as occurred_at.

#### `purge_expired(retention_period: timedelta, now: datetime) -> int`
- Success: returns the count of VisitRecord/EntryNotice rows purged.
- Failure: none.
- Spec rule: NFR-07.
- Injected: `now`.

### `suggestions` — apps/suggestions/services.py
Pure functions; no models, no side effects.

#### `suggest_category_and_priority(description: str, photo_count: int) -> tuple[str, str]`
- Success: returns (category, priority) advisory strings.
- Failure: raises `ValueError` if `description` is blank; caller must treat any error as "unavailable" and continue.
- Spec rule: FR-014; NFR-03; Decision 10.
- Injected: none; pure function.

#### `find_duplicate_candidates(building, room, open_requests) -> list[MaintenanceRequest]`
- Success: returns the subset of `open_requests` in the same room or floor.
- Failure: none; empty input returns an empty list.
- Spec rule: FR-014; NFR-03.
- Injected: none; pure function.

### `intake` — apps/intake/services.py
Resident/front-desk actions on requests; draft and emergency-banner support.

#### `save_draft(person, form_data, now) -> Draft`
- Success: returns the upserted Draft.
- Failure: none.
- Spec rule: NFR-11; AC-039.
- Injected: `now` as updated_at.

#### `get_draft(person: Person) -> Draft | None`
- Success: returns the Draft, or None.
- Failure: none.
- Spec rule: NFR-11; AC-039.
- Injected: none.

#### `submit_request(person, form_data, now) -> MaintenanceRequest`
- Success: returns the created MaintenanceRequest ("Submitted") with tracking number; draft deleted.
- Failure: raises `ValidationError` listing every missing required field, or NFR-14's rule if no current assignment; nothing is created and the draft is kept.
- Spec rule: FR-001; FR-014; NFR-14; AC-001, AC-012, AC-015, AC-039.
- Injected: `now` for every timestamp in the transaction.

#### `submit_phone_report(staff, resident, form_data, now) -> MaintenanceRequest`
- Success: returns the created MaintenanceRequest, owner=resident, recorded_by=staff.
- Failure: same as `submit_request`, plus `PermissionError` if `staff` holds no front-desk role.
- Spec rule: FR-019; AC-030.
- Injected: `now`.

#### `get_request_detail(person, tracking_number, now) -> dict`
- Success: returns a dict with the request, status history, and resident-visible notes only.
- Failure: raises `LookupError` for both nonexistent and belonging to someone else.
- Spec rule: FR-003; NFR-01; AC-003, AC-010.
- Injected: `now` for the audit "VIEW" entry.

#### `add_information(person, tracking_number, comment, photo_bytes, now) -> MaintenanceRequest`
- Success: returns the unchanged MaintenanceRequest; comment/photo appended to history.
- Failure: raises `PermissionError` if not owned by `person`; raises `ValueError` if "Closed".
- Spec rule: FR-017; AC-028.
- Injected: `now`.

#### `reopen_request(person, tracking_number, description, photo_bytes, now) -> MaintenanceRequest`
- Success: returns the request, request_state="REOPENED" (T13), same tracking number.
- Failure: raises `ValueError` if "Closed" or not owned by `person`.
- Spec rule: FR-005; AC-007, AC-045; T13.
- Injected: `now`.

#### `confirm_closure(person, tracking_number, now) -> MaintenanceRequest`
- Success: returns the request, request_state="CLOSED" (T15).
- Failure: raises `ValueError` if not "Completed" or not owned by `person`.
- Spec rule: FR-020; AC-031; T15.
- Injected: `now`.

#### `expire_closure(now: datetime) -> list[MaintenanceRequest]`
- Success: returns the requests closed by this run.
- Failure: none; an unconfigured campus closes nothing.
- Spec rule: FR-020; AC-032; T15.
- Injected: `now` as the reference point for elapsed time.

#### `change_entry_preference(person, tracking_number, preference, time_slots, now) -> MaintenanceRequest`
- Success: returns the MaintenanceRequest (self-transition).
- Failure: raises `PermissionError` if not owned by `person`.
- Spec rule: FR-004; AC-014.
- Injected: `now`, forwarded to `entry.set_preference`.

### `triage` — apps/triage/services.py
Supervisor decisions before dispatch; escalations.

#### `get_triage_item(supervisor, tracking_number, now) -> dict`
- Success: returns a dict with the request and its stored Suggestion (suggested_* only).
- Failure: raises `LookupError` if not found or not triage-eligible.
- Spec rule: FR-014; NFR-03; AC-015, AC-018.
- Injected: `now` for the audit "VIEW" entry.

#### `confirm_triage(supervisor, tracking_number, category, priority, now, expected_version) -> WorkOrder`
- Success: returns the WorkOrder, status="ACKNOWLEDGED" (T2/T14).
- Failure: raises `ValueError` if `category`/`priority` blank; raises `ConcurrencyError` on a stale version.
- Spec rule: FR-006; NFR-15; AC-002, AC-015, AC-046.
- Injected: `now`.

#### `merge_duplicates(supervisor, tracking_numbers, category, priority, now) -> WorkOrder`
- Success: returns one new WorkOrder linked to every named request; all tracking numbers/owners/histories retained.
- Failure: raises `ValueError` if not all in the same building, or any already has active dispatched work.
- Spec rule: FR-007; AC-008, AC-024.
- Injected: `now`.

#### `link_to_active_work_order(supervisor, tracking_number, work_order_number, now) -> WorkOrder`
- Success: returns the WorkOrder with the request added.
- Failure: raises `ValueError` if different buildings, or work order already "Completed".
- Spec rule: FR-007; AC-023.
- Injected: `now`.

#### `close_before_dispatch(supervisor, tracking_number, reason, now) -> MaintenanceRequest`
- Success: returns the request, request_state="CLOSED", `closed_reason` set (T3).
- Failure: raises `ValueError` if active dispatched work exists, or `reason` blank.
- Spec rule: FR-018; AC-029; T3.
- Injected: `now`.

#### `run_escalation_check(campus, now) -> list[Escalation]`
- Success: returns Escalation rows created by this run (empty if none newly overdue); a uniqueness constraint makes a repeat call a no-op.
- Failure: none; an unconfigured limit raises nothing for that rule.
- Spec rule: FR-015; AC-009, AC-027.
- Injected: `now` as the reference point.

#### `list_escalations(supervisor, campus) -> list[Escalation]`
- Success: returns Escalation rows for `campus`, newest first.
- Failure: raises `PermissionError` if not scoped to `campus`.
- Spec rule: FR-015; Decision 9.
- Injected: none.

### `dispatch` — apps/dispatch/services.py
Assign and reassign a technician together with a visit window.

#### `assign_and_schedule(supervisor, work_order_number, technician, visit_window_start, visit_window_end, notice_given_at, repair_order_exception_used, now, expected_version) -> WorkOrder`
- Success: returns the WorkOrder, status="SCHEDULED" (T4); one resident notification, one technician notice; a changed window cancels the old notice.
- Failure: raises `ValueError` if `entry.check_window` rejects the window (neither technician nor window is committed); raises `ConcurrencyError` on a stale version.
- Spec rule: FR-008; NFR-15; AC-003, AC-006, AC-020, AC-034, AC-048.
- Injected: `now`; `notice_given_at` for the entry-notice calculation.

### `fieldwork` — apps/fieldwork/services.py
Actions on dispatched work orders.

#### `list_my_assignments(technician: Person) -> list[WorkOrder]`
- Success: returns only this technician's assigned WorkOrders.
- Failure: none; no assignments returns an empty list.
- Spec rule: FR-009; NFR-01; AC-033.
- Injected: none.

#### `start_work(technician, work_order_number, now, expected_version) -> WorkOrder`
- Success: returns the WorkOrder, status="IN_PROGRESS" (T5).
- Failure: raises `PermissionError` if not the assigned technician; raises `ConcurrencyError` on a stale version.
- Spec rule: FR-010; T5.
- Injected: `now`.

#### `record_entry(technician, work_order_number, resident_present, knock_and_announce_confirmed, outcome, now) -> VisitRecord`
- Success: returns the created VisitRecord.
- Failure: raises `ValueError` if outcome="ENTERED" without knock-and-announce.
- Spec rule: FR-004, FR-010, FR-011; AC-035.
- Injected: `now`.

#### `complete_work_order(technician, work_order_number, diagnosis, work_performed, labor_hours, parts, tested_confirmed, now, expected_version) -> WorkRecord`
- Success: returns the created WorkRecord; the WorkOrder and every linked MaintenanceRequest become "Completed" (T11).
- Failure: raises `ValidationError` listing missing fields without changing status; raises `ValueError` if a private room has no recorded entry; raises `ConcurrencyError` on a stale version.
- Spec rule: FR-010; AC-004, AC-017, AC-047; T11; Decision 20.
- Injected: `now` for the work record, T11 history, and per-owner notifications.

#### `place_on_hold(technician, work_order_number, reason, part_name, next_action, now, expected_version) -> HoldRecord`
- Success: returns the created HoldRecord; WorkOrder becomes "ON_HOLD" (T8).
- Failure: raises `ValueError` if `reason`/`next_action` missing; raises `ConcurrencyError` on a stale version.
- Spec rule: FR-011; AC-005; T8.
- Injected: `now`.

#### `record_no_access(technician, work_order_number, resident_present, now, expected_version) -> WorkOrder`
- Success: returns the WorkOrder, status="NO_ACCESS" (T6); failed-access visit preserved.
- Failure: raises `ConcurrencyError` on a stale version.
- Spec rule: FR-004, FR-011; AC-020, AC-035; T6.
- Injected: `now`.

#### `request_transfer(technician, work_order_number, target_trade, reason, now, expected_version) -> WorkOrder`
- Success: returns the WorkOrder, status="ACKNOWLEDGED", unassigned (T12); earlier work records preserved.
- Failure: raises `ValueError` if `target_trade`/`reason` missing; raises `ConcurrencyError` on a stale version.
- Spec rule: FR-011; AC-016; T12.
- Injected: `now`.

#### `clear_hold(user, work_order_number, resolution, visit_window_start, visit_window_end, now, expected_version) -> WorkOrder`
- Success: returns the WorkOrder in "IN_PROGRESS" (T9, resolution="RESUME_NOW") or "SCHEDULED" (T10, resolution="RESCHEDULE").
- Failure: raises `PermissionError` if resuming and `user` is not the assigned on-site technician; raises `ValueError` if rescheduling without a window; raises `ConcurrencyError` on a stale version.
- Spec rule: FR-016; AC-021, AC-022; T9, T10; Decision 17.
- Injected: `now`.

#### `link_equipment(user, work_order_number, equipment, now) -> WorkOrder`
- Success: returns the WorkOrder with `equipment` set.
- Failure: none defined.
- Spec rule: FR-013.
- Injected: `now`.

### `reports` — apps/reports/services.py
Administrator reports computed on demand (Decision 18).

#### `get_operational_report(administrator, campus, period_start, period_end, building, category) -> dict`
- Success: returns counts/workloads/averages; no resident names, entry records, or photographs.
- Failure: raises `PermissionError` if `administrator` holds no administrator role.
- Spec rule: FR-012; NFR-01; AC-011.
- Injected: none; computed live.

#### `get_replacement_candidates(administrator, campus, now) -> list[dict]`
- Success: returns `{equipment, location, repair_count, work_history}` dicts.
- Failure: raises `ConfigurationError` (a "rule not configured" result, not a hidden screen) if the thresholds are unset.
- Spec rule: FR-013; AC-025, AC-026.
- Injected: `now` as the reference point for the repair window.

### `jobs` — apps/jobs/services.py
Scheduled checks, run by cron every 5 minutes; **no HTTP route** (architecture Decision 9: management command only).

#### `run_scheduled_checks(now: datetime) -> dict`
- Success: returns a summary dict of what each sub-check did.
- Failure: none; one sub-check failing does not block the others.
- Spec rule: FR-015, FR-020; NFR-07, NFR-16; Decision 9.
- Injected: `now`, read once and passed to every sub-check.

#### `refresh_housing(now: datetime) -> dict`
- Success: returns the summary dict from `housing.refresh_from_export`.
- Failure: raises `ValueError` if the export cannot be read; the local copy is left unchanged.
- Spec rule: Domain Model; Decision 3.
- Injected: `now`; the university housing export (C7).

## 2. REST API routes

Every route is a thin wrapper (`campusfix/http.py:api_view`) that calls
exactly one function from section 1 and returns its result as JSON. Until
that function is implemented, every route returns:

```
HTTP 501
{"error": "not_implemented", "message": "<module>.<view> is not implemented yet"}
```

Routes map one-to-one to the spec.md requirements that need a user-facing
entry point. `jobs` has no route (cron-only). `maintenance`, `housing`,
`audit`, `access`, `suggestions`, and `entry` have no route of their own —
they are called *through* the routes below (e.g. `intake.submit_request`
calls `maintenance.create_request`, `entry.set_preference`, and
`suggestions.suggest_category_and_priority` once implemented).

Authentication note: every route reads `request.person`, attached by
`apps/accounts/middleware.py:AttachPersonMiddleware` from the
`X-Debug-Person-Id` header — the stub login architecture.md C5 allows for
development. The production path is `accounts.complete_sso_login` (NFR-10),
not yet wired to route middleware.

| Method & Path | Function | Spec rule |
|---|---|---|
| `GET /api/auth/login` | `accounts.start_sso_login` | NFR-10 |
| `GET /api/auth/callback` | `accounts.complete_sso_login` | NFR-10; AC-043 |
| `GET /api/campus-settings/{campus_code}` | `campus_settings.get_config` | NFR-13 |
| `PUT /api/campus-settings/{campus_code}` | `campus_settings.update_config` | NFR-13; AC-040 |
| `GET /api/notifications` | `notifications.list_my_notifications` | FR-002 |
| `POST /api/photos` | `photos.upload_unattached` | FR-001, FR-010, FR-017 |
| `GET /api/photos/{photo_id}` | `photos.serve_photo` | NFR-01 |
| `PUT /api/requests/draft` (also `GET`) | `intake.save_draft` / `intake.get_draft` | FR-001; NFR-11; AC-039 |
| `POST /api/requests` | `intake.submit_request` | FR-001; AC-001, AC-012, AC-015, AC-019 |
| `POST /api/requests/phone-intake` | `intake.submit_phone_report` | FR-019; AC-030 |
| `GET /api/requests/{tracking_number}` | `intake.get_request_detail` | FR-003; AC-003, AC-010 |
| `PUT /api/requests/{tracking_number}/entry-preference` | `intake.change_entry_preference` | FR-004; AC-014 |
| `POST /api/requests/{tracking_number}/reopen` | `intake.reopen_request` | FR-005; AC-007, AC-045 |
| `POST /api/requests/{tracking_number}/updates` | `intake.add_information` | FR-017; AC-028 |
| `POST /api/requests/{tracking_number}/confirm-closure` | `intake.confirm_closure` | FR-020; AC-031, AC-032 |
| `GET /api/triage/{tracking_number}` | `triage.get_triage_item` | FR-014; AC-015, AC-018 |
| `POST /api/triage/{tracking_number}/confirm` | `triage.confirm_triage` | FR-006; AC-002, AC-015, AC-046 |
| `POST /api/triage/merge` | `triage.merge_duplicates` | FR-007; AC-008, AC-024 |
| `POST /api/triage/{tracking_number}/link` | `triage.link_to_active_work_order` | FR-007; AC-023 |
| `POST /api/triage/{tracking_number}/close` | `triage.close_before_dispatch` | FR-018; AC-029 |
| `GET /api/triage/escalations` | `triage.list_escalations` | FR-015; AC-009, AC-027 |
| `POST /api/work-orders/{work_order_number}/assign` | `dispatch.assign_and_schedule` | FR-008; AC-003, AC-006, AC-020, AC-034, AC-048 |
| `GET /api/technician/assignments` | `fieldwork.list_my_assignments` | FR-009; AC-033 |
| `POST /api/work-orders/{work_order_number}/start` | `fieldwork.start_work` | FR-010 (T5) |
| `POST /api/work-orders/{work_order_number}/entries` | `fieldwork.record_entry` | FR-004, FR-010, FR-011; AC-035 |
| `POST /api/work-orders/{work_order_number}/complete` | `fieldwork.complete_work_order` | FR-010; AC-004, AC-017, AC-047 |
| `POST /api/work-orders/{work_order_number}/hold` | `fieldwork.place_on_hold` | FR-011; AC-005 |
| `POST /api/work-orders/{work_order_number}/no-access` | `fieldwork.record_no_access` | FR-011; AC-020, AC-035 |
| `POST /api/work-orders/{work_order_number}/transfer` | `fieldwork.request_transfer` | FR-011; AC-016 |
| `POST /api/work-orders/{work_order_number}/clear-hold` | `fieldwork.clear_hold` | FR-016; AC-021, AC-022 |
| `POST /api/work-orders/{work_order_number}/equipment` | `fieldwork.link_equipment` | FR-013 |
| `GET /api/reports/operational` | `reports.get_operational_report` | FR-012; AC-011 |
| `GET /api/reports/replacement-candidates` | `reports.get_replacement_candidates` | FR-013; AC-025, AC-026 |

**Requirement coverage check** (every FR-001..FR-020 and the two NFRs with
a dedicated user-facing action): FR-001 ✓ (submit, draft), FR-002 ✓
(notifications), FR-003 ✓ (detail), FR-004 ✓ (entry-preference, entries),
FR-005 ✓ (reopen), FR-006 ✓ (confirm), FR-007 ✓ (merge, link), FR-008 ✓
(assign), FR-009 ✓ (assignments), FR-010 ✓ (start, complete), FR-011 ✓
(hold, no-access, transfer), FR-012 ✓ (operational report), FR-013 ✓
(replacement-candidates, equipment), FR-014 ✓ (triage item), FR-015 ✓
(escalations), FR-016 ✓ (clear-hold), FR-017 ✓ (updates), FR-018 ✓
(close), FR-019 ✓ (phone-intake), FR-020 ✓ (confirm-closure), NFR-10 ✓
(auth), NFR-13 ✓ (campus-settings). No route exists with no requirement
behind it (checked against section 1 and architecture.md section 2).
