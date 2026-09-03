from fastapi import APIRouter, Request

from app.services.workbook_importer import preview_workbook
from app.web import templates


router = APIRouter(prefix="/imports")
DEFAULT_IMPORT_PATH = "data/import/Job_Application_Tracker_Kadir_Eren_Unal.xlsm"


@router.get("")
def import_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="imports.html",
        context={"preview": None, "error": None, "path": DEFAULT_IMPORT_PATH},
    )


@router.post("/preview")
async def import_preview(request: Request):
    form = await request.form()
    path = str(form.get("path", DEFAULT_IMPORT_PATH)).strip()
    try:
        preview = preview_workbook(path)
        error = None
    except ValueError as exc:
        preview = None
        error = str(exc)
    return templates.TemplateResponse(
        request=request,
        name="imports.html",
        context={"preview": preview, "error": error, "path": path},
    )
