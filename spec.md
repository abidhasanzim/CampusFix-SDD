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

Requirements FR-001 through FR-016 are based on Project 1. FR-017 through FR-020 cover actions shown in the Project 1 wireframes and diagrams but not written as separate requirements. Each requirement identifies the goal it supports. `[MVP]` marks the features planned for the first release.

## Resident

- **FR-001 [MVP] — Submit request (G1).** As a resident, I want to submit a maintenance request with my official building and room, area type, exact location, description, urgency, entry preference (unless common area), and optional photographs, so that my problem is recorded. The building/room are read-only from housing data; area type, exact location, and description are required; urgency defaults to `Normal`; a valid submission creates one `Submitted` request and a unique tracking number. The request form shows emergency contacts and states it must not be used to obtain emergency dispatch. Photo upload is optional, warns against images of residents and belongings, and respects university-configured size/count limits.
- **FR-002 [MVP] — Notifications (G1, G5).** As a resident, I want status notifications after submitted, acknowledged, scheduled, held, resumed, no-access, completed, and closed events, so that I know my problem's progress. Scheduling and assignment occur in one transaction and produce **one** resident `Scheduled` message stating the assigned trade and visit window; staff receive their own assignment/reassignment messages. All messages use UNO email and an activity feed, include the resident's own tracking number, and are sent only after saving the event.
- **FR-003 [MVP] — Track request (G1).** As a resident, I want to find my requests by tracking number and see their full timestamped status history, hold reason, next action, and resident-visible notes, so that I can follow progress without calling the office. A request belonging to another resident and a nonexistent tracking number both return the same `not found` response. Staff notes are internal unless explicitly marked resident-visible.
- **FR-004 [MVP] — Room entry (G1).** As a resident, I want to choose `Present`, `Allow entry while away`, or `Preferred time slots` (with at least one slot) and receive notice before a technician enters, so that I can control access to my room. A changed preference cancels pending notice and requires a new visit window and notice. **Routine entry requires at least 24 hours' notice; shorter notice is permitted once a repair order has been filed (HRL Community Policies 2025–26).** The university must supply the applicable shorter period; the system must not guess it. Staff must knock and announce and record who entered, the time, permission, and outcome. If `Present` is chosen and the resident is absent, record `No Access` instead of entering.
- **FR-005 — Reopen (G1).** As a resident, I want to reopen my `Completed` request with a new description and optional photo when the repair did not solve the problem, so that the earlier history remains linked under my original tracking number. A `Closed` request cannot reopen. For a shared work order, reopening my request does not reopen other residents' reports or the completed work order; supervisor triage creates a new linked work order.
- **FR-017 — Add information (G1).** As a resident, I want to add a comment or photograph to my own active request without submitting a new ticket, so that staff have updated information. This does not change state or tracking number; adding to another resident's request or a `Closed` request is not allowed.
- **FR-020 — Confirm closure (G1, G5).** As a resident, I want to confirm my `Completed` request is resolved so that it can be closed. Alternatively, the system closes it after a university-configured confirmation period if one is defined; otherwise it stays `Completed` until I confirm. `Closed` is final and recorded in history.

## Facilities Supervisor

- **FR-006 [MVP] — Triage (G2).** As a facilities supervisor, I want to confirm or override category and final priority for submitted/reopened requests, so that work is triaged correctly. The queue shows resident urgency (Low/Normal/Urgent) separately from suggested/final priority (Emergency/High/Normal/Low); `Acknowledged` means the supervisor has accepted and triaged it. Category and priority are both required; manual triage works if suggestions are off or fail. Suggestions, decisions, staff identity, and time are logged. Reopened requests result in new work orders linked to their predecessors.
- **FR-007 — Merge duplicates (G2).** As a facilities supervisor, I want to combine multiple submitted reports of the same problem into one work order and link newly submitted reports to an existing active work order, so that no extra visit is dispatched and each original tracking number, owner, and history remains. Only reports from the same building can be merged. Two independent, already-dispatched work orders cannot be merged with this operation; the supervisor must resolve the duplicate dispatch separately.
- **FR-008 [MVP] — Assign and schedule (G2).** As a facilities supervisor, I want to assign or reassign a work order by trade, availability, and workload, with a visit window, so that technicians know what to do and residents receive valid entry notices. Assignment and scheduling are atomic: neither is committed without technician and visit window. A changed window cancels its old entry notice and generates a new one; reassignment is recorded and old/new technicians notified.
- **FR-018 — Reject/close before dispatch (G2).** As a facilities supervisor, I want to close an invalid `Submitted` or `Reopened` request without dispatching maintenance, with a recorded reason given to its owner, so that nonmaintenance or mistaken submissions do not remain in the queue. Only a request without active dispatched work is eligible. Closure is final.

