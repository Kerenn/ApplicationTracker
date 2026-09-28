from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import (
    PersonalProfile,
    ProfileAnswer,
    ProfileEducation,
    ProfileExperience,
    ProfileProject,
)
from app.services.applications import clean, parse_date
from app.web import templates


router = APIRouter(prefix="/profile")

PROFILE_FIELDS = (
    "preferred_name",
    "legal_name",
    "email",
    "phone",
    "address_line_1",
    "address_line_2",
    "postal_code",
    "city",
    "country",
    "linkedin_url",
    "github_url",
    "portfolio_url",
    "professional_summary",
    "work_authorization",
    "notice_period",
    "willing_to_relocate",
    "willing_to_travel",
    "driving_licence",
    "skills",
    "languages",
    "certifications",
)


def _profile(session: Session, create: bool = False) -> PersonalProfile:
    profile = session.get(PersonalProfile, 1)
    if profile is None:
        profile = PersonalProfile(id=1)
        if create:
            session.add(profile)
            session.flush()
    return profile


def _optional_bool(value: object | None) -> bool | None:
    normalized = clean(value)
    if normalized == "yes":
        return True
    if normalized == "no":
        return False
    return None


def _completion(profile: PersonalProfile) -> list[dict[str, object]]:
    sections = [
        ("Contact", bool(profile.preferred_name or profile.legal_name) and bool(profile.email)),
        ("Location", bool(profile.city and profile.country)),
        ("Work eligibility", bool(profile.work_authorization)),
        ("Professional summary", bool(profile.professional_summary)),
        ("Skills and languages", bool(profile.skills and profile.languages)),
        ("Experience", bool(profile.experiences)),
        ("Education", bool(profile.educations)),
        ("Reusable answers", bool(profile.answers)),
    ]
    return [{"label": label, "complete": complete} for label, complete in sections]


def _owned(session: Session, model, item_id: int):
    item = session.get(model, item_id)
    if item is None or item.profile_id != 1:
        raise HTTPException(status_code=404, detail="Profile item not found")
    return item


@router.get("", name="profile")
def profile_page(request: Request, session: Session = Depends(get_session)):
    profile = _profile(session)
    completion = _completion(profile)
    completed = sum(1 for item in completion if item["complete"])
    completion_percent = (completed * 100 + len(completion) // 2) // len(completion)
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "profile": profile,
            "completion": completion,
            "completion_percent": completion_percent,
            "saved": request.query_params.get("saved"),
        },
    )


