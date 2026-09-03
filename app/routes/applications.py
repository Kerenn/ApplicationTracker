from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import case, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.constants import ACTIVITY_DIRECTIONS, ACTIVITY_TYPES, ApplicationStatus, Priority
from app.database import get_session
from app.models import (
    Application,
    ApplicationActivity,
    ApplicationRequirement,
    Document,
    Tag,
)
from app.services.applications import (
    apply_application_form,
    change_application_status,
    find_duplicate,
    parse_date,
    parse_datetime,
)
from app.services.job_extractor import extract_job
from app.web import templates


router = APIRouter()


def _application_query():
    return select(Application).options(
        selectinload(Application.tags),
        selectinload(Application.requirements),
        selectinload(Application.documents),
        selectinload(Application.status_history),
        selectinload(Application.activities),
    )


def _get_application(session: Session, application_id: int) -> Application:
    application = session.scalar(
        _application_query().where(Application.id == application_id)
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.get("/applications", name="application_list")
def application_list(request: Request, session: Session = Depends(get_session)):
    params = request.query_params
    query = select(Application).options(selectinload(Application.tags))
    search = params.get("search", "").strip()
    if search:
        term = f"%{search}%"
        query = query.where(
            or_(
                Application.company.ilike(term),
                Application.role.ilike(term),
                Application.tags.any(Tag.name.ilike(term)),
            )
        )
    for key, column in (
        ("status", Application.status),
        ("track", Application.primary_track),
        ("priority", Application.priority),
    ):
        value = params.get(key, "").strip()
        if value:
            query = query.where(column == value)
    company = params.get("company", "").strip()
    if company:
        query = query.where(Application.company.ilike(f"%{company}%"))
    location = params.get("location", "").strip()
    if location:
        query = query.where(Application.location.ilike(f"%{location}%"))

    sort = params.get("sort", "newest")
    if sort == "priority":
        priority_order = case(
            (Application.priority == Priority.HIGH.value, 1),
            (Application.priority == Priority.MEDIUM.value, 2),
            else_=3,
        )
        query = query.order_by(priority_order, Application.date_found.desc())
    elif sort == "fit":
        query = query.order_by(Application.fit_score.desc().nullslast())
    elif sort == "applied":
        query = query.order_by(Application.applied_date.desc().nullslast())
    else:
        query = query.order_by(Application.date_found.desc(), Application.id.desc())

    applications = list(session.scalars(query))
    return templates.TemplateResponse(
        request=request,
        name="applications/list.html",
        context={"applications": applications, "filters": dict(params)},
    )


@router.get("/applications/new", name="application_new")
def application_new(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="applications/form.html",
        context={"application": None, "values": {}, "warning": None, "duplicate": None},
    )


@router.post("/applications/preview-url", name="application_preview_url")
async def application_preview_url(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    job_url = str(form.get("job_url", "")).strip()
    result = await extract_job(job_url)
    duplicate = find_duplicate(session, job_url)
    return templates.TemplateResponse(
        request=request,
        name="applications/form.html",
        context={
            "application": None,
            "values": result.to_dict(),
            "warning": result.warning,
            "duplicate": duplicate,
        },
    )


@router.post("/applications", name="application_create")
async def application_create(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    duplicate = find_duplicate(session, form.get("job_url"))
    if duplicate:
        return RedirectResponse(f"/applications/{duplicate.id}?duplicate=1", status_code=303)
    try:
        application = apply_application_form(session, Application(), form)
    except IntegrityError:
        session.rollback()
        duplicate = find_duplicate(session, form.get("job_url"))
        if duplicate:
            return RedirectResponse(f"/applications/{duplicate.id}?duplicate=1", status_code=303)
        raise
    return RedirectResponse(f"/applications/{application.id}", status_code=303)


@router.get("/applications/{application_id}", name="application_detail")
def application_detail(application_id: int, request: Request, session: Session = Depends(get_session)):
    application = _get_application(session, application_id)
    return templates.TemplateResponse(
        request=request,
        name="applications/detail.html",
        context={"application": application, "duplicate": request.query_params.get("duplicate")},
    )


@router.get("/applications/{application_id}/edit", name="application_edit")
def application_edit(application_id: int, request: Request, session: Session = Depends(get_session)):
    application = _get_application(session, application_id)
    return templates.TemplateResponse(
        request=request,
        name="applications/form.html",
        context={"application": application, "values": {}, "warning": None, "duplicate": None},
    )


@router.post("/applications/{application_id}", name="application_update")
async def application_update(application_id: int, request: Request, session: Session = Depends(get_session)):
    application = _get_application(session, application_id)
    form = await request.form()
    duplicate = find_duplicate(session, form.get("job_url"))
    if duplicate and duplicate.id != application.id:
        return templates.TemplateResponse(
            request=request,
            name="applications/form.html",
            status_code=409,
            context={
                "application": application,
                "values": dict(form),
                "warning": "That job URL already belongs to another application.",
                "duplicate": duplicate,
            },
        )
    apply_application_form(session, application, form)
    return RedirectResponse(f"/applications/{application.id}", status_code=303)


@router.post("/applications/{application_id}/quick-status")
async def application_quick_status(
    application_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    application = _get_application(session, application_id)
    form = await request.form()
    change_application_status(
        session,
        application,
        form.get("status"),
        form.get("pipeline_stage"),
    )
    session.commit()
    return_to = str(form.get("return_to", f"/applications/{application_id}"))
    if not return_to.startswith("/") or return_to.startswith("//"):
        return_to = f"/applications/{application_id}"
    return RedirectResponse(return_to, status_code=303)


@router.post("/applications/{application_id}/activities")
async def activity_create(
    application_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    application = _get_application(session, application_id)
    form = await request.form()
    activity_type = str(form.get("activity_type", "Note"))
    direction = str(form.get("direction", "Internal"))
    summary = str(form.get("summary", "")).strip()
    if summary:
        stage = form.get("pipeline_stage")
        change_application_status(session, application, form.get("status"), stage)
        next_action = str(form.get("next_action", "")).strip()
        if next_action:
            application.next_action = next_action
        follow_up_date = parse_date(form.get("follow_up_date"))
        if follow_up_date:
            application.follow_up_date = follow_up_date
        session.add(
            ApplicationActivity(
                application=application,
                activity_type=activity_type if activity_type in ACTIVITY_TYPES else "Note",
                direction=direction if direction in ACTIVITY_DIRECTIONS else "Internal",
                occurred_at=parse_datetime(form.get("occurred_at")),
                summary=summary,
                notes=str(form.get("notes", "")).strip() or None,
                interview_stage=(
                    application.pipeline_stage
                    if application.status == ApplicationStatus.INTERVIEW.value
                    else None
                ),
                needs_action=form.get("needs_action") == "on",
            )
        )
        session.commit()
    return RedirectResponse(f"/applications/{application_id}#activity", status_code=303)


@router.post("/activities/{activity_id}/toggle-action")
def activity_toggle_action(activity_id: int, session: Session = Depends(get_session)):
    activity = session.get(ApplicationActivity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    activity.action_completed = not activity.action_completed
    session.commit()
    return RedirectResponse(f"/applications/{activity.application_id}#activity", status_code=303)


@router.post("/applications/{application_id}/requirements")
async def requirement_create(application_id: int, request: Request, session: Session = Depends(get_session)):
    application = _get_application(session, application_id)
    form = await request.form()
    item = ApplicationRequirement(
        application=application,
        name=str(form.get("name", "")).strip(),
        category=str(form.get("category", "Other")),
        required=form.get("required") == "on",
        completed=form.get("completed") == "on",
        value=str(form.get("value", "")).strip() or None,
        notes=str(form.get("notes", "")).strip() or None,
        sort_order=len(application.requirements),
    )
    if item.name:
        session.add(item)
        session.commit()
    return RedirectResponse(f"/applications/{application_id}#requirements", status_code=303)


@router.post("/requirements/{requirement_id}/toggle")
def requirement_toggle(requirement_id: int, session: Session = Depends(get_session)):
    item = session.get(ApplicationRequirement, requirement_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    item.completed = not item.completed
    session.commit()
    return RedirectResponse(f"/applications/{item.application_id}#requirements", status_code=303)


@router.post("/requirements/{requirement_id}")
async def requirement_update(requirement_id: int, request: Request, session: Session = Depends(get_session)):
    item = session.get(ApplicationRequirement, requirement_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    form = await request.form()
    name = str(form.get("name", "")).strip()
    if name:
        item.name = name
    item.category = str(form.get("category", "Other"))
    item.required = form.get("required") == "on"
    item.completed = form.get("completed") == "on"
    item.value = str(form.get("value", "")).strip() or None
    item.notes = str(form.get("notes", "")).strip() or None
    session.commit()
    return RedirectResponse(f"/applications/{item.application_id}#requirements", status_code=303)


@router.post("/requirements/{requirement_id}/delete")
def requirement_delete(requirement_id: int, session: Session = Depends(get_session)):
    item = session.get(ApplicationRequirement, requirement_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    application_id = item.application_id
    session.delete(item)
    session.commit()
    return RedirectResponse(f"/applications/{application_id}#requirements", status_code=303)


@router.post("/applications/{application_id}/documents")
async def document_create(application_id: int, request: Request, session: Session = Depends(get_session)):
    application = _get_application(session, application_id)
    form = await request.form()
    document = Document(
        application=application,
        document_type=str(form.get("document_type", "Other")),
        local_path=str(form.get("local_path", "")).strip() or None,
        cloud_url=str(form.get("cloud_url", "")).strip() or None,
        version=str(form.get("version", "")).strip() or None,
        notes=str(form.get("notes", "")).strip() or None,
    )
    session.add(document)
    session.commit()
    return RedirectResponse(f"/applications/{application_id}#documents", status_code=303)


@router.get("/documents/{document_id}/open")
def document_open(document_id: int, session: Session = Depends(get_session)):
    document = session.get(Document, document_id)
    if document is None or not document.local_path:
        raise HTTPException(status_code=404, detail="Local document not found")
    path = Path(document.local_path).expanduser()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Local document not found")
    return FileResponse(path)


@router.post("/documents/{document_id}")
async def document_update(document_id: int, request: Request, session: Session = Depends(get_session)):
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    form = await request.form()
    document.document_type = str(form.get("document_type", "Other"))
    document.local_path = str(form.get("local_path", "")).strip() or None
    document.cloud_url = str(form.get("cloud_url", "")).strip() or None
    document.version = str(form.get("version", "")).strip() or None
    document.notes = str(form.get("notes", "")).strip() or None
    session.commit()
    return RedirectResponse(f"/applications/{document.application_id}#documents", status_code=303)


@router.post("/documents/{document_id}/delete")
def document_delete(document_id: int, session: Session = Depends(get_session)):
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    application_id = document.application_id
    session.delete(document)
    session.commit()
    return RedirectResponse(f"/applications/{application_id}#documents", status_code=303)