## Maintenance Technician

- **FR-009 [MVP] — View assignments (G3).** As a maintenance technician, I want to see only my assigned work orders on my phone, including location, priority, entry permission and notice, description, and past repair history, so that I can prepare for each visit.
- **FR-010 [MVP] — Record and complete work (G3).** As an assigned maintenance technician, I want to record diagnosis, work performed, labor time, parts used, optional before/after photographs, and a repair-tested confirmation, so that repair history is reliable. To complete an `In Progress` work order, the diagnosis, work performed, and test confirmation are required; successful completion updates all requests linked to that work order and notifies their owners. For private rooms, entry must first be recorded for the visit.
- **FR-011 — Hold, failed access, transfer (G3).** As a maintenance technician, I want to place `In Progress` work `On Hold` with a reason and expected next action, record `No Access` from `Scheduled`, or request another trade, so that blocked work is not lost. A transfer requires a proposed trade and reason; it returns the work order to unassigned `Acknowledged`, cancels the old visit/notice, and sends it to the supervisor queue while preserving history. No Access is rescheduled by a supervisor; it is not a hold.
- **FR-016 — Resume a cleared hold (G3, G5).** When a supervisor or assigned technician marks a hold's documented blocker cleared, CampusFix shall automatically apply the chosen transition. The assigned technician may select `Resume now` only while present and with required entry recorded, resulting in `In Progress`. Otherwise the user sets an authorized return visit, resulting in `Scheduled` with a new entry notice. The system preserves who cleared the hold, when, its reason, and notifications. No unverified part delivery or access event silently resumes work.

## Housing Administrator

- **FR-012 — Operational reports (G4).** As a housing administrator, I want open/completed work-order counts, technician workload, and times from submission to acknowledgment and completion, filtered by period, building, and category, so that I can understand effort and responsiveness without seeing residents' private details.
- **FR-013 — Replacement candidates (G4).** As a housing administrator, I want to see equipment with repeated work orders within university-configured count and time thresholds, with its work history, so that I can identify possible replacements. If a threshold is absent, the interface must state that the rule is not configured rather than guessing.

## CampusFix System

- **FR-014 — Advisory suggestions and audit (G2, G5).** On submission, CampusFix should suggest maintenance category and priority using text and optional photos and flag possible duplicate open requests from the same room, floor/building, or equipment. Suggestions never set the final result or merge reports. The supervisor makes the final decision; the system keeps suggestions, decisions, reviewer identity, and time. If automation is off or unavailable, intake and manual triage still work.
- **FR-015 — Delayed-work escalation (G5).** CampusFix shall alert the campus supervisor when a request whose **residentUrgency is `Urgent`** remains `Submitted` longer than `urgentResponseLimit`, or when a work order stays `On Hold` longer than `holdLimit`. `Accepted` means it has become `Acknowledged`. The system records one escalation per overdue period; escalation does not alter state or priority. A suggested `Emergency` priority alone is not the trigger for this specific pre-acknowledgment urgent rule.

## Restricted Staff Intake

- **FR-019 — Phone-reported request (G1, G5).** As authorized front-desk/RA staff, I want to record a maintenance issue reported by phone on behalf of a verified resident, so that the resident receives the same tracking and updates as for self-service reports. The staff identity is saved as `recordedBy`; the resident remains the owner; location comes from housing data. Emergency dispatch itself remains outside CampusFix.

## Quality and policy requirements retained from Project 1

These are not extra functional stories. They ensure the implementer does not omit policy rules merely because the course template names only five top-level sections.

