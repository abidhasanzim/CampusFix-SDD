# CampusFix Architecture (layered variant)

**Authors:** Abid Hasan Zim, Zerin Shaima Meem  

## 1. Overview

CampusFix is a server-rendered Django web application with one PostgreSQL database, running on one university server, plus a cron-triggered scheduler. It is organized in layers rather than features:
- **`web`** handles requests and renders pages for each role.
- **`commands`** carries out every change, each in a single transaction.
- **`queries`** carries out every read.
- **`rules`**, a pure module, holds every rule the spec states as MUST: the transition table, the notice rule, and the completion checks.
- **Adapters** connect to SSO, the housing export, UNO email, and photo storage.

## 2. Modules

| Module | Responsibility | May depend on | Needed by |
|---|---|---|---|
| `web` | Turn HTTP requests into commands and queries, and render the pages for each role, including the emergency banner on resident pages. | `commands`, `queries`, `reports`, `files`, `integrations` | Every FR with a screen; NFR-05, NFR-09, NFR-12 |
| `commands` | Run each state-changing action as one transaction: check permission, lock rows, apply `rules`, then write records, status history, audit entry, and notifications. | `rules`, `policy`, `store`, `audit`, `suggest`, `files`, `outbox` | Status lifecycle; NFR-15; every FR that changes data |
| `queries` | Load records for display, including the activity feed, filtered by `policy`, and log each view. | `store`, `policy`, `audit` | FR-003, FR-006.1, FR-009; NFR-01, NFR-02 |
| `rules` | Hold pure functions with no I/O, each taking `now` as an argument: the transition table T1–T15, required fields, the notice rule, completion requirements, escalation and closure deadlines, and each FR's guard checks (for example FR-004.6, FR-004.7, FR-007.1, FR-010.2). | — | Status lifecycle; FR-001.3, FR-004.3, FR-010.4, FR-015, FR-020.2; NFR-08, NFR-17 |
| `policy` | Decide whether a user may see or do something, given the user and the record. | — | NFR-01; FR-003.2, FR-009.1, FR-012.3, FR-019.4 |
| `store` | Define the Django models, migrations, constraints, and sequences for all records, including per-campus settings and the read-only housing copy. | — | Domain Model; Configuration values; NFR-13 |
| `audit` | Append view and change entries. Entries are never updated or deleted. | `store` | NFR-02 |
| `outbox` | Send pending notifications by UNO email, claiming each row so it is sent by only one sender, and retry failures. | `store`, `integrations` | FR-002; NFR-10, NFR-16 |
| `suggest` | Compute advisory category, priority, and duplicate candidates. Pure function. | — | FR-014; NFR-03 |
| `files` | Validate, store, serve, and delete photo files. | `store`, `policy` | FR-001.5, FR-010.3, FR-017.1; NFR-01, NFR-07 |
| `integrations` | Connect to outside systems: SSO sign-in, housing export import, and the SMTP relay. | `store` | NFR-10; FR-001.2, FR-019.2; NFR-14 |
| `reports` | Compute the FR-012 figures and CSV export, and the FR-013 replacement candidates. | `store`, `policy`, `audit` | FR-012, FR-013 |
| `scheduler` | Run time-based checks when cron starts it: escalations, automatic closure, retention, outbox retry, and housing import. | `commands`, `outbox`, `integrations`, `files`, `rules`, `store` | FR-015, FR-020.2; NFR-07, NFR-16 |

Only `commands` changes requests, work orders, entry records, and their status. `audit`, `outbox`, `files`, and `integrations` write only their own records (log entries, sent state, photo files, and the housing copy). `web` and `scheduler` never write models directly. The dependencies form no cycles.

## 3. Request flow

### 3.1 Supervisor assigns and schedules a work order (FR-008; AC-008.1–AC-008.5, AC-004.2, AC-004.6, AC-002.3–AC-002.5)

