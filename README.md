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
- A structured local profile for contact details, work eligibility, skills, languages, experience, education, projects, and reusable answers

## Run locally on macOS

Python 3.11 or newer is required.

### First-time setup

```bash
cd /Users/Eren/DevProjects/TrackerJob
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

### Start the application

Run these commands whenever you want to use the tracker:

```bash
cd /Users/Eren/DevProjects/TrackerJob
source .venv/bin/activate
uvicorn app.main:app --reload
```

Keep that Terminal window open and visit <http://127.0.0.1:8000>. Stop the server with `Control-C`.

If port 8000 is already occupied, use another port:

```bash
uvicorn app.main:app --reload --port 8001
```

Then open <http://127.0.0.1:8001>.

### Update after pulling new code

```bash
cd /Users/Eren/DevProjects/TrackerJob
git pull
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload
```

The default database is `data/tracker.sqlite`. Override it with `JOB_TRACKER_DATABASE_URL` if needed; see `.env.example`.

Your applications and profile are not inside Git. Before a major update, copy `data/tracker.sqlite` somewhere safe or download an Excel export from the dashboard.

## Tests

```bash
pytest
```

## Privacy

The database, import directory, private data, exports, PDFs, and personal document folders are ignored by Git. The app stores document paths and metadata only—it does not copy CVs, cover letters, certificates, or transcripts into this repository.

The workbook import screen is preview-only. It does not write source rows into SQLite.

## Next phase

The structured local profile is now available at <http://127.0.0.1:8000/profile>. The next capability is a per-application form pack that selects relevant profile material, identifies missing answers, and preserves exactly what was used for each application. A later browser assistant can prepare and fill reviewed answers for portals such as Workday while keeping the user in control of every account creation and submission.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the ordered implementation plan, privacy boundaries, salary guidance design, and later email integration.
