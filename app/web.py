from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.constants import (
    ApplicationStatus,
    ACTIVITY_DIRECTIONS,
    ACTIVITY_TYPES,
    DOCUMENT_TYPES,
    PrimaryTrack,
    Priority,
    PIPELINE_STAGES,
    REQUIREMENT_CATEGORIES,
    WORK_MODES,
    enum_values,
)


templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.globals.update(
    statuses=enum_values(ApplicationStatus),
    tracks=enum_values(PrimaryTrack),
    priorities=enum_values(Priority),
    work_modes=WORK_MODES,
    requirement_categories=REQUIREMENT_CATEGORIES,
    document_types=DOCUMENT_TYPES,
    pipeline_stages=PIPELINE_STAGES,
    activity_types=ACTIVITY_TYPES,
    activity_directions=ACTIVITY_DIRECTIONS,
)
