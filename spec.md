# Description

CampusFix is a mobile-friendly web application for handling maintenance requests in University of Nebraska Omaha residence halls. Right now, students at the Dodge and Scott campuses use different forms, portals, and phone contacts to report problems. CampusFix would give residents one place to submit requests, check progress, choose when staff may enter their rooms, and report problems that come back after a repair. Facilities supervisors would review requests, decide the category and priority, combine duplicate reports, and assign technicians. Technicians would use the system to see their jobs and record the repairs they make. Housing administrators would use the records to review workload, response times, and equipment with repeated problems. The system may suggest categories, priorities, and possible duplicates, but supervisors make the final decisions. CampusFix does not replace emergency phone reporting or the university's systems for budgeting, procurement, staff scheduling, billing, and building access.

# Goals

1. **G1 — Make maintenance reporting easier for residents.** Residents should be able to submit a problem, track its progress, and manage room-entry preferences without repeatedly contacting the housing office.
2. **G2 — Help supervisors send work to the right people.** Requests should be reviewed consistently, assigned to the right trade, and combined when several residents report the same problem.
3. **G3 — Help technicians finish and document repairs.** Technicians need clear assignment details and a reliable record of completed or blocked work.
4. **G4 — Give housing administrators useful maintenance data.** Reports should show workload, response times, and equipment that may need replacement.
5. **G5 — Keep the process dependable and accountable.** The system should send useful updates, flag delays, and record important decisions, including any changes to automated suggestions.

# Domain Model

## Actors

| Actor | Role in CampusFix |
|---|---|
| Resident | Reports maintenance problems, tracks their own requests, adds updates, and sets room-entry preferences. |
| Facilities Supervisor | Reviews and prioritizes requests, handles duplicates, and assigns or reassigns work. |
| Maintenance Technician | Views assigned work orders and records repairs, holds, access problems, and transfers. |
| Housing Administrator | Reviews maintenance activity, workload, and equipment repair history. |
| Front-desk staff / RA | Records phone-reported problems for residents using limited staff access. |
| CampusFix System | Creates tracking numbers, suggests classifications, sends notifications, flags delays, and records activity. |

External systems used by CampusFix include university single sign-on (SSO), housing assignment data, and UNO email. Freshdesk, the Scott Campus portal, Smartsheet, Maxient, MavLINK, and MavCARD are not replaced or implemented by this project.

## Objects

- **Person** — identified by university SSO identity and UNO email; Project 1 subclasses are Resident, FacilitiesSupervisor, MaintenanceTechnician, and HousingAdministrator. FrontDeskStaff is an additional restricted staff role introduced for the Project 1 phone-intake requirement.
- **Location / Building / Room** — `Location` is the parent class of `Building` and `Room` in the Project 1 ontology. A building belongs to one campus (Dodge or Scott); a room belongs to one building and floor. Official resident assignments come from housing data.
- **MaintenanceRequest** — one resident's report of one problem. It has these fields:
  - `trackingNumber`: unique, format `CF-<year>-<5-digit sequence>`, e.g., CF-2026-00482.
  - `owner` (Resident) and `recordedBy` (staff user, only under FR-019).
  - `building` and `room`, both from housing data.
  - `areaType` (`Private bedroom` | `Shared suite` | `Common area`), `exactLocation`, `description`, and `onset` (optional).
  - `residentUrgency` (`Low` | `Normal` | `Urgent`).
  - `photos` (0..n), `entryPermission`, `notes`, `status`, and `statusHistory`.
  - Linked work orders.
- **WorkOrder** — actionable job created from one or more acknowledged requests. It has these fields:
  - `workOrderNumber`: unique, e.g., WO-1187.
  - Linked requests (1..n).
  - `category`, `priority`, assigned technician (0..1), and `visitWindow`.
  - `status`, hold records, visit records, and work records.
  - `equipment` (optional).
  - `priorWorkOrder`, set when the work order was created from a reopened request.
- **WorkRecord** — diagnosis, work performed, labor time (hours, decimal), parts used, before/after photos, repair-tested confirmation, completion time.
- **Photograph** — optional repair image linked to a request or work record and subject to privacy controls.
- **Status** — enumerated lifecycle state stored on requests and work orders as specified below.
- **CampusFixSystem** — original OWL class representing the software actor that sends notifications and maintains maintenance records.
- **Part** — part name and quantity used.
- **HoldRecord** — a Project 2 refinement of Project 1's `holdReason`. Fields: reason (`Waiting for part` | `Waiting for approval` | `Other`), part name when waiting for a part, next action, start time, cleared time, and cleared by.
- **EntryPermission** — preference (`Present` | `Allow entry while away` | `Preferred time slots`), time slots, preference history, notices (sent time, visit window, cancelled), and visit records. Each visit record holds the person entering, entry time, whether the resident was present, knock-and-announce confirmation, and outcome.
- **MaintenanceCategory** — plumbing, electrical, HVAC, carpentry, locks/glass, appliance, other.
- **Priority** — supervisor-confirmed: `Emergency` | `High` | `Normal` | `Low`. Separate from `residentUrgency`.
- **Suggestion** — a Project 2 refinement for system-suggested category, priority, and duplicate candidates, plus the supervisor's final decision, reviewer, and decision time.
- **Equipment** — fixture, appliance, or building system at a location; linked to its work orders.
- **Notification** — recipient, event, tracking number, status, content, channel, sent time.
- **AuditEntry** — a Project 2 refinement capturing user, time, action (view or change), record, and changed fields.