| ID | Required rule |
|---|---|
| NFR-01 | Role-based access limits student information, room details, photos, and entry logs to authorized need-to-know users. |
| NFR-02 | Log **views and changes** of request/work-order records, including overrides, with user/time/action. |
| NFR-03 | Classification/priority/duplicate suggestions are recommendations requiring supervisor confirmation. |
| NFR-04 | Photos remain optional for submission. |
| NFR-05 | Screens support keyboard-only navigation and screen readers and meet WCAG 2.1 AA. |
| NFR-06 | Warn before photo upload not to include people or unrelated belongings. |
| NFR-07 | Photos and entry records are archived/deleted after a university-configured retention period. |
| NFR-08 | **24-hour routine notice** subject to the documented filed-repair-order exception; log knock-and-announce entry and outcomes. |
| NFR-09 | Emergency contacts are shown on the dashboard, request form, and request details; emergency response is not handled through the ordinary form. |
| NFR-10 | University SSO authenticates users; UNO email is the formal notification channel. |
| NFR-11 | Save unfinished form drafts and retry failed photo uploads without losing form data. |
| NFR-12 | Resident and technician views are mobile-friendly. |
| NFR-13 | Entry/approval/vendor/escalation configuration is separate for Dodge and Scott campuses. |
| NFR-14 | After a resident's housing assignment ends, block **new** submissions while retaining eligible historical read access until retention ends. |

# Acceptance Criteria

Each scenario uses Given–When–Then steps and lists the requirements it checks. AC-001 through AC-004 come from the four scenarios written in Project 1. AC-005 through AC-011 cover scenarios referenced in the original traceability table, and the remaining scenarios test other requirements, exceptions, and policy rules.

## AC-001 — Resident submits a valid request (FR-001, FR-014)

```gherkin
Scenario: AC-001 — Resident submits a valid request
Given a resident is signed in with a current official room assignment
And the request has area type "Private bedroom", exact location, description, and entry preference
And urgency has not been changed from its default "Normal"
When the resident submits with no photographs
Then CampusFix creates exactly one request in "Submitted"
And assigns a unique tracking number and displays it in the confirmation
And the resident's read-only building and room are saved from housing data
And suggestions, when enabled, remain marked as advisory
```

## AC-002 — Supervisor overrides a suggestion (FR-006, FR-014)

```gherkin
Scenario: AC-002 — Supervisor overrides a suggestion
Given a submitted request has a system-suggested priority
And the supervisor has chosen a maintenance category
When the supervisor confirms a different final priority
Then the request is acknowledged and its final priority is used for dispatch
And the original suggestion, confirmed value, reviewer, and time are saved in audit history
```

## AC-003 — Supervisor assigns a visit by trade and workload (FR-008, FR-002)

```gherkin
Scenario: AC-003 — Supervisor assigns a visit by trade and workload
Given an acknowledged work order has no technician or visit window
And the supervisor sees technicians of the relevant trade with their workloads
When the supervisor assigns a technician and a valid visit window together
Then the work order becomes "Scheduled" and appears in that technician's assignments
And the owner receives one scheduled notification with the trade and window
And the technician receives the assignment notice
```

## AC-004 — Technician completes a documented repair (FR-009, FR-010, FR-002)

```gherkin
Scenario: AC-004 — Technician completes a documented repair
Given an assigned technician has an "In Progress" work order
And the technician can view the request details, entry permission, and prior repair history
When the technician records a diagnosis, work performed, labor time, parts if used, and confirmation of testing
Then CampusFix stores the work record and marks the work order "Completed"
And every resident request linked to that work order displays "Completed"
And each owner receives their own completion notice
```

## AC-005 — Technician puts work on hold (FR-011, FR-002)

```gherkin
Scenario: AC-005 — Technician puts work on hold
Given an assigned work order is "In Progress"
When the technician records "Waiting for part", identifies the part, and enters the next action
Then the work order becomes "On Hold"
And the hold reason, part, next action, technician, and time are retained
And each linked request owner receives the hold notification
```

## AC-006 — Routine room entry respects 24-hour notice (FR-004, NFR-08)

```gherkin
Scenario: AC-006 — Routine room entry respects 24-hour notice
Given a resident has requested a routine private-room visit
And no filed-repair-order exception has been authorized
When the supervisor attempts to schedule a window beginning 23 hours after the proposed notice
Then CampusFix rejects the window and explains that routine entry requires at least 24 hours' notice
```

## AC-007 — Resident reopens a completed request (FR-005)

```gherkin
Scenario: AC-007 — Resident reopens a completed request
Given a resident owns a "Completed" request linked to a completed work order
When the resident submits a new description with "Reopen Request"
Then that resident's request becomes "Reopened" with its original tracking number
And previous work records remain accessible
And the request enters supervisor triage without altering other linked residents' requests
```

## AC-008 — Supervisor combines duplicate reports (FR-007)

```gherkin
Scenario: AC-008 — Supervisor combines duplicate reports
Given two "Submitted" reports describe the same problem in the same building
When the supervisor confirms them as duplicates during triage
Then both original tracking numbers, owners, and histories are retained
And exactly one actionable work order is created for the shared problem
And neither request reveals the other resident's personal details
```

