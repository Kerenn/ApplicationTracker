from datetime import date

from sqlalchemy import select

from app.models import Application, ApplicationRequirement
from app.services.applications import (
    apply_application_form,
    change_application_status,
    find_duplicate,
)


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