### Status lifecycle

Requests have an independent `requestState` (`Submitted`, `Acknowledged`, `Reopened`, `Completed`, `Closed`). Work orders have an independent `workOrderStatus` (`Acknowledged`, `Scheduled`, `In Progress`, `On Hold`, `No Access`, `Completed`). The resident-visible `displayStatus` is derived from the linked work order while it is active; it is not a second independently mutable work-order state.

- `Submitted` means received but not accepted. `Acknowledged` means accepted by a supervisor after category/priority confirmation. `Urgent` means **the resident selected `Urgent` on submission**, not a final priority. The escalation clock stops at acknowledgment.
- A work order is created in `Acknowledged`, meaning unassigned. For an accepted request linked to a work order, its displayed status follows that work order; all linked requests see the same work-order progress but only their own request details.
- When a shared work order completes, all linked requests display `Completed`; each owner can independently reopen or close their own request. Reopening one request creates a new triage case and later a new linked work order, without reopening other residents' requests or the completed shared work order.
- `Completed` is terminal for the original work order. `Closed` is terminal for a resident request; after it closes, any recurrence requires a new request.
- Only the transitions below are allowed; the system MUST reject other state changes. Escalations (FR-015) never change state.

| ID | From | To | Trigger | Req. |
|---|---|---|---|---|
| T1 | (new) | Submitted | Valid request submitted by a resident or front-desk staff | FR-001, FR-019 |
| T2 | Submitted | Acknowledged | Supervisor confirms category and priority; work order created or linked | FR-006, FR-007 |
| T3 | Submitted, Reopened | Closed (request) | Supervisor closes without active work (reason required) | FR-018 |
| T4 | Acknowledged | Scheduled | Supervisor assigns a technician and visit window | FR-008 |
| T5 | Scheduled | In Progress | Assigned technician starts work | FR-010 |
| T6 | Scheduled | No Access | Technician records an unsuccessful entry attempt | FR-011 |
| T7 | No Access | Scheduled | Supervisor sets a new visit window | FR-004, FR-008 |
| T8 | In Progress | On Hold | Technician places work on hold (reason and next action) | FR-011 |
| T9 | On Hold | In Progress | Assigned technician marks blocker cleared and selects Resume now while present on site | FR-016 |
| T10 | On Hold | Scheduled | Technician or supervisor marks blocker cleared and sets a return-visit window | FR-016 |
| T11 | In Progress | Completed | Technician completes with required documentation | FR-010 |
| T12 | Scheduled, In Progress, On Hold, No Access | Acknowledged | Technician requests transfer; work order is unassigned | FR-011 |
| T13 | Completed | Reopened | Owner reopens (request only) | FR-005 |
| T14 | Reopened | Acknowledged (request and new work order) | Supervisor re-confirms; a new work order references the previous one | FR-006 |
| T15 | Completed | Closed | Owner confirms resolution, or the confirmation period expires (request only) | FR-020 |

Self-transitions that do not change status: reassignment or a new visit window while `Scheduled` (FR-008), and entry-preference changes (FR-004).

### Configuration values

The university supplies these per campus. This specification does not set them, except where HRL policy gives a value.

| Key | Meaning | Used by |
|---|---|---|
| `urgentResponseLimit` | Longest an urgent request may stay `Submitted` before escalation | FR-015 |
| `holdLimit` | Longest a work order may stay `On Hold` before escalation | FR-015 |
| `minEntryNotice` | **At least 24 hours for routine entry**, per HRL Community Policies 2025–26. A shorter notice period is permitted once a repair order has been filed; the allowed shorter period must be provided by the university for that case (not guessed). | FR-004 |
| `repeatRepairCount`, `repeatRepairWindow` | Equipment with at least this many work orders within this window is a replacement candidate | FR-013 |
| `closureConfirmationPeriod` | Optional time after `Completed` before a request closes automatically; if unset, resident confirmation is required | FR-020 |
| `retentionPeriod` | When photographs and entry records are archived or deleted | NFR-07, NFR-14 |
| `maxPhotoBytes`, `maxPhotosPerRequest` | Photo size and count limits, unspecified in Project 1 | FR-001, FR-017 |
| `emergencyContacts` | Front desk, RA on duty, and Scott Campus 24-hour line shown to residents | FR-001, NFR-09 |

