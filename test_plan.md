# CampusFix Test Plan

**Authors:** Abid Hasan Zim, Zerin Shaima Meem

This plan refines spec.md's Acceptance Criteria (AC-001..AC-048) into
concrete test cases against the routes and functions fixed in
contracts.md. Expected values below are computed by hand from spec.md;
where spec.md deliberately leaves a configuration value unset (Spec issue
8 in architecture.md), this plan assumes a **test fixture value**, called
out explicitly so it is never mistaken for a spec-given number.

## Test fixtures assumed by this plan

Spec.md intentionally does not set these (architecture.md Spec issue 8).
Values marked "(spec-fixed)" come directly from spec.md; everything else
is a fixture this plan invented to make expected values computable.

| Key | Value | Source |
|---|---|---|
| `minEntryNotice` | 24 hours | spec-fixed (HRL Community Policies 2025-26) |
| `repairOrderNotice` (Dodge) | 4 hours | fixture |
| `urgentResponseLimit` (Dodge) | 4 hours | fixture |
| `holdLimit` (Dodge) | 72 hours | fixture |
| `closureConfirmationPeriod` (Dodge) | 7 days | fixture |
| `closureConfirmationPeriod` (Scott) | unset | fixture (deliberately, for AC-032) |
| `repeatRepairCount` / `repeatRepairWindow` (Dodge) | 3 / 90 days | spec-given, in AC-025 itself |
| `repeatRepairCount` (Scott) | unset | fixture (deliberately, for AC-026) |
| `retentionPeriod` | 365 days | fixture |
| `maxPhotoBytes` | 5,000,000 (5 MB) | fixture |
| `maxPhotosPerRequest` | 6 | fixture |

Fixture identities: resident `alice` (Dodge, Maverick Village room 101,
Private bedroom), resident `bob` (same building/room, Dodge), resident
`carla` (housing assignment ended yesterday), supervisor `dana` (Dodge),
technician `eli` (plumbing, Dodge), technician `zara` (plumbing, Dodge,
unrelated work orders), administrator `morgan`, front-desk `sam`.

## 1. Acceptance-criteria table