@router.post("", name="profile_update")
async def profile_update(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    profile = _profile(session, create=True)
    for field in PROFILE_FIELDS:
        setattr(profile, field, clean(form.get(field)))
    profile.sponsorship_required = _optional_bool(form.get("sponsorship_required"))
    session.commit()
    return RedirectResponse("/profile?saved=profile", status_code=303)


@router.post("/experiences", name="profile_experience_create")
async def experience_create(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    employer = clean(form.get("employer"))
    title = clean(form.get("title"))
    if not employer or not title:
        raise HTTPException(status_code=422, detail="Employer and title are required")
    profile = _profile(session, create=True)
    profile.experiences.append(ProfileExperience(employer=employer, title=title))
    item = profile.experiences[-1]
    _apply_experience(item, form)
    session.commit()
    return RedirectResponse("/profile?saved=experience#experience", status_code=303)


def _apply_experience(item: ProfileExperience, form) -> None:
    item.employer = clean(form.get("employer")) or item.employer
    item.title = clean(form.get("title")) or item.title
    item.location = clean(form.get("location"))
    item.start_date = parse_date(form.get("start_date"))
    item.current = form.get("current") == "on"
    item.end_date = None if item.current else parse_date(form.get("end_date"))
    item.responsibilities = clean(form.get("responsibilities"))
    item.achievements = clean(form.get("achievements"))
    item.technologies = clean(form.get("technologies"))


@router.post("/experiences/{item_id}", name="profile_experience_update")
async def experience_update(item_id: int, request: Request, session: Session = Depends(get_session)):
    item = _owned(session, ProfileExperience, item_id)
    form = await request.form()
    _apply_experience(item, form)
    session.commit()
    return RedirectResponse("/profile?saved=experience#experience", status_code=303)


@router.post("/experiences/{item_id}/delete", name="profile_experience_delete")
def experience_delete(item_id: int, session: Session = Depends(get_session)):
    session.delete(_owned(session, ProfileExperience, item_id))
    session.commit()
    return RedirectResponse("/profile#experience", status_code=303)


def _apply_education(item: ProfileEducation, form) -> None:
    item.institution = clean(form.get("institution")) or item.institution
    item.degree = clean(form.get("degree")) or item.degree
    item.field_of_study = clean(form.get("field_of_study"))
    item.location = clean(form.get("location"))
    item.start_date = parse_date(form.get("start_date"))
    item.end_date = parse_date(form.get("end_date"))
    item.grade = clean(form.get("grade"))
    item.notes = clean(form.get("notes"))


@router.post("/educations", name="profile_education_create")
async def education_create(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    institution = clean(form.get("institution"))
    degree = clean(form.get("degree"))
    if not institution or not degree:
        raise HTTPException(status_code=422, detail="Institution and degree are required")
    profile = _profile(session, create=True)
    item = ProfileEducation(institution=institution, degree=degree)
    _apply_education(item, form)
    profile.educations.append(item)
    session.commit()
    return RedirectResponse("/profile?saved=education#education", status_code=303)


@router.post("/educations/{item_id}", name="profile_education_update")
async def education_update(item_id: int, request: Request, session: Session = Depends(get_session)):
    item = _owned(session, ProfileEducation, item_id)
    form = await request.form()
    _apply_education(item, form)
    session.commit()
    return RedirectResponse("/profile?saved=education#education", status_code=303)


@router.post("/educations/{item_id}/delete", name="profile_education_delete")
def education_delete(item_id: int, session: Session = Depends(get_session)):
    session.delete(_owned(session, ProfileEducation, item_id))
    session.commit()
    return RedirectResponse("/profile#education", status_code=303)


def _apply_project(item: ProfileProject, form) -> None:
    item.name = clean(form.get("name")) or item.name
    item.role = clean(form.get("role"))
    item.project_url = clean(form.get("project_url"))
    item.start_date = parse_date(form.get("start_date"))
    item.end_date = parse_date(form.get("end_date"))
    item.description = clean(form.get("description"))
    item.impact = clean(form.get("impact"))
    item.technologies = clean(form.get("technologies"))


@router.post("/projects", name="profile_project_create")
async def project_create(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    name = clean(form.get("name"))
    if not name:
        raise HTTPException(status_code=422, detail="Project name is required")
    profile = _profile(session, create=True)
    item = ProfileProject(name=name)
    _apply_project(item, form)
    profile.projects.append(item)
    session.commit()
    return RedirectResponse("/profile?saved=project#projects", status_code=303)


@router.post("/projects/{item_id}", name="profile_project_update")
async def project_update(item_id: int, request: Request, session: Session = Depends(get_session)):
    item = _owned(session, ProfileProject, item_id)
    form = await request.form()
    _apply_project(item, form)
    session.commit()
    return RedirectResponse("/profile?saved=project#projects", status_code=303)


@router.post("/projects/{item_id}/delete", name="profile_project_delete")
def project_delete(item_id: int, session: Session = Depends(get_session)):
    session.delete(_owned(session, ProfileProject, item_id))
    session.commit()
    return RedirectResponse("/profile#projects", status_code=303)


def _apply_answer(item: ProfileAnswer, form) -> None:
    item.category = clean(form.get("category")) or "Other"
    item.question = clean(form.get("question")) or item.question
    item.answer = clean(form.get("answer")) or item.answer
    item.notes = clean(form.get("notes"))


@router.post("/answers", name="profile_answer_create")
async def answer_create(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    question = clean(form.get("question"))
    answer = clean(form.get("answer"))
    if not question or not answer:
        raise HTTPException(status_code=422, detail="Question and answer are required")
    profile = _profile(session, create=True)
    item = session.scalar(
        select(ProfileAnswer).where(
            ProfileAnswer.profile_id == profile.id,
            ProfileAnswer.question == question,
        )
    )
    if item is None:
        item = ProfileAnswer(question=question, answer=answer)
        profile.answers.append(item)
    _apply_answer(item, form)
    session.commit()
    return RedirectResponse("/profile?saved=answer#answers", status_code=303)


@router.post("/answers/{item_id}", name="profile_answer_update")
async def answer_update(item_id: int, request: Request, session: Session = Depends(get_session)):
    item = _owned(session, ProfileAnswer, item_id)
    form = await request.form()
    _apply_answer(item, form)
    session.commit()
    return RedirectResponse("/profile?saved=answer#answers", status_code=303)


@router.post("/answers/{item_id}/delete", name="profile_answer_delete")
def answer_delete(item_id: int, session: Session = Depends(get_session)):
    session.delete(_owned(session, ProfileAnswer, item_id))
    session.commit()
    return RedirectResponse("/profile#answers", status_code=303)