**Policy rule:** Routine entry requires at least 24 hours' notice; shorter notice is permitted once a repair order has been filed (HRL Community Policies 2025–26). Staff must knock and announce, and the actual entry/attempt must be recorded. The campus must configure a defensible shorter period where the exception applies.

# Functional Requirements

**How to read this version:** MUST is required. SHOULD is expected unless there is a documented reason not to follow it. MAY is optional.

- `FR-001`–`FR-016` correspond to Project 1 `FR-1`–`FR-16`.
- `FR-017`–`FR-020` cover behavior that Project 1's wireframes, navigation model, and statecharts show but that had no requirement.
- `NFR-01`–`NFR-14` correspond to Project 1 Appendix A.
- `[MVP]` keeps the Project 1 classification.
- Each requirement names the goal(s) it supports.

## Resident

### FR-001 [MVP] — Submit a maintenance request (G1)

1. Submission MUST require SSO sign-in and a current room assignment in housing data.
2. Building and room MUST be prefilled from housing data. The resident MUST NOT be able to change them in the form or in the submitted data.
3. Required fields MUST be area type, exact location, and description, plus entry preference unless the area type is `Common area`.
4. Urgency MUST default to `Normal`. Onset and photographs MUST be optional.
5. Photographs MUST be supported in approved image formats (JPG and PNG at minimum) and within university-configured `maxPhotoBytes` and `maxPhotosPerRequest` limits. These numerical values were not set in Project 1.
6. Before upload, the form MUST warn residents to show only the problem and to avoid people and personal belongings.
7. On valid submission, the system MUST:
   - create exactly one request in `Submitted` (T1);
   - assign a unique tracking number;
   - run FR-014;
   - send the confirmation in FR-002;
   - display the tracking number and status.
8. On invalid submission, the system MUST NOT create a request or tracking number. It MUST name each missing or invalid field and MUST keep everything already entered, including attached photographs.
9. The form MUST show `emergencyContacts` and state that it is not an emergency channel. Selecting `Urgent` MUST show the emergency instructions again.
10. The form SHOULD save drafts and retry failed photo uploads without losing the submission.

### FR-002 [MVP] — Status notifications (G1, G5)

1. The system MUST notify the request owner, by UNO email and in the in-app activity feed, when any of these events happens:
   - request submitted (confirmation);
   - acknowledged;
   - scheduled (with trade and visit window);
   - placed on hold (with reason and next action);
   - work resumed;
   - visit cancelled or changed;
   - no access recorded;
   - completed;
   - closed (with the reason when closed under FR-018).
2. Each notification MUST include the tracking number and the new status, and MUST be sent only after the change is saved.
3. When a work order is linked to several requests, each owner MUST receive a separate notification about their own tracking number. No notification may include another resident's name or room.
4. The assigned technician MUST be notified when a work order is assigned to them, reassigned away from them, or resumed after a hold.

### FR-003 [MVP] — Track own requests (G1)

1. A resident MUST see a list of their own requests, filterable by status. Each entry shows tracking number, short description, location, status, and last update.
2. Searching by tracking number MUST open a request only if the signed-in resident owns it. A number that does not exist and a number owned by someone else MUST return the same "not found" result.
3. Request details MUST show:
   - the full status history with timestamps;
   - the reason and next action for each hold;
   - resident-visible notes;
   - the current entry preference and notice status;
   - the assigned technician's first name and trade only.
4. Staff MUST mark each note as resident-visible or internal; the default MUST be internal. Internal notes MUST NOT be shown to residents.

### FR-004 [MVP] — Room-entry preference and notice (G1)

1. For a non-common area, the owner MUST choose `Present`, `Allow entry while away`, or `Preferred time slots`. `Preferred time slots` requires at least one slot.
2. The owner MAY change the preference until the request is `Completed` or `Closed`. Each change MUST be kept in history and shown at once to the supervisor and the assigned technician.
3. Whenever a visit window is set (T4, T7, T10, or a new window under FR-008), the system MUST send entry notice to the owner and record the send time. Routine visits require at least 24 hours' notice. Once a repair order has been filed, shorter notice is permitted under HRL policy, but the authorized shorter interval must be supplied by the university and recorded before a shorter-notice window can be saved.
4. If the preference changes after notice was sent, the pending notice MUST be cancelled. Entry MUST NOT occur until a new window is set and noticed.
5. When the preference is `Preferred time slots`, the visit window SHOULD fall inside a slot. A window outside every slot MUST require a supervisor reason, which is stored.
6. If the preference is `Present` and the resident is absent, the technician MUST NOT enter and MUST record `No Access` (FR-011).
7. For each entry, the technician MUST record:
   - person entering;
   - entry time;
   - whether the resident was present;
   - confirmation that staff knocked and announced;
   - outcome.

### FR-005 — Reopen an unresolved request (G1)

1. The owner MAY reopen their own request only while it is `Completed`, not after it is `Closed`.
2. Reopening MUST require a new description and MAY include photographs.
3. Reopening MUST:
   - keep the same tracking number;
   - set the request to `Reopened` (T13);
   - place it in the triage queue marked as reopened;
   - keep the earlier work order and work records visible.