1. The supervisor opens an `Acknowledged` or `No Access` work order. `queries` loads it only if `policy` allows (the supervisor's own campus) and logs the view. It lists technicians whose trade matches the category, with their open-work-order count and availability (FR-008.3, FR-008.4).
2. The supervisor picks a technician and a visit window. If the window misses every preferred slot, the supervisor adds a reason (FR-004.5); if the trade does not match, the supervisor confirms (FR-008.5). If the campus has set `repairOrderNotice`, the supervisor may also tick "use repair-order exception" (FR-004.3). `web` sends an `AssignAndSchedule` command that carries the work order's version.
3. `commands` opens a transaction and locks the work order, then its linked requests in id order. If the version has changed, it rejects the command (NFR-15, AC-N15.1).
4. `policy` confirms the supervisor's campus. `rules.transition` confirms T4 (from `Acknowledged`) or T7 (from `No Access`).
5. `rules.check_window` receives the current server time, `minEntryNotice`, whether the exception was ticked along with `repairOrderNotice`, and each linked request's entry preference. It fails if the elapsed time to the window start is shorter than the required notice, or if the window misses every preferred slot and no reason was given (AC-004.2, AC-004.6, AC-N17.1).
6. On any failure, the transaction rolls back and `web` shows the form with the reason. Nothing is saved or sent (AC-008.1).
7. Otherwise, `commands` writes:
   - the assignment and window;
   - the new status and its history;
   - one entry notice per linked request's owner, recording its send time and whether the exception was used (FR-004.3, AC-004.2);
   - the audit entry;
   - outbox rows: one `Scheduled` notification per owner with trade and window (AC-002.3, AC-002.4), and one assignment notification to the technician (AC-002.5).
8. After commit, `commands` asks `outbox` to send the new rows. Any that fail stay pending, and `scheduler` retries them (AC-N16.1).
9. The work order appears in the technician's Today or Upcoming list with its notice status (FR-009.1, AC-009.3).

### 3.2 Overdue urgent request escalates (FR-015; AC-015.1, AC-015.3, AC-015.5)

1. Cron starts `scheduler` every 5 minutes.
2. For each campus with `urgentResponseLimit` set, `scheduler` selects `Submitted` requests whose `residentUrgency` is `Urgent` and for which `rules.is_overdue(submitted_at, limit, now)` is true.
3. For each one, `commands.raise_escalation` inserts an escalation keyed by (request, submitted_at). A uniqueness constraint turns repeat runs into no-ops (AC-015.1).
4. The same transaction writes a request-history entry and outbox alerts to every supervisor of the campus. Status, priority, and assignment are untouched (FR-015.4).
5. The triage banner in `queries` lists escalations whose condition still holds, so acknowledgment removes the entry (AC-015.5). Hold escalations work the same way, keyed by hold record.

## 4. Design decisions

Decisions 1–10 settle the design questions the spec left open. A decision marked **Preference** has no requirement behind it.

| # | Decision | Reason |
|---|---|---|
| 1 | **Authentication.** Users sign in only through university SSO (in `integrations`). A stub login exists only in development settings. Login-required middleware wraps every `web` view. | NFR-10; AC-N10.1 |
| 2 | **Roles.** Staff roles are stored in `store`, keyed by SSO identity, and maintained by a system operator. A user may submit only while the housing copy shows a current assignment. `policy` grants read access by ownership, so a former resident can still read their own requests until `retentionPeriod`. | FR-001.1, NFR-14; AC-N14.1. Storing staff roles is a **Preference** (Spec issue 1). |
| 3 | **Housing data.** `integrations` imports the housing data nightly into a read-only copy. No command writes to it. | FR-001.2; Non-goal 6. The nightly import is a **Preference** (Spec issue 2). |
| 4 | **Shape.** One Django application and one PostgreSQL database, with no separate services, queues, or caches. | **Preference**: simplest design for C8. |
| 5 | **One write path.** Every change is a command in `commands`. A command runs in one transaction, locks rows with `SELECT … FOR UPDATE` (work order first, then requests by id), checks the form's version, and calls `rules` before writing anything. | Status lifecycle ("MUST reject other state changes"); NFR-15; FR-008.1; AC-N15.1, AC-N15.2 |
| 6 | **Pure rules.** Rules take `now` and configuration values as arguments and never read the clock themselves, so tests can fix the time. | NFR-17; AC-004.2, AC-N17.1 |
| 7 | **Time.** Times are stored in UTC and displayed in America/Chicago. Durations are compared as elapsed time, and a duration equal to the limit passes. | NFR-17 |
| 8 | **Notice rule.** Required notice is `minEntryNotice` (24 h) unless the supervisor ticks the repair-order exception on that window. The exception can be ticked only when `repairOrderNotice` is set, and its use is recorded with the notice. `rules.check_window` runs on every command that sets a window (T4, T7, T10, reassignment). | FR-004.3; NFR-08; AC-004.2 |
| 9 | **Notifications.** Outbox rows are written in the command's transaction, so the feed entry exists at commit. The email is sent after commit. A sender claims rows with `SELECT … FOR UPDATE SKIP LOCKED`, so the immediate send and a `scheduler` retry never send the same row together. | FR-002.2; NFR-16; AC-002.2, AC-N16.1 |
| 10 | **Suggestions.** Local keyword rules suggest category and priority. Duplicate candidates are open requests in the same room or on the same floor of the same building, and flags are computed once, at submission, so a dismissed pair is never flagged again. A per-campus `suggestionsEnabled` setting turns suggestions off. If `suggest` fails, the command continues without suggestions. | FR-014.1–FR-014.3, FR-007.5; NFR-03; AC-006.4, AC-007.5, AC-014.3. Keyword rules, and leaving out the photo and equipment clauses, are **Preferences** under C4 (Spec issue 3). |
| 11 | **Escalations once.** A uniqueness constraint applies per `Submitted` period and per hold record. | FR-015.3; AC-015.1, AC-015.4 |
| 12 | **Same 404.** `queries` returns the same not-found page whether a record does not exist or `policy` refuses it. | FR-003.2; NFR-01; AC-003.3, AC-009.1 |
| 13 | **Identifiers.** Tracking numbers come from a PostgreSQL sequence per Central-time calendar year; work-order numbers come from a separate sequence. | Domain Model. The year rule is a **Preference**. |
| 14 | **Photos.** Photos are stored on local disk outside the web root and served by `files` after a `policy` check. Size and count limits come from campus settings. Only JPG and PNG are accepted, verified by content. | FR-001.4–FR-001.5; NFR-01; AC-001.4, AC-001.5, AC-N01.1. Accepting only JPG and PNG is a **Preference** (Spec issue 8). |
| 15 | **Drafts.** Each intake user has one server-side draft, and photos attach to it. | FR-001.10; NFR-11; AC-N11.1. Keeping drafts on the server is a **Preference**. |
| 16 | **Displayed status.** A request's displayed status is computed at read time from its linked active work order. | Status lifecycle (`displayStatus` is derived); AC-005.4 |
| 17 | **Resume now (T9).** Requires the assigned technician, an entry record dated today for the current visit, and the technician's on-site confirmation. | FR-016.2; AC-016.1, AC-016.3. The evidence rule is a **Preference** (Spec issue 6). |
| 18 | **Reports.** Reports are computed on demand from status history; the CSV export uses the same query, and viewing a work order's history is logged. | FR-012.1–FR-012.4, FR-013; NFR-02; AC-012.1, AC-013.1. On-demand computation is a **Preference**. |
| 19 | **Pages.** Pages are server-rendered with mobile-first CSS. JavaScript is used only for drafts, upload retry, and showing the emergency instructions again when Urgent is chosen. | NFR-05, NFR-12; AC-001.7, AC-009.4, AC-N05.1. Choosing this over a single-page app is a **Preference**. |
| 20 | **Campus settings.** Settings are stored as one row per campus and edited in the Django admin by authorized administrators. `minEntryNotice` defaults to 24 h and cannot be set lower. `emergencyContacts`, the photo limits, `urgentResponseLimit`, `holdLimit`, and `retentionPeriod` must be filled in before a campus goes live. `repairOrderNotice`, the repeat-repair thresholds, and `closureConfirmationPeriod` are optional; when unset, their rule is off and the screen says so. | NFR-13; FR-013.4, FR-020.3; AC-013.3, AC-020.3, AC-N13.1. Which values are required before launch is a **Preference** (Spec issue 8). |
| 21 | **Linked requests complete together.** T11 sets every linked request to `Completed` in the same transaction. | FR-010.6; AC-010.4. The transition table has no request row for this (Spec issue 12). |

## 5. Constraints and known limits

### Constraints

- **C1** Python 3.12 and Django 5.2 LTS.
- **C2** PostgreSQL 16 is the only data store, because the design needs its row locks and sequences. Photos are stored on the server's disk.
- **C3** One Linux server runs Nginx, Gunicorn, PostgreSQL, and one cron entry, served over HTTPS.
- **C4** Free and open-source software only, with no paid cloud or AI services.
- **C5** University SSO uses SAML 2.0 or OIDC, whichever UNO ITS provides. Development uses a stub login.
- **C6** UNO email goes through the university SMTP relay. Development uses Django's console email backend.
- **C7** Housing assignments come from a university export whose format is to be confirmed. Development uses seeded fixtures.
- **C8** The team is two people working for one semester.

### Known limits

- **One server.** There is no failover, so an outage stops intake. Emergencies are unaffected because they never go through CampusFix. The design can run several `web` processes because all state is in PostgreSQL, but `scheduler` must run once.
- **Timing.** Escalations and automatic closures can be up to one cron interval late.
- **Housing import.** The housing copy can be up to a day old. A new resident may wait for the next import, and a departed resident may still submit until it runs.
- **Duplicate email.** If the server crashes after the mail server accepts a message but before the row is marked sent, that email can be sent again. Feed entries are unaffected.
- **Suggestions.** Keyword rules only; there is no photo analysis.
- **Email.** Email is one-way, and technicians need a network connection.

### If requirements grow

- **Each new rule:** add a function to `rules` and a command that calls it. Existing commands are untouched.
- **New notification channels:** add a sender in `outbox`.
- **Heavier reporting:** add summary tables written by `commands`.
- **Offline technicians:** needs client storage and a sync command with conflict handling. This is a major change.

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

1. **Role source.** The spec does not say where staff roles, supervisor campuses, and technician trades come from, or who maintains them.
2. **Housing data.** The housing export's interface and freshness are unspecified. So is what happens to an open request's visits and entry permission when its owner's assignment ends.
3. **Equipment.** FR-013.1 links work orders to equipment, but nothing says who creates equipment records. FR-014.2 flags duplicates "for the same equipment", but a new request has no equipment link.
4. **Notice exception.** Every visit follows a filed request, yet FR-004.3 keeps a routine 24-hour case and AC-004.2 requires the exception to be recorded. Nothing says when the exception may be used. Decision 8 makes it an explicit choice by the supervisor on each window.
5. **Timing tolerance.** FR-015 and FR-020.2 do not say how soon after a limit the escalation or closure must happen.
6. **Being on site.** FR-016.2 requires the technician to be "confirmed present on site" without defining the evidence.
7. **Retention scope.** `retentionPeriod` covers photographs and entry records, yet NFR-14 also uses it for read access to past requests. How long request records themselves are kept is not stated.
8. **Photo formats and missing values.** FR-001.5 says "JPG and PNG at minimum" without saying whether other formats are allowed. The spec also gives no values for the photo limits, `urgentResponseLimit`, `holdLimit`, `retentionPeriod`, or `emergencyContacts`, so Decision 20 requires them before launch.
9. **Draft strength.** FR-001.10 makes drafts a SHOULD, but AC-N11.1 tests them as required.
10. **Reassignment.** FR-008.6 allows reassignment only while a work order is `Scheduled`. `On Hold` work moves only through the technician's transfer (FR-011.3).
11. **Notice during an email outage.** The entry notice is recorded and shown in the feed at commit, but its email may be delayed (Decision 9). FR-004.3 does not say whether notice starts at recording or at email delivery.
12. **Completing linked requests.** FR-010.6 requires every linked request to become `Completed`, but the transition table has no request row for this; T11 covers only the work order.
13. **Closing a reopened request.** T3 lets a supervisor close a `Reopened` request. A reopened request is still linked to its earlier `Completed` work order, which AC-018.3 ("a `Scheduled` or later work order") forbids.
14. **Retrying uploads after leaving.** AC-N11.1 says a failed upload is retried. A file that never reached the server can be resent only while the page is open; after the resident leaves, they must select it again.
