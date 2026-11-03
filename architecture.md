# CampusFix Architecture

**Authors:** Abid Hasan Zim, Zerin Shaima Meem  

## 1. Overview

CampusFix is a server-rendered Django web application backed by one PostgreSQL database. It runs as a single deployment on one university server, plus a job runner started by cron. It is a modular monolith with one Django app per area of the spec. One shared module, `maintenance`, owns the records and is the only code that changes a status. CampusFix uses three outside systems: university SSO, the housing-assignment export, and UNO email.

## 2. Modules

| Module | Responsibility | May depend on | Needed by |
|---|---|---|---|
| `accounts` | Sign users in through SSO and identify each user's staff role (supervisor and campus, technician and trade, administrator, front-desk). | `housing` | NFR-10; FR-019; Actors |
| `housing` | Keep a read-only copy of campuses, buildings, floors, rooms, and current room assignments, refreshed from the university export. | — | FR-001, FR-019, NFR-14 |
| `campus_settings` | Store each campus's configuration values, editable only by authorized administrators. | `housing`, `accounts` | Configuration values; NFR-13 |
| `audit` | Append view and change entries. Entries are never updated or deleted. | — | NFR-02 |
| `maintenance` | Own the records for requests, work orders, holds, work, parts, equipment, and suggestions with their final decisions. Change a status only through the transition table (T1–T15) and write its history. | `housing`, `accounts`, `audit` | Domain Model; Status lifecycle; NFR-15 |
| `access` | Decide whether a user may see or act on a request, work order, photo, or report, and log each permitted view. | `accounts`, `maintenance`, `audit`, `campus_settings` | NFR-01, NFR-02, NFR-14 |
| `notifications` | Record each notification in the same transaction as its event, and deliver it by UNO email and the activity feed, retrying failed email. | `accounts` | FR-002; NFR-10, NFR-16 |
| `photos` | Validate, store, and serve photographs privately. Hold uploads made before submission until they are linked to a record, and delete photos when retention ends. | `access`, `maintenance`, `campus_settings` | FR-001, FR-010, FR-017; NFR-01, NFR-07 |
| `entry` | Keep entry preferences, send and cancel entry notices, record entries and failed attempts, enforce the notice rule, and delete entry records when retention ends. | `maintenance`, `campus_settings`, `notifications` | FR-004; NFR-07, NFR-08, NFR-17 |
| `suggestions` | Compute advisory category, priority, and duplicate candidates from a request's text and location. Stores nothing and has no side effects. | — | FR-014; NFR-03 |
| `intake` | Carry out resident and front-desk actions on requests: submit, save drafts, track, change entry preference, add information, reopen, and confirm or expire closure. Render the emergency banner. | `maintenance`, `housing`, `entry`, `photos`, `suggestions`, `access`, `notifications`, `campus_settings` | FR-001, FR-003, FR-005, FR-017, FR-019, FR-020; NFR-09, NFR-11, NFR-14 |
| `triage` | Carry out supervisor decisions before dispatch: confirm category and priority, link or merge duplicates, close without a work order, and re-categorize transferred work orders. Raise and show escalations. | `maintenance`, `access`, `notifications`, `campus_settings` | FR-006, FR-007, FR-015, FR-018 |
| `dispatch` | Assign and reassign a technician together with a visit window. | `maintenance`, `entry`, `access`, `notifications`, `accounts` | FR-008 |
| `fieldwork` | Carry out actions on dispatched work orders: record an entry or failed access, start, record work, link equipment, complete, hold, transfer, and clear a hold. Supervisors use the clear-hold and equipment actions. | `maintenance`, `entry`, `photos`, `access`, `notifications` | FR-009, FR-010, FR-011, FR-013 (link), FR-016 |
| `reports` | Compute administrator reports and replacement candidates from stored history. | `maintenance`, `campus_settings`, `access` | FR-012, FR-013 |
| `jobs` | Run time-based checks on a schedule: urgent and hold escalations, automatic closure, retention, email retry, and housing refresh. | `triage`, `intake`, `photos`, `entry`, `notifications`, `housing` | FR-015, FR-020, NFR-07, NFR-16 |

Every module that changes records may also depend on `audit`. The dependencies form no cycles. Pages in `intake`, `triage`, `dispatch`, `fieldwork`, and `reports` share one set of base templates (Decision 19), which is where NFR-05 and NFR-12 are met.

## 3. Request flow

### 3.1 Resident submits a request (FR-001; AC-001, AC-012, AC-019, AC-039)