4. Reopening one of several requests linked to the same work order MUST NOT change the status of the other requests.

### FR-017 — Add information to a request (G1)

1. The owner MAY add a comment, photographs, or both to their own request in any status except `Closed`. FR-001 photograph rules apply.
2. Adding information MUST NOT change status or create a new request.
3. The added information MUST appear in the request history and be visible to the supervisor and the assigned technician.
4. The assigned technician SHOULD be notified.

### FR-020 — Close a completed request (G1, G5)

1. The owner MAY confirm that a `Completed` request is resolved, which closes it (T15).
2. If the owner neither confirms nor reopens within `closureConfirmationPeriod` after completion, the system MUST close the request and record that the closure was automatic.
3. If `closureConfirmationPeriod` is not configured, the request MUST stay `Completed` until the owner confirms.

## Facilities Supervisor

### FR-006 [MVP] — Triage (G2)

1. The triage queue MUST list `Submitted` and `Reopened` requests for the supervisor's campus. Each entry shows location, description, resident urgency, age, photographs, and any suggestions labeled "suggested".
2. The supervisor MUST set both category and priority before acknowledging.
3. Confirming MUST move the request to `Acknowledged` (T2 or T14). It MUST also create a work order in `Acknowledged`, unless the request is linked to an existing work order under FR-007.
4. The system MUST store the suggested values (if any), the final values, the reviewer, and the decision time.
5. Triage MUST work when no suggestions exist.
6. After T14, the new work order MUST reference the previous work order as `priorWorkOrder`.

### FR-007 — Merge duplicate reports (G2)

1. The supervisor MAY link a `Submitted` request to an existing work order that is not `Completed`, or merge two `Submitted` requests into a single new work order during triage. All linked requests MUST be in the same building. Two separately dispatched work orders MUST NOT be merged until a supervisor cancels any conflicting dispatch; cancellation workflow is outside this version's merge operation.
2. A linked request MUST NOT create a second active work order or visit; a new combined work order is created only when no existing work order is being reused.
3. Each linked request MUST keep its tracking number, owner, history, notes, and entry permission.
4. Linking a `Submitted` request MUST acknowledge it with the work order's category and priority, recorded as the supervisor's decision.
5. The supervisor MUST confirm or dismiss each system duplicate flag; the system stores the decision, reviewer, and time. A dismissed pair SHOULD NOT be flagged again.
6. The supervisor SHOULD be able to unlink a request linked in error. It then returns to `Acknowledged` with its own new unassigned work order, and both the link and the unlink stay in history.

### FR-008 [MVP] — Assign, schedule, and reassign (G2)

1. For an `Acknowledged` work order, the supervisor MUST select a technician and a visit window in one action. Assignment and scheduling are one atomic transaction in this version; there is one resident Scheduled notification naming the trade and visit window, not separate assigned and scheduled status changes.
2. Saving the assignment MUST:
   - set `Scheduled` (T4 or T7);
   - add the work order to the technician's list;
   - trigger entry notice (FR-004) and notifications (FR-002).
3. The technician picker MUST default to technicians whose trade matches the work order's category. Each shows open work-order count and availability.
4. Availability MUST be derived from the technician's existing CampusFix visit windows and an unavailable flag that supervisors set. Staff shift scheduling stays out of scope.
5. Choosing a technician whose trade does not match the category SHOULD require explicit confirmation.
6. The supervisor MAY reassign a `Scheduled` work order to another technician or window. Reassignment MUST:
   - keep the earlier assignment in history;
   - notify both technicians;
   - cancel the old notice and send a new one if the window changes.

### FR-018 — Close a request without a work order (G2)

1. The supervisor MAY close a `Submitted` or `Reopened` request without creating a work order (T3), for example when it is not a maintenance problem. A reason is required and is shown to the owner.
2. `Closed` is final. The owner MUST NOT be able to reopen it and must submit a new request instead.

## Maintenance Technician

### FR-009 [MVP] — View assigned work (G3)

1. A technician MUST see only work orders assigned to them, grouped as Today, Upcoming, On Hold, and Completed, and sorted by priority.
2. Each work order MUST show:
   - location and area type;
   - priority and description;
   - the resident's photographs;
   - the current entry preference, visit window, and notice status;
   - repair history for the same room or equipment, including any `priorWorkOrder`.
3. A work order whose notice is unsent or cancelled MUST show a warning.
4. These screens MUST be usable on a phone.

### FR-010 [MVP] — Record and complete work (G3)

1. Only the assigned technician MAY start (T5) or complete (T11) a work order.
2. In a private bedroom or shared suite, starting work MUST follow a recorded entry for the current visit (FR-004).
3. The technician MUST be able to record diagnosis, work performed, labor time, parts (name and quantity), and before/after photographs.
4. Completion MUST require a diagnosis, a description of work performed, and confirmation that the repair was tested. Labor time and parts SHOULD be recorded; photographs are optional.
5. If a required item is missing, the status MUST stay `In Progress` and the system MUST name the missing items.
6. Completion MUST save the work record, set the work order and every linked request to `Completed`, and notify every owner.

