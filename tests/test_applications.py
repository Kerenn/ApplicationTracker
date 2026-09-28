from datetime import date, timedelta

from sqlalchemy import select

from app.models import Application, ApplicationActivity, ApplicationRequirement
from app.services.applications import (
    apply_application_form,
    change_application_status,
    find_duplicate,
)
from app.services.job_extractor import ExtractionResult


def application_form(**overrides):
    values = {
        "company": "Example Robotics",
        "role": "Perception Engineer",
        "job_url": "https://example.com/jobs/42?utm_source=newsletter",
        "primary_track": "Robotics",
        "tags": "Software, AI/ML, Computer Vision",
        "status": "Saved",
        "priority": "High",
        "fit_score": "8.5",
        "date_found": "2026-09-03",
    }
    values.update(overrides)
    return values


def test_application_creation_tags_history_and_duplicate_detection(session):
    application = apply_application_form(session, Application(), application_form())

    assert application.company == "Example Robotics"
    assert {tag.name for tag in application.tags} == {"Software", "AI/ML", "Computer Vision"}
    assert application.status_history[0].to_status == "Saved"
    assert application.pipeline_stage == "Saved"
    assert find_duplicate(session, "https://example.com/jobs/42") == application


def test_status_change_records_history_and_applied_date(session):
    application = apply_application_form(session, Application(), application_form())
    apply_application_form(session, application, application_form(status="Applied"))

    assert application.applied_date == date.today()
    assert [event.to_status for event in application.status_history] == ["Applied", "Saved"]


def test_lifecycle_dates_advance_status_automatically(session):
    application = apply_application_form(session, Application(), application_form())
    apply_application_form(
        session,
        application,
        application_form(status="Preparing", applied_date="2026-09-10"),
    )
    assert application.status == "Applied"
    assert application.pipeline_stage == "Submitted"

    apply_application_form(
        session,
        application,
        application_form(
            status="Applied",
            applied_date="2026-09-10",
            interview_date="2026-09-18",
        ),
    )
    assert application.status == "Interview"
    assert application.pipeline_stage == "Recruiter screen"


def test_ready_requires_at_least_one_required_completed_item(session):
    application = apply_application_form(session, Application(), application_form())
    assert application.is_ready_to_apply is False

    application.requirements.append(
        ApplicationRequirement(name="CV", category="Document", required=True, completed=True)
    )
    session.commit()
    assert application.is_ready_to_apply is True

    application.requirements.append(
        ApplicationRequirement(name="Salary", category="Salary", required=True, completed=False)
    )
    session.commit()
    assert application.is_ready_to_apply is False


def test_quick_status_move_sets_a_useful_default_stage(session):
    application = apply_application_form(session, Application(), application_form())
    change_application_status(session, application, "Interview", "Technical interview")
    session.commit()

    assert application.status == "Interview"
    assert application.pipeline_stage == "Technical interview"
    assert application.status_history[0].to_status == "Interview"


def test_application_routes_create_and_filter(client):
    response = client.post("/applications", data=application_form(), follow_redirects=True)
    assert response.status_code == 200
    assert "Example Robotics" in response.text
    assert "Perception Engineer" in response.text

    response = client.get("/applications", params={"search": "Computer Vision"})
    assert response.status_code == 200
    assert "Example Robotics" in response.text