1. The resident opens Submit Request. `accounts` requires an SSO session and sends a signed-out user to SSO first (AC-043).
2. `intake` asks `housing` for the resident's current room assignment. If there is none, it refuses the submission (AC-041). Otherwise it shows the form with building and room read-only, and the emergency banner from `campus_settings` (AC-036).
3. As the resident types, the browser saves the form to the resident's server-side draft in `intake`. Each photo uploads separately to `photos`, which checks the file type by content and the campus photo limits, then holds it as an unattached upload owned by the resident. The browser retries a failed upload (AC-039).
4. The resident submits. `intake` validates the required fields and takes building and room from `housing`, never from the posted form. If a field is missing, the form returns with each missing field named, and the draft and photos are kept. Nothing else is written (AC-012).
5. `intake` loads open requests in the same room, or on the same floor of the same building, from `maintenance`. It passes them to `suggestions` with the description and location. If the campus has suggestions turned off, or the call raises an error, `intake` continues without them (AC-015).
6. `intake` opens one database transaction (NFR-15). Inside it:
   1. Take the next tracking number from the year's sequence.
   2. Create the request and apply T1 through `maintenance`, which writes status history and an audit entry.
   3. Save the entry preference through `entry`.
   4. Link the resident's unattached uploads to the request in `photos`.
   5. Save the suggestion record labeled as suggested.
   6. Write the confirmation notification (email and feed) through `notifications`.
   7. Delete the draft.

   If any step fails, everything rolls back and the draft remains.
7. After commit, `notifications` tries to send the email immediately. If UNO email is unavailable, the notification stays pending and `jobs` retries it (NFR-16).
8. The resident sees the tracking number and `Submitted` status (AC-001). The request now appears in the campus triage queue.
9. If the resident chose `Urgent` and no supervisor acknowledges the request within `urgentResponseLimit`, the next `jobs` run makes `triage` record one escalation and alert the campus supervisors (AC-009).

### 3.2 Technician completes a shared work order (FR-010; AC-004, AC-017, AC-047)

1. The technician opens the work order through `access`. A technician who is not assigned to it gets the not-found page, and the view is logged (AC-033, AC-037). Only the assigned technician sees the Complete action (FR-010).
2. The technician submits the work record. If a required item is missing, `fieldwork` lists what is missing and leaves the status unchanged (AC-017).
3. One transaction (NFR-15):
   1. Lock the work order, then its linked requests in id order.
   2. Check the work order is still `In Progress` and the form's version matches.
   3. Save the work record and apply T11.
   4. Mark each linked request `Completed` as part of T11, writing history and audit (Spec issue 12).
   5. Write one completion notification per owner, each with only that owner's tracking number.
4. After commit, emails are sent or left for retry (AC-047).

## 4. Design decisions

Decisions 1–10 settle the design questions the spec left open. A decision marked **Preference** has no requirement behind it.