## AC-009 — Unacknowledged urgent intake escalates (FR-015)

```gherkin
Scenario: AC-009 — Unacknowledged urgent intake escalates
Given a request has resident urgency "Urgent" and remains "Submitted"
And the campus has configured an urgent response limit
When the configured response time expires without supervisor acknowledgment
Then CampusFix sends one supervisor escalation for that submitted period
And records its time without changing the request state or priority
```

## AC-010 — Another resident's tracking number does not leak information (FR-003, NFR-01)

```gherkin
Scenario: AC-010 — Another resident's tracking number does not leak information
Given a resident is signed in
And a valid tracking number belongs to a different resident
When the resident searches that tracking number
Then CampusFix returns the same "not found" response used for nonexistent tracking numbers
And does not reveal whether the other report exists
```

## AC-011 — Administrator sees filtered workload report (FR-012)

```gherkin
Scenario: AC-011 — Administrator sees filtered workload report
Given an administrator is signed in and has work-order records
When the administrator filters by campus building, category, and submission period
Then all report counts, workloads, and acknowledgment/completion averages use those filters
And no resident names, entry records, or photographs appear
```

## AC-012 — Incomplete submission does not create a ticket (FR-001)

```gherkin
Scenario: AC-012 — Incomplete submission does not create a ticket
Given a resident has a partially completed request form
When the resident submits without an exact location or description
Then CampusFix names the missing required fields
And creates no request or tracking number
And keeps the entered values for correction
```

## AC-013 — Saved status events trigger notifications (FR-002)

```gherkin
Scenario: AC-013 — Saved status events trigger notifications
Given a resident owns a request
When an authorized supervisor saves a valid acknowledgment transition
Then CampusFix sends one acknowledgment message to the owner's UNO email and activity feed
And includes only that resident's tracking number and the new status
```

## AC-014 — Changing entry preference cancels notice (FR-004)

```gherkin
Scenario: AC-014 — Changing entry preference cancels notice
Given a resident has an active request with a scheduled visit and a pending entry notice
When the resident changes their entry preference
Then CampusFix records the new preference and cancels the pending notice
And staff see a warning that a new visit window and notice are required
```

## AC-015 — Manual triage still works without suggestions (FR-006, FR-014)

```gherkin
Scenario: AC-015 — Manual triage still works without suggestions
Given suggestions are disabled for an unreviewed request
When the supervisor manually confirms category and final priority
Then CampusFix marks the request "Acknowledged"
And creates or links its unassigned work order
And saves the supervisor's identity and time
```

## AC-016 — Transfer sends work to unassigned triage (FR-011)

```gherkin
Scenario: AC-016 — Transfer sends work to unassigned triage
Given a technician has an active assigned work order
When the technician requests transfer with a target trade and reason
Then CampusFix sets the work order to unassigned "Acknowledged"
And cancels the pending visit and notice
And places it in the supervisor's transfer queue without erasing earlier work records
```

## AC-017 — Missing diagnosis prevents completion (FR-010)

```gherkin
Scenario: AC-017 — Missing diagnosis prevents completion
Given an assigned technician has an "In Progress" work order
When the technician attempts completion without a diagnosis or repair-tested confirmation
Then the work order stays "In Progress"
And CampusFix lists the missing fields
```

## AC-018 — Suggestions cannot act as final decisions (FR-014)

```gherkin
Scenario: AC-018 — Suggestions cannot act as final decisions
Given a new request has generated suggested category, priority, and possible duplicate matches
When the supervisor opens the triage screen
Then CampusFix labels the values as suggestions, not final values
And does not automatically merge reports or set a final priority
```

## AC-019 — Photos are optional and privacy warning appears (FR-001, NFR-04, NFR-06)

```gherkin
Scenario: AC-019 — Photos are optional and privacy warning appears
Given a resident has supplied all required request fields
And the form displays guidance not to photograph people or unrelated belongings
When the resident submits without photographs
Then the request is accepted with a tracking number
```

## AC-020 — No Access is rescheduled without treating it as a hold (FR-004, FR-008, FR-011)

```gherkin
Scenario: AC-020 — No Access is rescheduled without treating it as a hold
Given a work order is "No Access" after a recorded unsuccessful visit
When a supervisor selects a valid new visit window and assigned technician
Then CampusFix preserves the failed-access visit record and returns the work order to "Scheduled"
And issues a new entry notice under the applicable policy
```

