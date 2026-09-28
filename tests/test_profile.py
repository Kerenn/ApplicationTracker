from datetime import date

from sqlalchemy import select

from app.models import (
    PersonalProfile,
    ProfileAnswer,
    ProfileEducation,
    ProfileExperience,
    ProfileProject,
)


def test_profile_page_starts_empty_without_persisting_placeholder(client, session):
    response = client.get("/profile")

    assert response.status_code == 200
    assert "Personal profile" in response.text
    assert "0%" in response.text
    assert session.get(PersonalProfile, 1) is None


def test_core_profile_is_saved_and_completion_updates(client, session):
    response = client.post(
        "/profile",
        data={
            "preferred_name": "Kadir Eren",
            "legal_name": "Kadir Eren Unal",
            "email": "eren@example.test",
            "phone": "+49 123 456",
            "city": "Berlin",
            "country": "Germany",
            "work_authorization": "Eligible to work in Germany",
            "sponsorship_required": "no",
            "professional_summary": "Electronics and FPGA engineer.",
            "skills": "VHDL, Python",
            "languages": "English, German, Turkish",
        },
        follow_redirects=True,
    )

    profile = session.get(PersonalProfile, 1)
    assert response.status_code == 200
    assert "Saved locally" in response.text
    assert profile.preferred_name == "Kadir Eren"
    assert profile.sponsorship_required is False
    assert "63%" in response.text


def test_structured_profile_entries_can_be_created_updated_and_deleted(client, session):
    client.post(
        "/profile/experiences",
        data={
            "employer": "Example Systems",
            "title": "FPGA Engineer",
            "start_date": "2024-01-01",
            "current": "on",
            "achievements": "Reduced verification time by 30%.",
            "technologies": "VHDL, cocotb",
        },
    )
    experience = session.scalar(select(ProfileExperience))
    assert experience.current is True
    assert experience.end_date is None
    assert experience.start_date == date(2024, 1, 1)

    client.post(
        f"/profile/experiences/{experience.id}",
        data={
            "employer": "Example Systems",
            "title": "Senior FPGA Engineer",
            "start_date": "2024-01-01",
            "end_date": "2026-09-01",
        },
    )
    assert experience.title == "Senior FPGA Engineer"
    assert experience.current is False
    assert experience.end_date == date(2026, 9, 1)

    client.post(
        "/profile/educations",
        data={
            "institution": "Example University",
            "degree": "MSc",
            "field_of_study": "Electrical Engineering",
        },
    )
    client.post(
        "/profile/projects",
        data={
            "name": "Motor-control FPGA",
            "role": "Developer",
            "impact": "Implemented deterministic control logic.",
        },
    )
    client.post(
        "/profile/answers",
        data={
            "category": "Availability",
            "question": "When can you start?",
            "answer": "After my contractual notice period.",
        },
    )

    assert session.scalar(select(ProfileEducation)).degree == "MSc"
    assert session.scalar(select(ProfileProject)).name == "Motor-control FPGA"
    assert session.scalar(select(ProfileAnswer)).category == "Availability"

    client.post(
        "/profile/answers",
        data={
            "category": "Availability",
            "question": "When can you start?",
            "answer": "Four weeks after signing.",
        },
    )
    answers = list(session.scalars(select(ProfileAnswer)))
    assert len(answers) == 1
    assert answers[0].answer == "Four weeks after signing."

    response = client.get("/profile")
    assert "Senior FPGA Engineer" in response.text
    assert "Motor-control FPGA" in response.text
    assert "When can you start?" in response.text
    assert "Four weeks after signing." in response.text

    client.post(f"/profile/experiences/{experience.id}/delete")
    assert session.get(ProfileExperience, experience.id) is None


def test_profile_entry_required_fields_are_validated(client, session):
    response = client.post("/profile/experiences", data={"employer": ""})
    assert response.status_code == 422
    assert session.scalar(select(ProfileExperience)) is None
