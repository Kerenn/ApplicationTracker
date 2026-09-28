from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import ApplicationStatus, PrimaryTrack, Priority
from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


application_tags = Table(
    "application_tags",
    Base.metadata,
    Column("application_id", ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint("fit_score IS NULL OR (fit_score >= 0 AND fit_score <= 10)", name="fit_score_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    legacy_id: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    company: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(300), default="")
    job_url: Mapped[str | None] = mapped_column(Text)
    normalized_job_url: Mapped[str | None] = mapped_column(Text, unique=True, index=True)
    application_url: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200))
    work_mode: Mapped[str | None] = mapped_column(String(40))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    contact: Mapped[str | None] = mapped_column(String(300))

    primary_track: Mapped[str] = mapped_column(String(40), default=PrimaryTrack.OTHER.value, index=True)
    status: Mapped[str] = mapped_column(String(40), default=ApplicationStatus.SAVED.value, index=True)
    pipeline_stage: Mapped[str | None] = mapped_column(String(80), index=True)
    priority: Mapped[str] = mapped_column(String(20), default=Priority.MEDIUM.value, index=True)
    fit_score: Mapped[float | None] = mapped_column(Float)

    date_found: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    applied_date: Mapped[date | None] = mapped_column(Date)
    application_deadline: Mapped[date | None] = mapped_column(Date)
    follow_up_date: Mapped[date | None] = mapped_column(Date, index=True)
    interview_date: Mapped[date | None] = mapped_column(Date)

    salary_expectation: Mapped[str | None] = mapped_column(String(200))
    salary_notes: Mapped[str | None] = mapped_column(Text)
    cv_version: Mapped[str | None] = mapped_column(String(120))
    next_action: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    tags: Mapped[list[Tag]] = relationship(secondary=application_tags, back_populates="applications")
    requirements: Mapped[list[ApplicationRequirement]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationRequirement.sort_order, ApplicationRequirement.id",
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    status_history: Mapped[list[StatusHistory]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="StatusHistory.changed_at.desc()",
    )
    activities: Mapped[list[ApplicationActivity]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationActivity.occurred_at.desc()",
    )

    @property
    def is_ready_to_apply(self) -> bool:
        required = [item for item in self.requirements if item.required]
        return bool(required) and all(item.completed for item in required)

    @property
    def attention_count(self) -> int:
        return sum(
            1
            for activity in self.activities
            if activity.needs_action and not activity.action_completed
        )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    applications: Mapped[list[Application]] = relationship(
        secondary=application_tags, back_populates="tags"
    )


class ApplicationRequirement(Base):
    __tablename__ = "application_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(240))
    category: Mapped[str] = mapped_column(String(80), default="Other")
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    value: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    application: Mapped[Application] = relationship(back_populates="requirements")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    document_type: Mapped[str] = mapped_column(String(100))
    local_path: Mapped[str | None] = mapped_column(Text)
    cloud_url: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    application: Mapped[Application] = relationship(back_populates="documents")


class StatusHistory(Base):
    __tablename__ = "status_history"
    __table_args__ = (
        UniqueConstraint("application_id", "changed_at", "to_status", name="unique_status_event"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    application: Mapped[Application] = relationship(back_populates="status_history")


class ApplicationActivity(Base):
    __tablename__ = "application_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    activity_type: Mapped[str] = mapped_column(String(40), default="Note", index=True)
    direction: Mapped[str] = mapped_column(String(20), default="Internal")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    summary: Mapped[str] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)
    interview_stage: Mapped[str | None] = mapped_column(String(100))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    contact: Mapped[str | None] = mapped_column(String(200))
    meeting_url: Mapped[str | None] = mapped_column(Text)
    interview_format: Mapped[str | None] = mapped_column(String(80))
    needs_action: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    action_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    application: Mapped[Application] = relationship(back_populates="activities")
