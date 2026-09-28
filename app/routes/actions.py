from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.constants import ApplicationStatus
from app.database import get_session
from app.models import Application, ApplicationActivity
from app.web import templates


router = APIRouter()
TERMINAL_STATUSES = (
    ApplicationStatus.REJECTED.value,
    ApplicationStatus.WITHDRAWN.value,
)


@router.get("/actions", name="action_inbox")
def action_inbox(request: Request, session: Session = Depends(get_session)):
    needs_response = list(
        session.scalars(
            select(ApplicationActivity)
            .where(
                ApplicationActivity.needs_action.is_(True),
                ApplicationActivity.action_completed.is_(False),
            )
            .options(selectinload(ApplicationActivity.application))
            .order_by(ApplicationActivity.occurred_at.asc())
        )
    )
    due_follow_ups = list(
        session.scalars(
            select(Application)
            .where(
                Application.follow_up_date.is_not(None),
                Application.follow_up_date <= date.today(),
                Application.status.not_in(TERMINAL_STATUSES),
            )
            .order_by(Application.follow_up_date.asc(), Application.priority.asc())
        )
    )
    upcoming_interviews = list(
        session.scalars(
            select(ApplicationActivity)
            .where(
                ApplicationActivity.activity_type == "Interview",
                ApplicationActivity.scheduled_at.is_not(None),
                ApplicationActivity.scheduled_at >= datetime.now(timezone.utc),
            )
            .options(selectinload(ApplicationActivity.application))
            .order_by(ApplicationActivity.scheduled_at.asc())
        )
    )
    missing_next_action = list(
        session.scalars(
            select(Application)
            .where(
                Application.status.not_in(TERMINAL_STATUSES),
                (Application.next_action.is_(None) | (Application.next_action == "")),
            )
            .order_by(Application.updated_at.desc())
            .limit(20)
        )
    )
    return templates.TemplateResponse(
        request=request,
        name="actions.html",
        context={
            "needs_response": needs_response,
            "due_follow_ups": due_follow_ups,
            "upcoming_interviews": upcoming_interviews,
            "missing_next_action": missing_next_action,
            "today": date.today(),
        },
    )
