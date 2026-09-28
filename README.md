# Job Application Tracker

A small, professional, local-first tracker for personal job applications on macOS. SQLite is the source of truth; the web UI runs only on your computer.

## Current features

- Add a job from a URL with best-effort JSON-LD/OpenGraph extraction
- Review extracted, missing, and confirmation-required fields before saving
- Require company and role so incomplete URL extraction cannot create blank applications
- Duplicate URL warnings
- Manual application creation and editing
- Board view with quick status moves and detailed pipeline stages
- Drag-and-drop board movement and reversible workflow shortcuts
- Action Inbox for replies, due follow-ups, upcoming interviews, and missing next steps
- Context-aware status/stage controls in both detail and table views
- Lifecycle synchronization: board moves persist, Applied Date advances to Applied, and Interview Date advances to Interview
- Manual activity timeline for replies, calls, follow-ups, and interviews
- Action-needed flags for incoming messages that require a response
- Structured interview scheduling with format, interviewer, meeting link, and preparation notes
- Flexible employer-specific requirements and readiness checklist
- Document references without copying personal files into the project
- Automatic status history
- Dashboard plus searchable, filterable application list
- Read-only `.xlsx`/`.xlsm` import preview
- CSV and XLSX exports

## Setup

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>.

The default database is `data/tracker.sqlite`. Override it with `JOB_TRACKER_DATABASE_URL` if needed; see `.env.example`.

## Tests

```bash
pytest
```

## Privacy

The database, import directory, private data, exports, PDFs, and personal document folders are ignored by Git. The app stores document paths and metadata only—it does not copy CVs, cover letters, certificates, or transcripts into this repository.

The workbook import screen is preview-only. It does not write source rows into SQLite.

## Planned next phase

The next major capability is a reusable, local personal profile plus a per-application form pack. It will hold contact details, work authorization, education, employment history, languages, skills, links, and reviewed answers to recurring questions. A later browser assistant can prepare and fill reviewed answers for portals such as Workday while keeping the user in control of every account creation and submission.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the ordered implementation plan, privacy boundaries, salary guidance design, and later email integration.