### FR-011 — Hold, no access, and transfer (G3)

1. **Hold (T8):** only from `In Progress`. Requires a reason and a next action. The reason `Waiting for part` also requires the part name.
2. **No access (T6):** only from `Scheduled`. Records the attempt time, the person attempting entry, and the reason. It MUST NOT set `Completed`.
3. **Transfer (T12):** requires a proposed trade and a reason. The work order returns to `Acknowledged` and is unassigned. It appears in the supervisor's queue marked as a transfer. Any pending visit window and notice are cancelled, and the owner(s) are notified that the visit was cancelled.
4. None of these actions MAY close a request or delete any record.

### FR-016 — Resume held work (G3, G5)

1. The assigned technician or a supervisor MUST be able to mark a hold's blocking condition as cleared (e.g., part received, approval granted).
2. Upon an authorized user recording that the blocking condition is cleared, the system MUST automatically transition according to the selected option (the user does not manually edit the resulting status):
   - **Resume now:** assigned technician only, confirmed present on site with required entry record; the work order returns to `In Progress` (T9).
   - **Schedule return visit:** a visit window is required; the work order becomes `Scheduled` (T10), with entry notice under FR-004.
3. The system MUST close the hold record with cleared time and user, keep it in history, and notify the technician and the owner(s) that work has resumed.
4. Escalation timing for that hold MUST stop.

## Housing Administrator

### FR-012 — Operational reports (G4)

1. The administrator MUST see:
   - open work-order count, where open means not `Completed`;
   - completed work-order count;
   - open work orders per technician;
   - average time to acknowledge (first `Acknowledged` time minus `Submitted` time);
   - average time to complete (first `Completed` time minus `Submitted` time), by category and building.
2. Filters for period (by submission date), building, and category MUST apply to every figure.
3. Reports MUST NOT show resident names, photographs, or entry records.
4. The filtered report SHOULD be exportable as CSV.

### FR-013 — Replacement candidates (G4)

1. A supervisor or technician MUST be able to link a work order to an equipment item at its location.
2. The system MUST flag equipment with at least `repeatRepairCount` work orders within `repeatRepairWindow`. Work orders created from reopened requests count.
3. Each candidate MUST show equipment, location, work-order count, and last repair date. Selecting a candidate MUST show its work-order history.
4. If either threshold is not configured, nothing is flagged and the screen MUST say the rule is not configured.

## CampusFix System

### FR-014 — Suggestions and duplicate flags (G2, G5)

1. On submission, the system SHOULD suggest a category and priority from the description, and from photographs when present.
2. It SHOULD flag as possible duplicates any open requests (not `Completed` or `Closed`) in the same room, on the same floor of the same building, or for the same equipment.
3. Suggestions MAY be disabled. If suggestions are disabled or fail, the request MUST still be created and triaged manually.
4. Suggestions MUST be labeled as suggestions. They MUST NOT set final values, merge requests, or change status.
5. The system MUST record each suggestion together with the final decision, the reviewer, and the time (FR-006).

### FR-015 — Escalate delays (G5)

1. **Urgent requests:** the system MUST alert supervisors of the request's campus when a request whose `residentUrgency` is `Urgent` stays `Submitted` longer than `urgentResponseLimit`. The urgent escalation rule does not depend on optional automated suggestions; acknowledgment stops the clock.
2. **Holds:** the system MUST alert the same supervisors when a work order has stayed `On Hold` longer than `holdLimit`.
3. Each condition MUST alert once per occurrence: once per `Submitted` period and once per hold. Each alert MUST be recorded in the request history with its time.
4. Escalation MUST NOT change status, priority, or assignment.
5. Active escalations MUST stay in the triage-queue alert banner until the condition ends.

## Staff intake

### FR-019 — Record a phone-reported problem (G1, G5)

1. Front-desk staff or an RA MUST be able to submit a request on behalf of a resident identified by university identity. FR-001 fields and validation apply. Phone intake documents an already-reported issue; emergency dispatch remains outside CampusFix.
2. Building and room MUST come from that resident's housing data. The owner is the resident; `recordedBy` is the staff user.
3. The owner MUST receive the FR-002 confirmation and then has the same rights as for a request they submitted themselves.
4. The staff role MUST be limited to creating requests and viewing the requests it recorded.

## Quality and policy constraints