## AC-021 — A recorded cleared blocker triggers scheduled resumption (FR-016)

```gherkin
Scenario: AC-021 — A recorded cleared blocker triggers scheduled resumption
Given a work order is "On Hold" waiting for a part
And a supervisor has confirmation that the part has arrived
When the supervisor records the blocker cleared and a valid return-visit window
Then CampusFix automatically changes the work order to "Scheduled"
And closes the hold record with who cleared it and when
And notifies the assigned technician and all linked request owners
```

## AC-022 — Resuming now requires assigned on-site technician (FR-016, FR-010)

```gherkin
Scenario: AC-022 — Resuming now requires assigned on-site technician
Given an assigned technician is present for a held work order
And required room entry has been recorded for the current visit
When the technician marks its blocker cleared and selects "Resume now"
Then CampusFix automatically changes the work order from "On Hold" to "In Progress"
And saves clearance identity, time, and hold history
```

## AC-023 — Linking a new request to scheduled work does not double-dispatch (FR-007)

```gherkin
Scenario: AC-023 — Linking a new request to scheduled work does not double-dispatch
Given a scheduled work order covers a problem already reported by one resident
And another resident submits a report of that same problem in the same building
When the supervisor links the submitted request to the active work order
Then no additional work order or technician visit is created
And each resident continues to see only their own report and linked work-order progress
```

## AC-024 — Invalid duplicate merge is rejected (FR-007)

```gherkin
Scenario: AC-024 — Invalid duplicate merge is rejected
Given two submitted requests concern different buildings
When a supervisor attempts to merge them
Then CampusFix rejects the merge and preserves both original reports
```

## AC-025 — Replacement candidates depend on configured thresholds (FR-013)

```gherkin
Scenario: AC-025 — Replacement candidates depend on configured thresholds
Given repeatRepairCount is 3 and repeatRepairWindow is 90 days for the selected campus
And an equipment item has three linked work orders dated within that window
When the administrator opens Replacement Candidates
Then CampusFix lists that equipment with location, repair count, and accessible repair history
```

## AC-026 — Missing replacement threshold does not invent a rule (FR-013)

```gherkin
Scenario: AC-026 — Missing replacement threshold does not invent a rule
Given repeatRepairCount has not been configured for the campus
When the administrator opens Replacement Candidates
Then no equipment is automatically flagged
And the screen states that the rule is not configured
```

## AC-027 — Hold escalation is recorded once (FR-015)

```gherkin
Scenario: AC-027 — Hold escalation is recorded once
Given a work order remains "On Hold" beyond the campus holdLimit
When CampusFix evaluates overdue holds more than once
Then the supervisor sees one escalation for that hold episode
And the work-order state remains "On Hold"
```

## AC-028 — Resident adds information without creating another request (FR-017)

```gherkin
Scenario: AC-028 — Resident adds information without creating another request
Given a resident owns a "Scheduled" request
When the resident adds a new comment and an optional photo
Then the tracking number and displayed status remain unchanged
And the new information appears in the request history for authorized staff
```

## AC-029 — Supervisor closes invalid submitted request with reason (FR-018)

```gherkin
Scenario: AC-029 — Supervisor closes invalid submitted request with reason
Given a resident's request is still "Submitted" with no dispatched work
When the supervisor closes it with a recorded nonmaintenance reason
Then CampusFix marks the request "Closed"
And notifies the owner with the reason
And creates no work order
```

## AC-030 — Front desk records phone report on behalf of resident (FR-019)

```gherkin
Scenario: AC-030 — Front desk records phone report on behalf of resident
Given authorized front-desk staff identify a resident with a current housing assignment
When staff record the reported maintenance issue with the required intake fields
Then CampusFix creates a "Submitted" request owned by the resident
And records the staff user as recordedBy
And sends the tracking confirmation to the resident
```

## AC-031 — Resident confirms completed work is resolved (FR-020)

```gherkin
Scenario: AC-031 — Resident confirms completed work is resolved
Given a resident owns a "Completed" request
When the resident confirms it is resolved
Then CampusFix marks only that request "Closed"
And no Reopen action remains for that request
```

## AC-032 — Optional auto-closure waits for configured interval (FR-020)

```gherkin
Scenario: AC-032 — Optional auto-closure waits for configured interval
Given a "Completed" request's campus has no closureConfirmationPeriod configured
When the resident takes no action
Then the request remains "Completed" and is not automatically closed
```