| # | Decision | Reason |
|---|---|---|
| 1 | **Authentication.** Users sign in only through university SSO; CampusFix stores no passwords. A stub login exists only in development settings. Login-required middleware in `accounts` covers every page. | NFR-10; AC-043 |
| 2 | **Roles.** Staff roles live in `accounts`, keyed by SSO identity and maintained by a system operator. A user may submit as a resident only while `housing` shows a current room assignment. Read access depends on ownership, not on current assignment: `access` lets owners read their requests until `retentionPeriod`. | FR-001, NFR-14; AC-041. Storing staff roles in CampusFix is a **Preference**, because the spec does not say where roles come from (Spec issue 1). |
| 3 | **Housing data.** CampusFix keeps a read-only local copy that `jobs` refreshes nightly from the university export. No screen edits it. | FR-001; Non-goal 6. The nightly refresh is a **Preference** (Spec issue 2). |
| 4 | **Shape.** One Django application and one PostgreSQL database, with no separate services, message queues, or caches. | **Preference**: the simplest design that meets every acceptance criterion for a two-person team (C8). |
| 5 | **Status changes.** Only `maintenance.transition()` changes a status. It checks T1–T15 and writes history and audit. Each action runs in one transaction that locks its rows with `SELECT … FOR UPDATE` (work order first, then linked requests by id). Each form carries the record's version, and a stale version is rejected. | Status lifecycle ("MUST reject other state changes"); NFR-15; FR-008; AC-046 |
| 6 | **Notifications.** Each notification is written as a row in the same transaction as its event. The activity feed reads the same rows, so the feed entry is visible at commit. After commit, a sender claims pending rows with `SELECT … FOR UPDATE SKIP LOCKED`, so the immediate send and a `jobs` retry never send the same row at once. Failed sends stay pending and are retried. | FR-002 (sent only after saving); NFR-16; AC-013, AC-047 |
| 7 | **Time.** Times are stored in UTC and displayed in America/Chicago. Limits are compared as elapsed durations against the database clock, and a duration equal to the limit passes. This is enforced in `entry` (notice), `triage` (escalation), and `intake` (auto-closure). | NFR-17; AC-006, AC-048 |
| 8 | **Notice rule.** Required notice is `minEntryNotice` (24 h). A supervisor may choose the repair-order exception on a particular window only when the campus has set `repairOrderNotice`; `entry` records the choice with the notice. `entry.check_window()` runs on every visit-window save (T4, T7, T10, reassignment), and the save fails if the check fails. | FR-004; NFR-08; AC-006 (no exception authorized → 24 h), AC-034 (exception recorded) |
| 9 | **Scheduled checks.** One management command, run by cron every 5 minutes, handles escalations, auto-closure, retention, and email retry; it refreshes housing nightly. A uniqueness constraint per `Submitted` period and per hold record makes repeated runs raise only one escalation. `notifications` sends each escalation to every supervisor of the request's campus. | Uniqueness: FR-015; AC-009, AC-027. The 5-minute interval and alerting every campus supervisor are **Preferences** (Spec issues 5 and 10). |
| 10 | **Suggestions.** Category and priority come from local keyword rules. Duplicate candidates are open requests in the same room, or on the same floor of the same building. Each campus has a `suggestionsEnabled` setting, and flags are computed once, at submission. There is no external AI service and no photo-based suggestion. | FR-014, NFR-03; AC-015, AC-018. Keyword rules and leaving out photo-based suggestion (FR-014 is a SHOULD) are **Preferences** made under C4. |
| 11 | **Identifiers.** Tracking numbers come from one PostgreSQL sequence per calendar year (Central time); work-order numbers come from a separate sequence. Sequences stay unique when submissions happen at the same moment. | Domain Model (format and uniqueness). Basing the year on Central time is a **Preference**. |
| 12 | **Not found.** Every detail page loads its record through `access`. A record that does not exist and one the user may not see return the same 404 page. Permitted views are logged. | NFR-01, NFR-02; AC-010, AC-033, AC-037 |
| 13 | **Photos.** Photos are stored on local disk outside the web root under random names and served only through an `access`-checked view. The size and count limits come from `campus_settings`. Only JPG and PNG are accepted, after a content check. | FR-001; NFR-01; AC-019. Restricting formats to JPG and PNG is a **Preference**. |
| 14 | **Drafts.** Each resident or front-desk user has one server-side draft in `intake`, saved as the form changes. Photos the user uploads stay in `photos` until submission. | NFR-11; AC-039. Keeping drafts server-side is a **Preference**, because browser storage cannot hold photos reliably. |
| 15 | **Campus settings.** Configuration values are stored as one row per campus. `minEntryNotice` defaults to 24 h and cannot be set lower. `emergencyContacts`, the photo limits, `urgentResponseLimit`, `holdLimit`, and `retentionPeriod` must be filled in before a campus goes live. `repairOrderNotice`, `repeatRepairCount`/`repeatRepairWindow`, and `closureConfirmationPeriod` are optional: when unset, their rule is off and the screen says so. | NFR-13, NFR-08; FR-013, FR-020; AC-026, AC-032, AC-040. Which values are required before launch is a **Preference** (Spec issue 8). |
| 16 | **Displayed status.** A request linked to an active work order shows that work order's status. The status is computed when read, not stored twice. | Status lifecycle (`displayStatus` is derived); AC-023, AC-045 |
| 17 | **Resume now (T9).** Only the assigned technician may resume, only when `entry` holds an entry record for the current visit dated today, and only after the technician confirms being on site. | FR-016; AC-022. Using "an entry dated today" as evidence is a **Preference** (Spec issue 6). |
| 18 | **Reports.** Reports are computed on demand with SQL over status history and work orders. There is no separate reporting store. | FR-012, FR-013; AC-011, AC-025. On-demand queries are a **Preference** at one university's volume. |
| 19 | **Pages.** Pages are server-rendered HTML with mobile-first CSS and semantic markup. JavaScript is used only for saving drafts and retrying uploads. | NFR-05, NFR-12; AC-038, AC-044. Not building a single-page app is a **Preference**. |
| 20 | **Linked requests complete together.** When T11 completes a work order, `maintenance` sets every linked request to `Completed` in the same transaction. | FR-010; AC-004, AC-047. The transition table has no row for this (Spec issue 12). |

## 5. Constraints and known limits

### Constraints

