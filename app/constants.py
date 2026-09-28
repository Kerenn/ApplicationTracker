from enum import StrEnum


class ApplicationStatus(StrEnum):
    SAVED = "Saved"
    PREPARING = "Preparing"
    APPLYING = "Applying"
    APPLIED = "Applied"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"


class PrimaryTrack(StrEnum):
    SOFTWARE = "Software"
    EMBEDDED = "Embedded"
    ELECTRONICS = "Electronics"
    FPGA = "FPGA"
    AI_ML = "AI/ML"
    ROBOTICS = "Robotics"
    GAME = "Game"
    RESEARCH = "Research"
    OTHER = "Other"


class Priority(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


PIPELINE_STAGES = {
    ApplicationStatus.SAVED.value: ("Saved",),
    ApplicationStatus.PREPARING.value: (
        "Reviewing role",
        "Tailoring CV",
        "Preparing documents",
        "Ready to apply",
    ),
    ApplicationStatus.APPLYING.value: ("Application form", "Waiting to submit"),
    ApplicationStatus.APPLIED.value: (
        "Submitted",
        "Awaiting response",
        "Follow-up due",
        "Recruiter replied",
    ),
    ApplicationStatus.INTERVIEW.value: (
        "Recruiter screen",
        "Hiring manager interview",
        "Technical interview",
        "Take-home task",
        "On-site interview",
        "Final interview",
    ),
    ApplicationStatus.OFFER.value: ("Offer received", "Negotiating", "Accepted"),
    ApplicationStatus.REJECTED.value: ("Rejected",),
    ApplicationStatus.WITHDRAWN.value: ("Withdrawn",),
}

ACTIVITY_TYPES = ("Email", "Call", "Interview", "Follow-up", "Note")
ACTIVITY_DIRECTIONS = ("Incoming", "Outgoing", "Internal")

INTERVIEW_FORMATS = ("Video", "Phone", "On-site", "Take-home", "Other")


WORK_MODES = ("On-site", "Hybrid", "Remote", "Not stated")

REQUIREMENT_CATEGORIES = (
    "Document",
    "Form Question",
    "Salary",
    "Availability",
    "Language",
    "Work Authorization",
    "Portfolio",
    "Other",
)

DOCUMENT_TYPES = (
    "CV",
    "Cover Letter",
    "Reference Letter",
    "Degree Certificate",
    "Transcript",
    "Portfolio",
    "Other",
)


def enum_values(enum_type: type[StrEnum]) -> tuple[str, ...]:
    return tuple(item.value for item in enum_type)