| ID | Constraint | Tested by |
|---|---|---|
| NFR-01 | Room details, photographs, and entry records MUST be visible only to the owner, the campus's supervisors, and the assigned technician; administrators see aggregates only (FR-012). | AC-N01.1 |
| NFR-02 | The system MUST log every view and change of a request or work order (user, time, action, changed fields), including suggestion overrides. | AC-N02.1, AC-006.3 |
| NFR-03 | Automated results are recommendations only (FR-014). | AC-014.4 |
| NFR-04 | Every request can be submitted without photographs (FR-001). | AC-001.4 |
| NFR-05 | All screens MUST meet WCAG 2.1 Level AA and support keyboard-only use and screen readers. | AC-N05.1 |
| NFR-06 | Photo privacy warning before upload (FR-001). | AC-001.6 |
| NFR-07 | Photographs and entry records MUST be archived or deleted after `retentionPeriod`. | AC-N07.1 |
| NFR-08 | Entry notice and knock-and-announce records (FR-004). | AC-004.2 – AC-004.5 |
| NFR-09 | `emergencyContacts` MUST be visible on every resident request screen (dashboard, submit form, request details). Staff can record phone reports (FR-019). | AC-N09.1, AC-019.1 |
| NFR-10 | Users MUST authenticate through university SSO. UNO email is the formal notification channel. | AC-N10.1 |
| NFR-11 | Drafts are saved and failed photo uploads are retried (FR-001). | AC-N11.1 |
| NFR-12 | Resident and technician screens MUST be usable on a phone. | AC-009.4 |
| NFR-13 | Notice, escalation, approval, and vendor rules MUST be configurable separately for the Dodge and Scott campuses. | AC-N13.1 |
| NFR-14 | A user without a current room assignment MUST NOT submit new requests but MUST keep read access to their own past requests until `retentionPeriod`. | AC-N14.1 |

# Acceptance Criteria

Each criterion refines one requirement into a check that passes or fails. `AC-<nnn>.<k>` tests `FR-<nnn>`; `AC-N<nn>.<k>` tests `NFR-<nn>`. Statuses and transitions refer to the Status lifecycle table.

## FR-001 — Submit a maintenance request

- **AC-001.1** A signed-in resident with a room assignment submits area type, exact location, description, and entry preference. The system creates exactly one request in `Submitted` with a new unique tracking number, and the confirmation shows that number and status.
- **AC-001.2** Building and room are prefilled and locked. A submission whose data carries a different building or room is rejected.
- **AC-001.3** Omitting exact location, description, area type, or (for a non-common area) entry preference creates no request and no tracking number. Each missing field is named, and the entered values and attached photographs remain.
- **AC-001.4** A request with all required fields and no photographs is accepted.
- **AC-001.5** A photograph outside approved formats, greater than configured `maxPhotoBytes`, or exceeding `maxPhotosPerRequest` is rejected with a message; the rest of the form is kept.
- **AC-001.6** The privacy warning is visible before any photograph is uploaded.
- **AC-001.7** Emergency instructions are visible on the form and appear again when `Urgent` is selected.
- **AC-001.8** Urgency is `Normal` unless the resident changes it.
- **AC-001.9** Two submissions with identical content create two requests with different tracking numbers. Duplicates are handled by FR-014 and FR-007, not rejected at submission.

## FR-002 — Status notifications

- **AC-002.1** Each listed event produces exactly one email to the owner's UNO address and one activity-feed entry, each with the tracking number and new status.
- **AC-002.2** No notification is sent when the status change fails to save.
- **AC-002.3** The `Scheduled` notification includes trade and visit window. The `On Hold` notification includes reason and next action.
- **AC-002.4** Completing a work order linked to three requests sends three notifications. Each carries its own owner's tracking number and no other resident's name or room.
- **AC-002.5** The technician is notified on assignment, on reassignment away, and when held work resumes.

## FR-003 — Track own requests

- **AC-003.1** A resident's request list contains only requests they own.
- **AC-003.2** Searching their own tracking number opens the details with full timestamped status history.
- **AC-003.3** Searching a nonexistent number and searching another resident's number return identical "not found" responses.
- **AC-003.4** Internal notes never appear in the resident view. Notes marked resident-visible do.
- **AC-003.5** The assigned party shows only the technician's first name and trade.

## FR-004 — Room-entry preference and notice

- **AC-004.1** `Preferred time slots` with no slot is rejected.
- **AC-004.2** For routine entry without the repair-order exception, a visit window starting 23 hours after notice is rejected and one starting 24 hours after notice is accepted. Once a repair order is filed, a shorter visit window is allowed only when the campus has configured an authorized shorter interval; the notice and exception are recorded.
- **AC-004.3** Changing the preference after notice was sent cancels that notice and keeps both preferences in history. The technician view shows the notice warning until a new window is noticed.
- **AC-004.4** With preference `Present` and the resident absent, the technician cannot record an entry; only `No Access` can be recorded.
- **AC-004.5** Recording an entry is rejected unless person entering, entry time, present/absent, knock-and-announce confirmation, and outcome are all given.
- **AC-004.6** Scheduling outside every preferred slot is rejected without a supervisor reason and accepted with one, which is stored.
- **AC-004.7** The preference cannot be changed once the request is `Completed` or `Closed`.

## FR-005 — Reopen an unresolved request

