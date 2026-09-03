from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.constants import ApplicationStatus, PrimaryTrack, enum_values
from app.database import get_session
from app.models import Application, ApplicationActivity
from app.web import templates


router = APIRouter()


@router.get("/", name="dashboard")
def dashboard(request: Request, session: Session = Depends(get_session)):
    status_counts = dict(
        session.execute(
            select(Application.status, func.count(Application.id)).group_by(Application.status)
        ).all()
    )
    track_counts = dict(
        session.execute(
            select(Application.primary_track, func.count(Application.id)).group_by(
                Application.primary_track
            )
        ).all()
    )
    terminal = {
        ApplicationStatus.OFFER.value,
        ApplicationStatus.REJECTED.value,
        ApplicationStatus.WITHDRAWN.value,
    }
    follow_ups_due = session.scalar(
        select(func.count(Application.id)).where(
            Application.follow_up_date.is_not(None),
            Application.follow_up_date <= date.today(),
            Application.status.not_in(terminal),
        )
    ) or 0
    replies_needing_action = session.scalar(
        select(func.count(ApplicationActivity.id)).where(
            ApplicationActivity.needs_action.is_(True),
            ApplicationActivity.action_completed.is_(False),
        )
    ) or 0
    recent = list(
        session.scalars(
            select(Application)
            .options(selectinload(Application.tags))
            .options(selectinload(Application.activities))
            .order_by(Application.date_found.desc(), Application.id.desc())
            .limit(10)
        )
    )
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "status_counts": status_counts,
            "track_counts": track_counts,
            "status_labels": enum_values(ApplicationStatus),
            "track_labels": enum_values(PrimaryTrack),
            "follow_ups_due": follow_ups_due,
            "replies_needing_action": replies_needing_action,
            "total": sum(status_counts.values()),
            "recent": recent,
        },
    )
