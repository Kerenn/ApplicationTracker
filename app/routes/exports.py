from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_session
from app.services.exporter import build_csv, build_xlsx


router = APIRouter(prefix="/exports")


@router.get("/applications.csv")
def export_csv(session: Session = Depends(get_session)):
    return Response(
        build_csv(session),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="job-applications.csv"'},
    )


@router.get("/job-tracker.xlsx")
def export_xlsx(session: Session = Depends(get_session)):
    return Response(
        build_xlsx(session),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="job-tracker.xlsx"'},
    )