- **AC-005.1** Reopen is offered only to the owner and only while the request is `Completed`.
- **AC-005.2** Reopening without a new description is rejected.
- **AC-005.3** A reopened request keeps its tracking number, becomes `Reopened`, and appears in the triage queue marked as reopened. The earlier work order and work record remain visible.
- **AC-005.4** Reopening one of three linked requests leaves the other two in their current status.

## FR-006 — Triage

- **AC-006.1** A supervisor's queue shows only `Submitted` and `Reopened` requests for their campus.
- **AC-006.2** Acknowledging without both category and priority is rejected.
- **AC-006.3** Overriding a suggested priority stores the suggestion, the final value, the reviewer, and the time. Later processing uses the final value.
- **AC-006.4** With suggestions disabled, a supervisor sets category and priority manually. The request becomes `Acknowledged` and a work order exists in `Acknowledged`.
- **AC-006.5** Acknowledging a reopened request creates a new work order whose `priorWorkOrder` is the earlier work order.

## FR-007 — Merge duplicate reports

- **AC-007.1** Merging two Submitted requests creates one work order linked to both; both tracking numbers, owners, and histories are unchanged.
- **AC-007.2** Linking a new request to an already `Scheduled` work order creates no new assignment or visit.
- **AC-007.3** Linking a `Submitted` request records the work order's category and priority as the supervisor's decision for that request.
- **AC-007.4** Merging requests from different buildings or merging two independently dispatched work orders is rejected.
- **AC-007.5** A dismissed duplicate flag is recorded with reviewer and time, and that pair is not flagged again.
- **AC-007.6** Unlinking a request returns it to `Acknowledged` with its own work order. Both the link and the unlink appear in history.

## FR-008 — Assign, schedule, and reassign

- **AC-008.1** Saving an assignment without a technician or without a visit window is rejected.
- **AC-008.2** A valid assignment sets `Scheduled`, shows the work order in the technician's list, and triggers the entry notice and notifications.
- **AC-008.3** By default, the picker lists only technicians whose trade matches the category, each with open work-order count and availability.
- **AC-008.4** Choosing a technician of another trade requires explicit confirmation.
- **AC-008.5** Reassigning keeps the earlier assignment in history, removes the work order from the old technician's list, and notifies both technicians. A changed window cancels the old notice and sends a new one.

## FR-009 — View assigned work

- **AC-009.1** A technician sees only work orders assigned to them. Opening another technician's work order by number is refused.
- **AC-009.2** Each work order shows every field listed in FR-009, including repair history for the same room or equipment.
- **AC-009.3** A work order with an unsent or cancelled notice shows a warning.
- **AC-009.4** On a phone-width screen, work-order cards stack in one column and every action is reachable without horizontal scrolling.

## FR-010 — Record and complete work

- **AC-010.1** A user other than the assigned technician cannot start or complete the work order.
- **AC-010.2** Starting work in a private bedroom or shared suite is rejected until an entry is recorded for the current visit.
- **AC-010.3** Completing without diagnosis, work performed, or tested confirmation is rejected. The status stays `In Progress`, and the missing items are named.
- **AC-010.4** With all three present, completion saves the work record, sets the work order and every linked request to `Completed`, and notifies each owner.
- **AC-010.5** Completion succeeds without photographs, labor time, or parts, and shows a reminder when labor time or parts are missing.
- **AC-010.6** Completing a work order that is not `In Progress` is rejected.

## FR-011 — Hold, no access, and transfer

- **AC-011.1** A hold without reason or next action is rejected. `Waiting for part` without a part name is rejected.
- **AC-011.2** A valid hold sets `On Hold`, records reason, next action, and start time, and notifies the owner(s).
- **AC-011.3** A hold from any status other than `In Progress` is rejected. A no-access record from any status other than `Scheduled` is rejected.
- **AC-011.4** A no-access record stores attempt time, person, and reason, and sets `No Access`, never `Completed`.
- **AC-011.5** A transfer without proposed trade or reason is rejected.
- **AC-011.6** A valid transfer:
  - sets the work order to `Acknowledged` and unassigns it;
  - cancels the pending window and notice;
  - shows the work order in the supervisor's queue marked as a transfer;
  - notifies the owner(s) that the visit was cancelled;
  - keeps all earlier work records.

## FR-012 — Operational reports

- **AC-012.1** For a fixed test dataset, the displayed averages equal those computed from status timestamps as defined in FR-012.
- **AC-012.2** Changing period, building, or category changes every figure on the page.
- **AC-012.3** No report contains resident names, photographs, or entry records.
- **AC-012.4** Residents and technicians cannot open reports.

## FR-013 — Replacement candidates

- **AC-013.1** With test values `repeatRepairCount` = 3 and `repeatRepairWindow` = 90 days, equipment with 3 work orders in 90 days is listed and equipment with 2 is not.
- **AC-013.2** Each candidate shows equipment, location, work-order count, and last repair date. Selecting it shows its work-order history.
- **AC-013.3** With either threshold unset, nothing is flagged and the screen states the rule is not configured.

