from io import BytesIO

from openpyxl import Workbook, load_workbook

from app.models import Application
from app.services.applications import apply_application_form
from app.services.exporter import build_csv, build_xlsx
from app.services.workbook_importer import preview_workbook
from tests.test_applications import application_form


def test_exports_are_readable(session):
    apply_application_form(session, Application(), application_form())

    csv_data = build_csv(session).decode("utf-8-sig")
    assert "Example Robotics" in csv_data
    assert "Computer Vision" in csv_data

    workbook = load_workbook(BytesIO(build_xlsx(session)))
    assert workbook.sheetnames == ["Applications", "Requirements", "Documents", "Status History", "Activities"]
    assert workbook["Applications"]["B2"].value == "Example Robotics"
    workbook.close()


def test_workbook_preview_does_not_import_and_flags_ambiguity(tmp_path):
    path = tmp_path / "source.xlsm"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Applications"
    sheet.append(["App ID", "Company", "Role", "Track", "Status", "Days Since Applied"])
    sheet.append(["APP-001", "Example", "Engineer", "Embedded/Electronics", "Recruiter Screen", 10])
    workbook.create_sheet("Cover Letters").append(["Application ID", "Company"])
    workbook.save(path)

    preview = preview_workbook(path)
    assert preview.rows[0].direct["company"] == "Example"
    assert preview.rows[0].unresolved["Track"] == "Embedded/Electronics"
    assert preview.rows[0].direct["status"] == "Interview"
    assert preview.rows[0].direct["pipeline_stage"] == "Recruiter screen"
    assert any("Days Since Applied" in warning for warning in preview.warnings)