| ID | Requirement | Cases | Inside/Outside | Control |
|---|---|---|---|---|
| AC-001 | FR-001, FR-014 | `POST /api/requests` as alice, all required fields + default urgency, no photos → **201**, body `{tracking_number: ~"CF-2026-\d{5}", status:"SUBMITTED"}`. Side effects: exactly 1 `MaintenanceRequest` row; `building`/`room` taken from housing data, not the payload; 1 `Suggestion` row (suggested_* set, final_* null); 1 confirmation `Notification`. | N/A — no numeric limit in this criterion. | N/A — not a rejection. |
| AC-002 | FR-006, FR-014 | Setup: CF-2026-00010 has stored `Suggestion(suggested_priority="NORMAL")`. `POST /api/triage/CF-2026-00010/confirm` as dana `{category:"PLUMBING", priority:"HIGH", expected_version:1}` → **200**, `status:"ACKNOWLEDGED"`. Side effects: `Suggestion.final_priority="HIGH"` (suggested value retained unchanged); `AuditEntry(action="CHANGE")` logs the override; reviewer=dana, decided_at set. | N/A. | Confirming the **same** value as suggested (`priority:"NORMAL"`) is also accepted — shows override isn't required, just logged either way. |
| AC-003 | FR-008, FR-002 | Setup: WO-1187 Acknowledged, no technician. `POST /api/work-orders/WO-1187/assign` as dana `{technician_id: eli.id, visit_window_start: now+30h, visit_window_end: now+31h, notice_given_at: now, expected_version:1}` → **200**, `status:"SCHEDULED"`. Side effects: exactly 1 `Notification` to alice naming trade+window; exactly 1 to eli. | Notice boundary tested in AC-006/AC-048, not repeated here. | See extra row E4 for the atomic-rejection control. |
| AC-004 | FR-009, FR-010, FR-002 | Setup: WO-1187 In Progress, eli assigned, linked to CF-2026-00010 (alice) and CF-2026-00011 (bob). `POST /api/work-orders/WO-1187/complete` as eli `{diagnosis:"Washer worn", work_performed:"Replaced washer", labor_hours:"1.50", parts:[["Washer",1]], tested_confirmed:true, expected_version:2}` → **201**. Side effects: 1 `WorkRecord`; `WorkOrder.status="COMPLETED"`; **both** CF-2026-00010 and CF-2026-00011 become `COMPLETED`; 2 Notifications, each naming only its own owner's tracking number. | N/A. | Paired rejection is AC-017. |
| AC-005 | FR-011, FR-002 | Setup: WO-1187 In Progress. `POST /api/work-orders/WO-1187/hold` as eli `{reason:"WAITING_FOR_PART", part_name:"Washer", next_action:"Order from vendor", expected_version:2}` → **201**. Side effects: `HoldRecord` created; `WorkOrder.status="ON_HOLD"`; hold Notification to each linked owner. | N/A (categorical, see E5 for the part-name rule). | See extra row E5. |
| AC-006 | FR-004, NFR-08 | Setup: WO Acknowledged, private bedroom, no repair-order exception; `notice_given_at = T0`. | **Outside** (rejected): `visit_window_start = T0+23h59m59s` → `assign_and_schedule` → **422** `{"error":"invalid_window"}`; side effect: `WorkOrder` stays Acknowledged, no `EntryNotice` created. **Inside** (accepted): `visit_window_start = T0+24h00m00s` exactly → **200**, `status:"SCHEDULED"`, `EntryNotice` created — NFR-17 "exactly at the limit satisfies it". | The Inside case is the Control: identical payload, only the window start differs, so the Outside rejection is wrong in exactly one way. |
| AC-007 | FR-005 | Setup: CF-2026-00010 Completed, linked WO-1187 Completed. `POST /api/requests/CF-2026-00010/reopen` as alice `{description:"Faucet leaking again"}` → **200**, `status:"REOPENED"`, same tracking number. Side effects: WO-1187 status stays `COMPLETED` (not reopened); prior `WorkRecord`s still readable. | N/A. | See extra row E12 (reopening a Closed request). |
| AC-008 | FR-007 | Setup: CF-2026-00020 (alice) and CF-2026-00021 (bob), same building/room, both Submitted. `POST /api/triage/merge` as dana `{tracking_numbers:["CF-2026-00020","CF-2026-00021"], category:"PLUMBING", priority:"HIGH"}` → **201**. Side effects: exactly 1 new `WorkOrder` linked to both; each keeps its own owner/tracking number; bob's `GET` detail never shows alice's description. | N/A. | AC-024 (different buildings) is the paired rejection control. |
| AC-009 | FR-015 | Setup: CF-2026-00030, `resident_urgency="URGENT"`, Submitted at `T0`; Dodge `urgentResponseLimit=4h`. | **Inside** (not yet due): `run_escalation_check(now=T0+3h59m59s)` → 0 Escalations. **Outside** (due): `run_escalation_check(now=T0+4h00m00s)` → exactly 1 `Escalation(kind="URGENT_SUBMITTED")`; side effect: request state and priority unchanged. | See extra/AC-027 for the idempotency control (repeated run raises no second escalation). |
| AC-010 | FR-003, NFR-01 | Setup: CF-2026-00040 owned by bob. `GET /api/requests/CF-2026-00040` as alice → **404** `{"error":"not_found"}`. `GET /api/requests/CF-2026-99999` (nonexistent) as alice → same 404 shape. Side effect: no audit "VIEW" entry is written for either denied attempt (only permitted views are logged). | N/A. | `GET /api/requests/CF-2026-00040` as **bob** (the owner) → 200 with full detail — proves the 404 is about permission, not a routing bug. |
| AC-011 | FR-012 | Setup: historical work orders across Dodge/Scott, various categories/dates. `GET /api/reports/operational?building=Maverick+Village&category=PLUMBING&period_start=2026-01-01&period_end=2026-03-01` as morgan → **200**; counts reflect only the filtered subset; no resident names/photos/entry records in the body. | **Inside**: a work order `created_at` exactly = `period_start` → included. **Outside**: `created_at = period_start - 1s` → excluded. | Same call with no filters returns the full unfiltered counts — proves filtering is actually applied, not a constant-zero bug. |
| AC-012 | FR-001 | `POST /api/requests` as alice, `exact_location` and `description` both missing → **422**, `missing_fields:["exact_location","description"]`. Side effects: `MaintenanceRequest.objects.count()` unchanged; alice's `Draft` keeps the entered values. | **Inside**: all three required fields present with a single non-blank character each → **201**. **Outside**: `exact_location=""` (empty string) → listed as missing. | AC-001 (all fields present) is the natural control. |
| AC-013 | FR-002 | Setup: CF-2026-00050 Submitted, owned by alice. `POST /api/triage/CF-2026-00050/confirm` as dana `{category:"ELECTRICAL", priority:"NORMAL", expected_version:1}` → **200**. Side effect: exactly 1 `Notification` to alice, `event="ACKNOWLEDGED"`, naming only CF-2026-00050. | N/A. | N/A. |
| AC-014 | FR-004 | Setup: CF-2026-00050 Scheduled, pending uncancelled `EntryNotice`. `PUT /api/requests/CF-2026-00050/entry-preference` as alice `{preference:"ALLOW_ENTRY_WHILE_AWAY"}` → **200**. Side effects: `EntryPreference` updated; the existing `EntryNotice.cancelled=True`; staff-facing triage item flags that a new window/notice is required. | N/A. | N/A. |
| AC-015 | FR-006, FR-014 | Setup: Dodge `suggestionsEnabled=False`; CF-2026-00060 Submitted, no `Suggestion` row. `POST /api/triage/CF-2026-00060/confirm` as dana `{category:"HVAC", priority:"LOW", expected_version:1}` → **200**, `ACKNOWLEDGED`. | N/A. | Same call shape on a campus **with** suggestions enabled (AC-002's setup) also succeeds — manual triage works either way. |
| AC-016 | FR-011 | Setup: WO-1188 Scheduled, eli assigned, pending `EntryNotice`. `POST /api/work-orders/WO-1188/transfer` as eli `{target_trade:"ELECTRICAL", reason:"Needs licensed electrician", expected_version:2}` → **200**, `status:"ACKNOWLEDGED"`, `assigned_technician:null`. Side effects: `EntryNotice.cancelled=True`; prior `WorkRecord`s preserved. | N/A. | See extra row E13-adjacent note: missing `reason`/`target_trade` rejected (not separately numbered; covered by the "wrong in one way" rule applied to this same call with a blank field). |
| AC-017 | FR-010 | Setup: WO-1187 In Progress. `POST /api/work-orders/WO-1187/complete` as eli `{diagnosis:"", work_performed:"Replaced washer", labor_hours:"1.0", tested_confirmed:true, expected_version:2}` → **422**, `missing_fields:["diagnosis"]`. Side effect: `WorkOrder.status` unchanged ("IN_PROGRESS"); no `WorkRecord` row created. | N/A (categorical). | AC-004 (all fields present) is the control. |
| AC-018 | FR-014 | `GET /api/triage/CF-2026-00060` as dana before confirming → **200**; `suggestion.suggested_category`/`suggested_priority` present; `suggestion.final_category`/`final_priority` are `null`; no `work_order` auto-created. | N/A. | N/A. |
| AC-019 | FR-001, NFR-04, NFR-06 | `POST /api/requests` as alice, all required fields, `photos:[]` → **201** with tracking number. | N/A. | Same payload **with** one linked photo also returns 201 — photos are optional either way. |
| AC-020 | FR-004, FR-008, FR-011 | Setup: WO-1189 `status="NO_ACCESS"` after a recorded failed visit. `POST /api/work-orders/WO-1189/assign` as dana `{technician_id: eli.id, visit_window_start: now+25h, visit_window_end: now+26h, notice_given_at: now, expected_version:3}` → **200**, `SCHEDULED`. Side effects: the prior failed-access `VisitRecord` is preserved (not deleted); a new `EntryNotice` is created. | Notice boundary covered in AC-006, not repeated. | N/A. |
| AC-021 | FR-016 | Setup: WO-1187 On Hold, `HoldRecord(reason="WAITING_FOR_PART")`. `POST /api/work-orders/WO-1187/clear-hold` as dana `{resolution:"RESCHEDULE", visit_window_start: now+30h, visit_window_end: now+31h, expected_version:4}` → **200**, `SCHEDULED`. Side effects: `HoldRecord.cleared_at`/`cleared_by=dana` set; Notifications to eli and all linked owners. | N/A. | N/A. |
| AC-022 | FR-016, FR-010 | Setup: WO-1187 On Hold, eli assigned, today's `VisitRecord` exists (on-site evidence). `POST /api/work-orders/WO-1187/clear-hold` as **eli** `{resolution:"RESUME_NOW", expected_version:4}` → **200**, `IN_PROGRESS`. Side effect: `HoldRecord.cleared_by=eli`. | N/A. | Same call by **dana** (supervisor, not the assigned technician) with `resolution:"RESUME_NOW"` → **403** — the one-field difference (actor) isolates the rule. |
| AC-023 | FR-007 | Setup: WO-1190 Scheduled, linked to CF-2026-00070 (alice); CF-2026-00071 (bob) newly Submitted, same building, same problem. `POST /api/triage/CF-2026-00071/link` as dana `{work_order_number:"WO-1190"}` → **200**. Side effects: `WorkOrder.objects.count()` unchanged (still 1, WO-1190 only); no new `EntryNotice`/visit; bob's detail view shows only his own report plus shared progress. | N/A. | AC-024 is the paired rejection control. |
| AC-024 | FR-007 | Setup: CF-2026-00080 (Maverick Village, Dodge) and CF-2026-00081 (Scott Hall, Scott), both Submitted. `POST /api/triage/merge` as dana with both tracking numbers → **422**, `{"error":"invalid_merge"}`. Side effect: `WorkOrder.objects.count()` unchanged; both requests remain Submitted, unlinked. | N/A (categorical). | AC-008 (same building) is the paired control. |
| AC-025 | FR-013 | Setup: Dodge `repeatRepairCount=3`, `repeatRepairWindow=90 days`; equipment "Water Heater #4" has 3 work orders within 90 days. `GET /api/reports/replacement-candidates` as morgan → **200**; candidate list includes it with `repair_count=3` and full work history. | **Inside**: a 4th equipment's oldest of 3 work orders is exactly 90 days old → included. **Outside**: oldest is 90 days + 1 second old → only 2 count, excluded. | Equipment with only 2 work orders in the window is **not** listed — the threshold is enforced, not cosmetic. |
| AC-026 | FR-013 | Setup: Scott `repeatRepairCount` unset. `GET /api/reports/replacement-candidates` as a Scott administrator → **200**; `candidates:[]`; `rule_configured:false`; message states the rule is not configured. | N/A. | AC-025 (Dodge, configured) is the paired control — real candidates are returned there, proving Scott's empty result is about configuration, not a bug. |
| AC-027 | FR-015 | Setup: WO-1187 On Hold since `T0`; `holdLimit=72h`. | **Inside**: `run_escalation_check(now=T0+71h59m59s)` → 0 Escalations. **Outside/due**: `run_escalation_check(now=T0+72h00m00s)` → 1 `Escalation(kind="HOLD_OVERDUE")`. | Re-running `run_escalation_check(now=T0+80h)` for the same overdue period → 0 **new** Escalations (still 1 total); `WorkOrder.status` unchanged. |
| AC-028 | FR-017 | Setup: CF-2026-00090 Scheduled, owned by alice. `POST /api/requests/CF-2026-00090/updates` as alice `{comment:"Noise got worse"}` → **200**. Side effects: tracking number and `request_state` unchanged; `MaintenanceRequest.objects.count()` unchanged; comment visible to staff in history. | N/A. | See extra row E13 (adding info to another resident's / a Closed request). |
| AC-029 | FR-018 | Setup: CF-2026-00100 Submitted, no work order. `POST /api/triage/CF-2026-00100/close` as dana `{reason:"Not a maintenance issue - furniture complaint"}` → **200**, `CLOSED`. Side effects: owner notified with the reason text; `WorkOrder.objects.count()` unchanged. | N/A. | See extra row E11-adjacent: a request with active dispatched work cannot be closed this way (tests FR-018's eligibility clause). |
| AC-030 | FR-019 | Setup: sam holds a front-desk role; alice has a current assignment. `POST /api/requests/phone-intake` as sam `{resident:"alice", area_type:"COMMON_AREA", exact_location:"Lounge TV", description:"TV won't turn on"}` → **201**. Side effects: `owner=alice`, `recorded_by=sam`; confirmation notification goes to alice, not sam. | N/A. | See extra row E8-adjacent: a non-front-desk staff member attempting this call is rejected (role check mirrors E8). |
| AC-031 | FR-020 | Setup: CF-2026-00010 Completed. `POST /api/requests/CF-2026-00010/confirm-closure` as alice `{}` → **200**, `CLOSED`. Side effect: a subsequent reopen attempt on it returns the same rejection as E12. | N/A. | N/A. |
| AC-032 | FR-020 | Setup: Scott `closureConfirmationPeriod` unset; CF-2026-00110 Completed since `T0`. `expire_closure(now=T0+365d)` → returns `[]`; request stays `COMPLETED`. | Dodge control case (configured, 7 days) below doubles as the Inside/Outside check for this rule. | Dodge request Completed at `T0` (campus has `closureConfirmationPeriod=7d`): **Inside** `expire_closure(now=T0+6d23h59m59s)` → not yet closed; **Outside/due** `expire_closure(now=T0+7d00m00s)` → closed. This proves Scott's non-closure is about missing config, not a general bug. |
| AC-033 | FR-009, NFR-01 | Setup: WO-1187 assigned to eli; WO-1191 assigned to zara. `GET /api/technician/assignments` as eli → **200**, `work_orders:["WO-1187"]` only. `GET /api/photos/{zara's photo id}` as eli by direct URL → **404** (not 403, per Decision 12). | N/A. | `GET /api/technician/assignments` as zara → `["WO-1191"]` only — filtering is per-technician, not a blanket-empty bug. |
| AC-034 | FR-004, NFR-08 | Setup: Dodge `repairOrderNotice=4h`; WO-1192 Acknowledged; a repair order already filed. `POST /api/work-orders/WO-1192/assign` as dana `{..., visit_window_start: now+4h, notice_given_at: now, repair_order_exception_used:true, expected_version:1}` → **200**, `SCHEDULED`. Side effect: `EntryNotice.repair_order_exception_used=True`. | **Inside**: window at exactly `notice_given_at+4h00m00s` → accepted. **Outside**: `notice_given_at+3h59m59s` → rejected. | The Outside case **without** the exception flag (or with no repair order filed) is also rejected under the plain 24h rule — cross-referenced to AC-006, not re-tested here. |
| AC-035 | FR-004, FR-011 | Setup: CF-2026-00010 preference=`"PRESENT"`, WO-1187 Scheduled, visit window now. `POST /api/work-orders/WO-1187/entries` as eli `{resident_present:false, knock_and_announce_confirmed:true, outcome:"NO_ACCESS"}` → **201**. Side effects: `VisitRecord(outcome="NO_ACCESS")`; `WorkOrder.status="NO_ACCESS"`. | N/A. | Same call with `resident_present:true, outcome:"ENTERED"` → **201** and the work order is **not** set to No Access — isolates the outcome/presence combination as the deciding factor. |
| AC-036 | FR-001, NFR-09 | `GET /api/requests/draft` (dashboard), the submit-form metadata, and `GET /api/requests/CF-2026-00010` (details) as alice each → body includes an `emergency_contacts` block and the "handled outside normal intake" disclaimer. | N/A. | N/A. |
| AC-037 | NFR-02 | `GET /api/requests/CF-2026-00010` as dana (permitted) → **200**; side effect: exactly 1 new `AuditEntry(action="VIEW")`. `POST /api/triage/CF-2026-00010/confirm` as dana → side effect: 1 new `AuditEntry(action="CHANGE")` listing `request_state` among `changed_fields`. | N/A. | N/A. |
| AC-038 | NFR-05 | Deferred to a UI-level WCAG 2.1 AA audit once templates exist (architecture.md Decision 19); not exercised by a REST contract call. | N/A. | N/A. |
| AC-039 | NFR-11 | `PUT /api/requests/draft` as alice `{form_data:{description:"partial"}}` → **200**. `GET /api/requests/draft` as alice → returns the same `form_data` unchanged. Photo-retry behavior requires a fault-injection hook on `photos.upload_unattached`, noted for when that function is implemented. | N/A. | N/A. |
| AC-040 | NFR-13 | `PUT /api/campus-settings/DODGE` as morgan `{hold_limit_hours:96}` → **200**. `GET /api/campus-settings/SCOTT` as morgan → `hold_limit` unchanged from its original value. | N/A. | `GET /api/campus-settings/DODGE` confirms the Dodge change **did** apply — proves Scott's unchanged value isn't a universal no-op. |
| AC-041 | NFR-14 | Setup: carla's `RoomAssignment.end_date` = yesterday. `POST /api/requests` as carla (valid payload) → **403**, `{"error":"no_current_assignment"}`. Side effect: no row created. `GET /api/requests/{carla's past tracking number}` as carla → **200** (read access preserved). | **Inside**: `end_date` = today (not yet past) → submission accepted. **Outside**: `end_date` = yesterday → rejected. | alice (current assignment) submitting the identical payload → accepted (AC-001). |
| AC-042 | NFR-07 | Setup: `Photograph.uploaded_at=T0`; `retentionPeriod=365d`. | **Inside**: `purge_expired(now=T0+364d23h59m59s)` → 0 purged. **Outside/due**: `purge_expired(now=T0+365d00m00s)` → 1 purged; `GET /api/photos/{id}` afterward → **404**. | A second photo uploaded at `T0+1day` (not yet 365 days old at the same `now`) remains visible — purge targets by age, not wholesale deletion. |
| AC-043 | NFR-10 | `GET /api/requests/CF-2026-00010` with no authenticated identity → **401**, `{"error":"authentication_required"}`. | N/A. | Same call **with** a valid authenticated owner identity → 200 (cross-referenced to AC-010's control). |
| AC-044 | FR-009, NFR-12 | Deferred to a UI-level responsive-layout check at 375px width once templates exist; not exercised by a REST contract call. | N/A. | N/A. |
| AC-045 | FR-005, FR-007 | Setup: WO-1193 Completed, linked to CF-2026-00120 (alice)/00121 (bob)/00122 (carla), all `COMPLETED`. `POST /api/requests/CF-2026-00120/reopen` as alice → **200**. Side effects: only CF-2026-00120 becomes `REOPENED`; 00121/00122 stay `COMPLETED`; the `Notification` rows created by this call target only alice (0 for bob/carla). | N/A. | N/A. |
| AC-046 | NFR-15, FR-006, FR-007 | Setup: CF-2026-00130 Submitted, `version=1`. Call A: `POST /api/triage/CF-2026-00130/confirm` as dana `{..., expected_version:1}` → **200** (wins). Call B (second supervisor, same stale `expected_version:1`, issued after A commits): same route → **409**, `{"error":"concurrent_update"}`. Side effects: exactly 1 `WorkOrder` exists for the request; exactly 1 acknowledgment `Notification` sent. | N/A. | Call B retried with the now-current `expected_version:2` → succeeds normally — the 409 was about staleness, not a permanent block. |
| AC-047 | NFR-16, FR-002 | Setup: UNO email simulated unavailable; WO-1194 In Progress, linked to two requests. `POST /api/work-orders/WO-1194/complete` as eli (valid fields) → **201** despite the outage. Side effects: both requests `COMPLETED`; 2 `Notification` rows, `status="PENDING"`, each visible in the owner's feed immediately. Later, `send_pending(now=later)` once email recovers → both become `SENT`; a second `send_pending` call does not re-send either row. | N/A. | N/A. |
| AC-048 | NFR-17, FR-004 | Setup: Dodge, no `repairOrderNotice`; `notice_given_at` = 2026-10-31 09:00 CDT (14:00 UTC). | **Inside**: `visit_window_start` = 2026-11-01 08:00 CST (14:00 UTC) → elapsed = exactly 24h00m00s UTC → **200**, `SCHEDULED`. **Outside**: `visit_window_start` = 2026-11-01 07:59 CST (13:59 UTC) → elapsed = 23h59m00s → rejected. | The Inside case is the Control: identical payload, one minute later. |

## 2. Extra cases (gap checklist)

Added because the acceptance criteria above don't exercise this category
of behavior for the named requirement.

| ID | Category | Requirement | Case |
|---|---|---|---|
| E1 | Boundary | FR-001 | `POST /api/photos` with a file of exactly `maxPhotoBytes` (5,000,000 bytes) → accepted. A file of `maxPhotoBytes + 1` byte → rejected with `ValueError`/422. Control: a 1-byte file is accepted (isolates the byte-count rule). |
| E2 | Boundary | FR-001, FR-017 | Linking the 6th photo (= `maxPhotosPerRequest`) to a request → accepted. Linking a 7th → rejected. Control: linking the 5th (one under the limit) is accepted. |
| E3 | State | Status lifecycle, NFR-15 | Attempting `maintenance.transition(record=<Submitted request>, transition_id="T11", to_status="COMPLETED", ...)` — a transition not in the T1-T15 table for that starting state — raises `ValueError`; no history/audit row is written. Control: the same request via its real transition (T2, to "ACKNOWLEDGED") succeeds. |
| E4 | Concurrency | FR-008, NFR-15 | Two supervisors call `assign_and_schedule` on the same work order with the same stale `expected_version` (mirrors AC-046 but for dispatch instead of triage) — the second call gets `ConcurrencyError`/409; exactly one technician/window combination is committed. |
| E5 | Input types | FR-010, FR-011 | `labor_hours="-1"` or `labor_hours="not-a-number"` on `complete_work_order` → rejected, `WorkOrder` status unchanged. `place_on_hold(reason="WAITING_FOR_PART", part_name="")` → rejected per the contract's documented failure. Control: `labor_hours="0.25"` (valid) is accepted. |
| E6 | Input types | FR-006 | `confirm_triage(..., priority="CRITICAL")` (not one of Emergency/High/Normal/Low) → rejected, 422. Control: `priority="EMERGENCY"` is accepted. |
| E7 | Errors & precedence | FR-001, FR-010 | A submission missing **both** `exact_location` and `description` lists **both** field names in `missing_fields`, not just the first one found (extends AC-012's single-field case to the multi-field case). Same check for `complete_work_order` missing both `diagnosis` and `tested_confirmed` (extends AC-017). |
| E8 | Identity | FR-006 | `confirm_triage` called by a Person holding only a `TECHNICIAN` role (no `SUPERVISOR` role for that campus) → `PermissionError`/403. Control: the same call by dana (a supervisor) succeeds (AC-002). |
| E9 | Listing | FR-015, NFR-01 | `list_escalations` called by a Dodge supervisor returns only Dodge escalations, never Scott's, even when both campuses have overdue items at the same time. |
| E10 | What is returned | FR-003 | `get_request_detail` for the **owner** never includes a staff note that has not been marked resident-visible, even though the same note is visible to dana via the triage/staff view. Control: a note explicitly marked resident-visible **does** appear in the owner's view. |
| E11 | Non-goal boundary | FR-007, Non-goal 7 | `merge_duplicates` on two requests that are each already linked to their own **dispatched** (Scheduled or later) work order → rejected distinctly from AC-024's different-building rejection; both work orders remain independent. This is the "two already-dispatched work orders cannot be merged with this operation" rule, which AC-008/023/024 do not exercise. |
| E12 | State | FR-005 | `reopen_request` on a `Closed` request (e.g. CF-2026-00010 after AC-031) → `ValueError`/422; request stays `Closed`. Control: the identical call on a `Completed` request succeeds (AC-007). |
| E13 | Identity | FR-017 | `add_information` on a request owned by a **different** resident → `PermissionError`/403; and on the caller's **own** `Closed` request → `ValueError`/422 (two distinct one-field-wrong rejections). Control: AC-028 (own, active request) succeeds. |
| E14 | Boundary / input types | FR-004 | `set_preference(preference="PREFERRED_TIME_SLOTS", time_slots=[])` → rejected ("at least one slot" rule). Control: the same call with exactly one slot is accepted. |

## 3. Spec gaps

Per the task rules, these are listed, not resolved.

- **FR-002's notification-trigger list is broader than its acceptance
  criteria exercise.** FR-002 enumerates nine trigger events (submitted,
  acknowledged, scheduled, visit cancelled/changed, held, resumed,
  no-access, completed, closed). Acknowledged (AC-013), scheduled
  (AC-003), held (AC-005), and completed (AC-004/AC-047) each have an AC
  that explicitly asserts a notification was sent. **Submitted** (AC-001),
  **no-access** (AC-035), **resumed** (AC-021/AC-022), **closed**
  (AC-031/AC-032), and **visit changed by reassignment** (AC-016, which
  tests the transfer-to-unassigned path but not FR-008's "old/new
  technicians notified" clause for a straightforward reassignment while
  still Scheduled) have no AC that checks a notification was actually
  produced for that specific event.
- **FR-007 / Non-goal 7's "two dispatched work orders cannot be merged"
  rule has no acceptance criterion.** AC-008, AC-023, and AC-024 test
  merging/linking Submitted requests and rejecting a cross-building
  merge, but none tests the distinct Non-goal-7 rejection (two
  already-dispatched work orders). This plan adds coverage as extra case
  E11, but the spec itself never wrote an AC for it.
- **FR-004's "Preferred time slots" and "Allow entry while away"
  preferences are never exercised by name.** AC-006, AC-014, AC-020,
  AC-034, AC-035, and AC-048 all operate on `Present` (or don't specify a
  preference at all). No AC chooses `Allow entry while away` or
  `Preferred time slots`, and no AC directly tests the "at least one
  slot" requirement text in FR-004 (added here as extra case E14).
- **FR-009's content requirements aren't checked, only its filtering.**
  AC-033 verifies a technician sees *only* their own work orders, but no
  AC asserts that an assignment's detail actually contains "location,
  priority, entry permission and notice, description, and past repair
  history" as FR-009 requires.
- **Configuration values the spec deliberately leaves unset** (per
  architecture.md Spec issue 8: `urgentResponseLimit`, `holdLimit`,
  `retentionPeriod`, `maxPhotoBytes`, `maxPhotosPerRequest`,
  `emergencyContacts`) mean every AC and extra case above that depends on
  one of these (AC-009, AC-025/026, AC-027, AC-032, AC-041/042, E1, E2)
  can only be computed against this plan's fixture values (section "Test
  fixtures assumed by this plan"), not a spec-given number. A real
  per-campus value could change which side of a boundary a given test
  input lands on.
- **No requirement (FR-001..FR-020, NFR-01..NFR-17) is entirely without
  an acceptance criterion**, and no acceptance criterion cites a
  requirement number that doesn't exist in spec.md — checked against the
  "Tested by" column of the NFR table and the requirement ids in every
  AC-xxx heading.
