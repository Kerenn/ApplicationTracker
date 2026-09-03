# Job Application Tracker

A small, professional, local-first tracker for personal job applications on macOS. SQLite is the source of truth; the web UI runs only on your computer.

## Version 1 features

- Add a job from a URL with best-effort JSON-LD/OpenGraph extraction
- Always review extracted fields before saving
- Duplicate URL warnings
- Manual application creation and editing
- Board view with quick status moves and detailed pipeline stages
- Manual activity timeline for replies, calls, follow-ups, and interviews
- Action-needed flags for incoming messages that require a response
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