def test_board_status_post_persists_status_and_stage(client, session):
    client.post("/applications", data=application_form())
    application = session.scalar(select(Application))

    response = client.post(
        f"/applications/{application.id}/quick-status",
        data={"status": "Applied", "return_to": "/board"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert application.status == "Applied"
    assert application.pipeline_stage == "Submitted"
    assert application.applied_date == date.today()


def test_company_and_role_are_required(client, session):
    response = client.post(
        "/applications",
        data=application_form(company="", role=""),
    )
    assert response.status_code == 422
    assert "Complete the required fields: Company, Role" in response.text
    assert session.scalar(select(Application)) is None


def test_url_preview_shows_found_missing_and_confirmation_fields(client, monkeypatch):
    async def fake_extract(_url):
        return ExtractionResult(
            job_url="https://jobs.example/42",
            company="Example Robotics",
            role="FPGA Engineer",
            location=None,
        )

    monkeypatch.setattr("app.routes.applications.extract_job", fake_extract)
    response = client.post(
        "/applications/preview-url",
        data={"job_url": "https://jobs.example/42"},
    )
    assert response.status_code == 200
    assert "Check the extracted job details" in response.text
    assert "Confirm this value" in response.text
    assert "Location" in response.text
    assert "Missing" in response.text


def test_activity_can_move_stage_and_surface_on_board(client, session):
    client.post("/applications", data=application_form())
    application = session.scalar(select(Application))

    response = client.post(
        f"/applications/{application.id}/activities",
        data={
            "activity_type": "Email",
            "direction": "Incoming",
            "summary": "Recruiter invited me to a technical interview",
            "status": "Interview",
            "pipeline_stage": "Technical interview",
            "needs_action": "on",
            "next_action": "Reply with available time slots",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Recruiter invited me to a technical interview" in response.text
    assert "1 needs action" in response.text
    assert application.status == "Interview"
    assert application.pipeline_stage == "Technical interview"
    assert application.activities[0].interview_stage == "Technical interview"

    board = client.get("/board")
    assert board.status_code == 200
    assert "Technical interview" in board.text
    assert "Log reply" in board.text


def test_quick_actions_create_follow_up_and_response_work(client, session):
    client.post("/applications", data=application_form())
    application = session.scalar(select(Application))

    client.post(
        f"/applications/{application.id}/quick-action",
        data={"action": "applied_today"},
    )
    assert application.status == "Applied"
    assert application.pipeline_stage == "Submitted"
    assert application.follow_up_date == date.today() + timedelta(days=7)

    client.post(
        f"/applications/{application.id}/quick-action",
        data={"action": "reply_received"},
    )
    response_activity = session.scalar(
        select(ApplicationActivity).where(ApplicationActivity.needs_action.is_(True))
    )
    assert response_activity.summary == "Recruiter reply received"
    assert application.pipeline_stage == "Recruiter replied"

    inbox = client.get("/actions")
    assert inbox.status_code == 200
    assert "Needs a response" in inbox.text
    assert "Recruiter reply received" in inbox.text


def test_interview_schedule_is_structured_and_appears_in_inbox(client, session):
    client.post("/applications", data=application_form())
    application = session.scalar(select(Application))
    scheduled_at = f"{date.today() + timedelta(days=3)}T14:30"

    response = client.post(
        f"/applications/{application.id}/interviews",
        data={
            "pipeline_stage": "Technical interview",
            "scheduled_at": scheduled_at,
            "interview_format": "Video",
            "contact": "Alex Recruiter",
            "meeting_url": "https://meet.example/interview",
            "notes": "Review FPGA timing constraints",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert application.status == "Interview"
    assert application.pipeline_stage == "Technical interview"
    assert application.interview_date == date.today() + timedelta(days=3)

    interview = session.scalar(
        select(ApplicationActivity).where(ApplicationActivity.activity_type == "Interview")
    )
    assert interview.scheduled_at is not None
    assert interview.interview_format == "Video"
    assert interview.contact == "Alex Recruiter"
    assert interview.meeting_url == "https://meet.example/interview"

    inbox = client.get("/actions")
    assert "Upcoming interviews" in inbox.text
    assert "Alex Recruiter" in inbox.text
    assert "Open meeting link" in inbox.text


def test_phase_two_controls_are_rendered(client):
    client.post("/applications", data=application_form())
    board = client.get("/board")
    assert 'draggable="true"' in board.text
    assert "Applied today" in board.text

    listing = client.get("/applications")
    assert "data-status-select" in listing.text
    assert "Use default stage" in listing.text
