# Product roadmap

The tracker stays local-first: SQLite remains the source of truth, personal files remain outside Git, and no external account action or application submission happens without the user's review.

## Phase 2.1 — Reliable daily workflow

Implemented in the current development version:

- Board drops use a normal form submission and persist the destination status before the board reloads.
- Moving to Applied sets an Applied Date when one is missing.
- Entering an Applied Date while a job is Saved, Preparing, or Applying advances it to Applied.
- Entering an Interview Date before the interview stage advances it to Interview.
- URL preview labels extracted values that need confirmation and fields that are still missing.
- Company and role are required before an application can be saved.
- Excel export contains Applications, Requirements, Documents, Status History, and Activities.

Still worth adding after the profile work:

- A structured "Close application" flow for Rejected and Withdrawn: date, reason category, stage reached, feedback, and whether to reapply.
- Archive and duplicate-merge controls so old applications stay available without crowding the active board.
- A visible Undo link after quick moves and actions.

## Phase 3 — Profile and application form pack

### 3A. Reusable local profile

Create a dedicated Profile page with structured sections instead of one large notes field:

- Identity and contact: preferred name, legal name, email, phone, address, portfolio, LinkedIn, GitHub.
- Work eligibility: citizenship/work authorization, sponsorship requirement, notice period, willingness to relocate and travel.
- Education: institution, degree, subject, dates, grade, location.
- Experience: employer, title, dates, location, responsibilities, achievements, technologies, and reusable bullet points.
- Projects and publications: description, impact, links, technologies, dates.
- Skills, tools, languages, certifications, and driving licence.
- Reusable answers: salary, start date, motivation, leadership, conflict, strengths, demographic "prefer not to say" choices, and other recurring questions.
- Document catalogue: CV and cover-letter versions plus local file references. Files themselves remain in the user's chosen folders.

Each section gets a completeness indicator. Resume import must show a preview and differences before it changes the profile.

Passwords, one-time codes, security answers, passport scans, bank details, and portal credentials must never be stored in this tracker.

### 3B. Per-application form pack

For every application, generate a reviewed snapshot of the profile rather than reading the live profile blindly. The pack should:

- List portal sections and every missing answer before the user opens the external form.
- Recommend the most relevant experience bullets and projects from job requirements and tags.
- Preserve the exact answers, CV version, and salary value used for that application.
- Provide one-click copy controls for individual answers and a clean print view.
- Mark each answer as Profile value, Job-specific answer, Missing, or Needs confirmation.
- Record portal name, account email, and application URL, but never the password.

This snapshot matters because the profile will improve over time while submitted applications must retain an accurate historical record.

## Salary guidance

Keep three values separate:

1. Advertised compensation copied from the vacancy, with currency, period, location, and source URL.
2. Personal minimum and target, configurable by role family and location.
3. Market benchmark, including source, occupation match, region, data date, and confidence.

The assistant can recommend a range and explain it, but it must not silently overwrite the user's value. A recommendation should show annual and monthly gross amounts, flag ambiguous currencies or periods, and state when the occupational match is broad. For Germany, the Bundesagentur für Arbeit Entgeltatlas is a suitable official benchmark source; job-posting ranges and collective agreements can supplement it.

## Phase 4 — Reviewed browser form assistant

Build this only after the profile and application pack are dependable.

- Use a small Manifest V3 browser extension activated by the user on the current tab.
- Request `activeTab` and narrowly scoped optional host permissions, not permanent access to every website.
- Detect visible fields, map them to the reviewed application pack, and show a preview of proposed changes.
- Fill only after explicit confirmation. Never click the final Submit button.
- Add portal adapters incrementally: Workday first, then common Greenhouse, Lever, and SuccessFactors patterns.
- Keep a fallback copy panel because employer-specific questions and portal layouts vary.

Candidate accounts remain user-controlled. The helper may remember which email was used for a portal, but sign-in, multi-factor authentication, CAPTCHA, legal declarations, and final submission stay with the user.

## Phase 5 — Email and calendar assistance

Start with a no-account option: paste an email or import a local `.eml` file, detect the company/application/stage, and preview the proposed activity. Then add optional providers:

- Gmail OAuth with the smallest practical read scope.
- Microsoft Graph delegated permissions for Outlook, again using least privilege.
- A review queue that suggests links to applications and status/stage changes; no automatic status change without confirmation.
- Calendar-event creation only after the interview details have been reviewed.

Sending replies is deliberately later than reading and classifying. The first useful version should prepare a draft or copy-ready response and leave sending to the user.

## Professional hardening

- Automated encrypted backups and a tested restore command.
- Schema migration tooling before profile tables expand.
- Export/import round-trip tests and a privacy-safe diagnostic bundle.
- Data-quality checks for duplicate URLs, missing companies, impossible date order, and stale next actions.
- Funnel analytics by role family, source, CV version, and interview stage.
- Keyboard accessibility, responsive board alternatives, and a non-drag status control for every card.

## Recommended order

1. Profile schema and Profile page.
2. Application form pack and missing-answer checklist.
3. Structured rejection/withdrawal flow, archive, merge, and Undo.
4. Salary recommendation panel with source and confidence.
5. Workday browser assistant proof of concept on a test application, without final submission.
6. Email import preview, then optional Gmail/Outlook connections.
7. Calendar integration and analytics.

## Technical references

- [Chrome extension permissions](https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions) and [the scripting API](https://developer.chrome.com/docs/extensions/reference/api/scripting)
- [Workday candidate-account and Quick Apply configuration](https://doc.workday.com/admin-guide/en-us/human-capital-management/recruiting/career-sites/san1431625385171.html)
- [Gmail OAuth scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) and [desktop OAuth quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [Microsoft Graph delegated authentication](https://learn.microsoft.com/en-us/graph/auth-v2-user) and [permission guidance](https://learn.microsoft.com/en-us/graph/permissions-overview)
- [Bundesagentur für Arbeit Entgeltatlas](https://web.arbeitsagentur.de/entgeltatlas/)
