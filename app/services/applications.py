from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import (
    PIPELINE_STAGES,
    ApplicationStatus,
    PrimaryTrack,
    Priority,
    enum_values,
)
from app.models import Application, StatusHistory, Tag


TRACKS = enum_values(PrimaryTrack)
STATUSES = enum_values(ApplicationStatus)
PRIORITIES = enum_values(Priority)


def clean(value: object | None) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def parse_date(value: object | None) -> date | None:
    text = clean(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def parse_score(value: object | None) -> float | None:
    text = clean(value)
    if not text:
        return None
    try:
        score = float(text)
    except ValueError:
        return None
    return score if 0 <= score <= 10 else None


def parse_datetime(value: object | None) -> datetime:
    text_value = clean(value)
    if not text_value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(text_value)
    except ValueError:
        return datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def default_stage(status: str) -> str | None:
    stages = PIPELINE_STAGES.get(status, ())
    return stages[0] if stages else None


def valid_stage(status: str, stage: object | None) -> str | None:
    requested = clean(stage)
    allowed = PIPELINE_STAGES.get(status, ())
    return requested if requested in allowed else default_stage(status)


def normalize_url(value: object | None) -> str | None:
    url = clean(value)
    if not url:
        return None
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return url
    filtered_query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"fbclid", "gclid", "ref", "source"}
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, urlencode(filtered_query), "")
    )


def find_duplicate(session: Session, job_url: object | None) -> Application | None:
    normalized = normalize_url(job_url)
    if not normalized:
        return None
    return session.scalar(
        select(Application).where(Application.normalized_job_url == normalized)
    )


def _set_tags(session: Session, application: Application, raw_tags: object | None) -> None:
    names = []
    for name in str(raw_tags or "").split(","):
        normalized = name.strip()
        if normalized and normalized.casefold() not in {item.casefold() for item in names}:
            names.append(normalized)

    application.tags.clear()
    for name in names:
        tag = session.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name)
            session.add(tag)
        application.tags.append(tag)


def apply_application_form(
    session: Session,
    application: Application,
    form: Mapping[str, object],
) -> Application:
    is_new = application.id is None
    previous_status = application.status if not is_new else None
    if is_new:
        session.add(application)

    application.company = clean(form.get("company")) or ""
    application.role = clean(form.get("role")) or ""
    application.job_url = clean(form.get("job_url"))
    application.normalized_job_url = normalize_url(application.job_url)
    application.application_url = clean(form.get("application_url"))
    application.source = clean(form.get("source"))
    application.location = clean(form.get("location"))
    application.work_mode = clean(form.get("work_mode"))
    application.employment_type = clean(form.get("employment_type"))
    application.contact = clean(form.get("contact"))

    track = clean(form.get("primary_track"))
    application.primary_track = track if track in TRACKS else PrimaryTrack.OTHER.value
    status = clean(form.get("status"))
    application.status = status if status in STATUSES else ApplicationStatus.SAVED.value
    application.pipeline_stage = valid_stage(
        application.status, form.get("pipeline_stage")
    )
    priority = clean(form.get("priority"))
    application.priority = priority if priority in PRIORITIES else Priority.MEDIUM.value
    application.fit_score = parse_score(form.get("fit_score"))

    application.date_found = parse_date(form.get("date_found")) or date.today()
    application.applied_date = parse_date(form.get("applied_date"))
    if application.status == ApplicationStatus.APPLIED.value and application.applied_date is None:
        application.applied_date = date.today()
    application.application_deadline = parse_date(form.get("application_deadline"))
    application.follow_up_date = parse_date(form.get("follow_up_date"))
    application.interview_date = parse_date(form.get("interview_date"))

    application.salary_expectation = clean(form.get("salary_expectation"))
    application.salary_notes = clean(form.get("salary_notes"))
    application.cv_version = clean(form.get("cv_version"))
    application.next_action = clean(form.get("next_action"))
    application.notes = clean(form.get("notes"))
    _set_tags(session, application, form.get("tags"))

    if is_new:
        session.flush()
        session.add(StatusHistory(application=application, to_status=application.status))
    elif previous_status != application.status:
        session.add(
            StatusHistory(
                application=application,
                from_status=previous_status,
                to_status=application.status,
            )
        )
    session.commit()
    session.refresh(application)
    return application


def change_application_status(
    session: Session,
    application: Application,
    status: object | None,
    stage: object | None = None,
) -> None:
    requested_status = clean(status)
    new_status = requested_status if requested_status in STATUSES else application.status
    previous_status = application.status
    application.status = new_status
    application.pipeline_stage = valid_stage(new_status, stage)
    if new_status == ApplicationStatus.APPLIED.value and application.applied_date is None:
        application.applied_date = date.today()
    if previous_status != new_status:
        session.add(
            StatusHistory(
                application=application,
                from_status=previous_status,
                to_status=new_status,
            )
        )
