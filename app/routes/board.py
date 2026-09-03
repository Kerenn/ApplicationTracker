from fastapi import APIRouter, Depends, Request
from sqlalchemy import case, select
from sqlalchemy.orm import Session, selectinload

from app.constants import ApplicationStatus
from app.database import get_session
from app.models import Application
from app.web import templates


router = APIRouter()
ACTIVE_STATUSES = (
    ApplicationStatus.SAVED.value,
    ApplicationStatus.PREPARING.value,
    ApplicationStatus.APPLYING.value,
    ApplicationStatus.APPLIED.value,
    ApplicationStatus.INTERVIEW.value,
    ApplicationStatus.OFFER.value,
)
TERMINAL_STATUSES = (
    ApplicationStatus.REJECTED.value,
    ApplicationStatus.WITHDRAWN.value,
)


@router.get("/board", name="application_board")
def application_board(request: Request, session: Session = Depends(get_session)):
    priority_order = case(
        (Application.priority == "High", 1),
        (Application.priority == "Medium", 2),
        else_=3,
    )
    applications = list(
        session.scalars(
            select(Application)
            .options(
                selectinload(Application.tags),
                selectinload(Application.activities),
            )
            .order_by(priority_order, Application.updated_at.desc())
        )
    )
    columns = {
        status: [application for application in applications if application.status == status]
        for status in ACTIVE_STATUSES
    }
    terminal = [
        application for application in applications if application.status in TERMINAL_STATUSES
    ]
    return templates.TemplateResponse(
        request=request,
        name="board.html",
        context={
            "columns": columns,
            "active_statuses": ACTIVE_STATUSES,
            "terminal": terminal,
        },
    )