## AC-033 — Assigned technician only sees authorized work (FR-009, NFR-01)

```gherkin
Scenario: AC-033 — Assigned technician only sees authorized work
Given a technician has signed in to CampusFix
When the technician opens My Assignments
Then only work orders assigned to that technician appear
And other technicians' work-order photos and entry records are not accessible by direct URL
```

## AC-034 — Room notice may be shorter under documented exception (FR-004, NFR-08)

```gherkin
Scenario: AC-034 — Room notice may be shorter under documented exception
Given a repair order has been filed and the campus has configured an authorized shorter notice interval
When the supervisor schedules a visit meeting that shorter notice interval
Then CampusFix permits the shorter notice and records the exception and notice time
And the technician must still record knock-and-announce at entry
```

## AC-035 — Failed resident-present entry is No Access (FR-004, FR-011)

```gherkin
Scenario: AC-035 — Failed resident-present entry is No Access
Given the resident's entry choice is "Present" and a visit is scheduled
And the resident is absent when the technician arrives
When the technician reports the attempted visit
Then CampusFix records person, time, and no-access reason
And sets the work order to "No Access" without recording an unauthorized entry
```

## AC-036 — Emergency instructions appear on every resident request screen (FR-001, NFR-09)

```gherkin
Scenario: AC-036 — Emergency instructions appear on every resident request screen
Given a resident uses the dashboard, request form, or request details view
When the resident opens any of those screens
Then the front desk, RA-on-duty, and relevant campus emergency instructions are visible
And the form says emergencies are handled outside normal intake
```

## AC-037 — Viewing and editing are both audited (NFR-02)

```gherkin
Scenario: AC-037 — Viewing and editing are both audited
Given an authenticated supervisor has access to a maintenance request
When the supervisor views the request
Then CampusFix records an audit entry with the actor, action "view", record identifier, and time
```

## AC-038 — Accessibility and keyboard support (NFR-05)

```gherkin
Scenario: AC-038 — Accessibility and keyboard support
Given the resident and technician screens are implemented
When accessibility testing is performed against WCAG 2.1 AA
Then all required tasks are operable using keyboard navigation and assistive technology
And the WCAG 2.1 AA checks pass
```

## AC-039 — Draft survives failed uploads (NFR-11)

```gherkin
Scenario: AC-039 — Draft survives failed uploads
Given a resident has entered an unfinished request with an attached photo
When the photo upload fails and the resident returns to the form
Then CampusFix restores the saved draft and text fields
And retries the failed upload without creating a duplicate request
```

## AC-040 — Campus settings are separate (NFR-13)

```gherkin
Scenario: AC-040 — Campus settings are separate
Given the Dodge and Scott campuses have separate configuration sets
When an authorized administrator changes the Dodge campus holdLimit
Then the Scott campus holdLimit remains unchanged
```

## AC-041 — Former resident cannot submit new requests (NFR-14)

```gherkin
Scenario: AC-041 — Former resident cannot submit new requests
Given a user's official housing assignment has ended
When the user tries to submit a new maintenance request
Then CampusFix rejects the new submission
And preserves access to eligible previous requests for the configured retention period
```

## AC-042 — Photographs and entry records expire at retention (NFR-07)

```gherkin
Scenario: AC-042 — Photographs and entry records expire at retention
Given a photo and entry record have reached their university-configured retention deadline
When the retention process runs
Then the records are archived or deleted according to the campus retention rule
And they are no longer visible in ordinary resident and staff views
```

## AC-043 — Formal login and communication channels (NFR-10)

```gherkin
Scenario: AC-043 — Formal login and communication channels
Given an unauthenticated browser session
When the user opens a protected CampusFix view
Then CampusFix requires university single sign-on before showing protected data
```

## AC-044 — Mobile work-order details can be used without horizontal scrolling (FR-009, NFR-12)

```gherkin
Scenario: AC-044 — Mobile work-order details can be used without horizontal scrolling
Given a maintenance technician is viewing an assigned work order on a phone-width screen
When the technician opens work-order details and record-work actions
Then information and controls remain accessible without horizontal scrolling
```

## AC-045 — No other resident is notified when one shared report reopens (FR-005, FR-007)

```gherkin
Scenario: AC-045 — No other resident is notified when one shared report reopens
Given three requests were linked to one completed shared work order
When one owner reopens their own completed request with a description
Then only that request returns to "Reopened"
And the two other requests remain "Completed" or "Closed" as previously recorded
```