## FR-014 — Suggestions and duplicate flags

- **AC-014.1** With suggestions enabled, a new request shows a category and priority labeled "suggested". Its final category and priority stay empty until a supervisor confirms them.
- **AC-014.2** An open request in the same room, on the same floor of the same building, or for the same equipment is flagged as a possible duplicate. `Completed` and `Closed` requests are not.
- **AC-014.3** If the suggestion service fails, the request is still created in `Submitted` and appears in triage without suggestions.
- **AC-014.4** No suggestion or flag sets a final value, merges requests, or changes status.

## FR-015 — Escalate delays

- **AC-015.1** An urgent request still `Submitted` after `urgentResponseLimit` produces exactly one alert and one history entry.
- **AC-015.2** A request with resident urgency `Normal` and only a suggested priority of `Emergency` does not meet this pre-acknowledgment urgent-rule trigger; the suggestion is prominently visible for prompt human review.
- **AC-015.3** A request acknowledged before `urgentResponseLimit` produces no alert.
- **AC-015.4** A work order `On Hold` longer than `holdLimit` produces exactly one alert for that hold. Status, priority, and assignment are unchanged.
- **AC-015.5** An escalation stays in the triage alert banner until the condition ends, then disappears.

## FR-016 — Resume held work

- **AC-016.1** When the assigned technician records the blocker cleared and chooses Resume now while on site with the required entry recorded:
  - the work order becomes `In Progress`;
  - the hold record is closed with time and user, and stays in history;
  - the technician and owner(s) are notified.
- **AC-016.2** Recording the blocker cleared with Schedule return visit but no window is rejected. With a valid window and applicable notice rule, the work order automatically becomes `Scheduled` and notice is sent.
- **AC-016.3** Users other than the assigned technician and supervisors cannot clear a hold. Only the assigned technician can choose Resume now.
- **AC-016.4** After a hold is cleared, no hold escalation is raised for it.

## FR-017 — Add information to a request

- **AC-017.1** An owner adds a comment to a `Scheduled` request. The status is unchanged, no new tracking number is created, and the comment appears in history for the supervisor and the assigned technician.
- **AC-017.2** Adding information to a `Closed` request, or to another resident's request, is rejected.

## FR-018 — Close a request without a work order

- **AC-018.1** Closing a `Submitted` request without a reason is rejected.
- **AC-018.2** With a reason, the request becomes `Closed`, no work order is created, and the owner is notified with the reason.
- **AC-018.3** A request already linked to a `Scheduled` or later work order cannot be closed this way.
- **AC-018.4** A request closed this way cannot be reopened.

## FR-019 — Record a phone-reported problem

- **AC-019.1** A staff-recorded request has the resident as owner, the staff user as `recordedBy`, and building and room from the resident's housing data. The resident receives the confirmation.
- **AC-019.2** Missing required fields are handled exactly as in AC-001.3.
- **AC-019.3** The staff user can view the requests they recorded and no others.
- **AC-019.4** A person without a current room assignment cannot be selected as the owner.

## FR-020 — Close a completed request

- **AC-020.1** The owner confirms resolution of a `Completed` request. It becomes `Closed`, and reopening is no longer offered.
- **AC-020.2** A `Completed` request with no owner action for `closureConfirmationPeriod` closes automatically, and history records the closure as automatic.
- **AC-020.3** With `closureConfirmationPeriod` unset, the request stays `Completed` until the owner confirms.
- **AC-020.4** Confirming resolution of a request that is not `Completed` is rejected.

## Quality and policy constraints

- **AC-N01.1** A technician cannot open the photographs or entry records of a work order not assigned to them. A resident cannot open another resident's photograph by direct link.
- **AC-N02.1** Opening a request and overriding a suggestion each create an audit entry with user, time, and action.
- **AC-N05.1** An accessibility review finds no WCAG 2.1 AA failures, and every action can be completed with the keyboard alone.
- **AC-N07.1** After `retentionPeriod`, photographs and entry records are archived or deleted and no longer visible to any role.
- **AC-N09.1** Emergency instructions are visible on the resident dashboard, the submit form, and request details.
- **AC-N10.1** Opening any screen while signed out redirects to university SSO. Formal notifications go to UNO email.
- **AC-N11.1** Leaving the form mid-entry and returning restores the saved draft. A failed photo upload is retried without losing typed fields.
- **AC-N13.1** Changing `holdLimit` for the Dodge campus does not change it for the Scott campus.
- **AC-N14.1** After a resident's room assignment ends, they cannot submit a new request but can still view their past requests until their configured retention period ends.

<!-- Project 2 design decisions for team review: Resident Urgent triggers pre-ack escalation; assignment+visit-window are atomic; transfers return unassigned to Acknowledged; authorized staff clear holds; the system then performs the status transition; No Access is rescheduled by supervisor rather than handled as hold; closure is owner-confirmed or automatic after an optional campus-configured period. Photo limits, any shorter-than-24-hour permitted notice, and closure period require university confirmation. -->
