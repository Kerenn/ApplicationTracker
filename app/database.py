import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv(
    "JOB_TRACKER_DATABASE_URL", "sqlite:///data/tracker.sqlite"
)

if DATABASE_URL.startswith("sqlite:///"):
    database_path = DATABASE_URL.removeprefix("sqlite:///")
    if database_path and database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _apply_additive_migrations() -> None:
    """Keep early local databases usable without introducing a migration framework yet."""
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "applications" not in inspector.get_table_names():
            return
        columns = {column["name"] for column in inspector.get_columns("applications")}
        if "pipeline_stage" not in columns:
            connection.execute(
                text("ALTER TABLE applications ADD COLUMN pipeline_stage VARCHAR(80)")
            )
        connection.execute(
            text(
                "UPDATE applications SET pipeline_stage = CASE status "
                "WHEN 'Saved' THEN 'Saved' "
                "WHEN 'Preparing' THEN 'Reviewing role' "
                "WHEN 'Applying' THEN 'Application form' "
                "WHEN 'Applied' THEN 'Submitted' "
                "WHEN 'Interview' THEN 'Recruiter screen' "
                "WHEN 'Offer' THEN 'Offer received' "
                "WHEN 'Rejected' THEN 'Rejected' "
                "WHEN 'Withdrawn' THEN 'Withdrawn' "
                "ELSE status END "
                "WHERE pipeline_stage IS NULL OR pipeline_stage = ''"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_applications_pipeline_stage "
                "ON applications (pipeline_stage)"
            )
        )


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(engine)
    _apply_additive_migrations()


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