- **C1** Python 3.12 and Django 5.2 LTS.
- **C2** PostgreSQL 16 is the only data store, because it provides row locks and sequences. Photos are stored on the server's disk.
- **C3** One Linux server runs Nginx, Gunicorn, PostgreSQL, and one cron entry, served over HTTPS. The database clock and the server clock are therefore the same clock.
- **C4** Free and open-source software only, with no paid cloud or AI services.
- **C5** University SSO uses SAML 2.0 or OIDC, whichever UNO ITS provides. Development uses a stub login.
- **C6** UNO email goes through the university SMTP relay. Development uses Django's console email backend.
- **C7** Housing assignments come from a university export whose format is to be confirmed. Development uses seeded fixtures.
- **C8** The team is two people working for one semester.

### Known limits

- **One server.** If it is down, no one can submit or update requests. Emergencies are unaffected because they never go through CampusFix. More web processes can be added because all state is in PostgreSQL, but `jobs` must run on exactly one machine.
- **Timing.** Escalations and automatic closures can be up to one cron interval late.
- **Housing refresh.** The housing copy can be up to a day old. A new resident may have to wait for the next refresh to submit, and a departed resident may still submit until it runs.
- **Duplicate email.** If the server crashes after the mail server accepts a message but before the row is marked sent, that one email can be sent again. In-app notifications are not affected.
- **Suggestions.** Suggestions are keyword-based only. There is no photo analysis.
- **Email.** Email is one-way: replies to notification emails do not reach the record.
- **Connectivity.** Technicians need a network connection, because there is no offline mode.
- **Reports at scale.** Reports query live tables. A much larger dataset would need summary tables.

### If requirements grow

- **New notification channels (SMS, push):** add a delivery method in `notifications`.
- **More campuses:** add data rows in `housing` and `campus_settings`. No code changes.
- **Vendor or approval workflows:** add a new module that depends on `maintenance`.
- **Two-way legacy integration:** add an adapter module.
- **Offline technician use:** needs client storage, a sync endpoint, and conflict handling. This is a major change.

## 6. Out of scope

Copied from the spec's Non-goals. CampusFix will not:

1. Dispatch or coordinate emergency response.
2. Import records from, synchronize with, or change Freshdesk, the Scott Campus resident portal, Smartsheet, or Maxient.
3. Bill residents for damage (MavLINK) or manage building access and keys (MavCARD).
4. Handle budgeting, purchasing, or parts inventory.
5. Schedule staff shifts.
6. Edit housing assignment data.
7. Merge two work orders that have both been dispatched, or cancel a duplicate dispatch.
8. Make final triage decisions automatically.
9. Provide a native mobile app.

## 7. Spec issues

1. **Role source.** The spec does not say where staff roles and campus or trade assignments come from, or who maintains them.
2. **Housing data.** The interface and refresh frequency are unspecified. So is what happens to an open request's visits and entry permission when its owner's assignment ends.
3. **Equipment.** FR-013 links work orders to equipment, but nothing says who creates equipment records. FR-014 flags duplicates "for the same equipment", but a new request has no equipment link, so that check cannot run at submission.
4. **Notice exception.** Every CampusFix visit follows a filed request, but the spec still keeps a routine 24-hour case (AC-006) and requires the exception to be authorized and recorded (AC-034). It never says when a supervisor may use the exception. Decision 8 makes it an explicit, recorded choice on each window.
5. **Timing tolerance.** FR-015 and FR-020 say when an escalation or automatic closure is due, but not how soon after the limit it must happen.
6. **Being on site.** FR-016, T9, and AC-022 require the technician to be "present on site" but do not define what proves it.
7. **Retention scope.** `retentionPeriod` covers photographs and entry records, but NFR-14 also uses it for read access to past requests. AC-041 refers to "eligible" requests without defining them. How long request records themselves are kept is not stated.
8. **Missing values.** The spec gives no values for the photo limits, `urgentResponseLimit`, `holdLimit`, `retentionPeriod`, or `emergencyContacts`. Decision 15 requires all of them before a campus goes live.
9. **Reassignment.** FR-008 allows reassignment only while a work order is `Scheduled`. A supervisor cannot move `On Hold` work to another technician except through the technician's own transfer (FR-011).
10. **Escalation recipients.** FR-015 alerts "the campus supervisor" in the singular. Decision 9 alerts every supervisor of the campus.
11. **Notice during an email outage.** The entry notice is recorded and shown in the activity feed at commit, but its email may be delayed (Decision 6). The spec does not say whether the 24-hour period starts when the notice is recorded or when the email is delivered.
12. **Completing linked requests.** FR-010 and AC-004 require every linked request to become `Completed`, but the transition table has no request row for this; T11 covers only the work order. Decision 20 treats it as part of T11.
13. **Retrying uploads after leaving.** AC-039 says CampusFix retries a failed upload after the resident returns. A file that never reached the server can be resent only by the browser while the page is still open; after the resident leaves, they must select the file again.
