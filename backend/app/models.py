from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PartType(str, Enum):
    ASSEMBLY = "ASSEMBLY"
    COMPONENT = "COMPONENT"


class RevisionState(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    RELEASED = "RELEASED"
    OBSOLETE = "OBSOLETE"


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    part_type: Mapped[PartType] = mapped_column(SqlEnum(PartType))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revisions: Mapped[list["Revision"]] = relationship(
        back_populates="part", order_by="Revision.id", cascade="all, delete-orphan"
    )


class Revision(Base):
    __tablename__ = "revisions"
    __table_args__ = (UniqueConstraint("part_id", "label", name="uq_part_revision"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id"), index=True)
    label: Mapped[str] = mapped_column(String(32))
    state: Mapped[RevisionState] = mapped_column(SqlEnum(RevisionState), default=RevisionState.DRAFT)
    change_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    part: Mapped[Part] = relationship(back_populates="revisions")
    bom_lines: Mapped[list["BomLine"]] = relationship(
        back_populates="parent_revision", cascade="all, delete-orphan", order_by="BomLine.id"
    )


class BomLine(Base):
    __tablename__ = "bom_lines"
    __table_args__ = (
        UniqueConstraint("parent_revision_id", "child_part_id", name="uq_bom_child"),
        CheckConstraint("quantity > 0", name="ck_positive_quantity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_revision_id: Mapped[int] = mapped_column(ForeignKey("revisions.id"), index=True)
    child_part_id: Mapped[int] = mapped_column(ForeignKey("parts.id"), index=True)
    quantity: Mapped[int]
    parent_revision: Mapped[Revision] = relationship(back_populates="bom_lines")
    child_part: Mapped[Part] = relationship()


class Role(str, Enum):
    ENGINEER = "ENGINEER"
    REVIEWER = "REVIEWER"
    APPROVER = "APPROVER"


class ChangeStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RELEASED = "RELEASED"


class DecisionStage(str, Enum):
    REVIEW = "REVIEW"
    APPROVAL = "APPROVAL"


class DecisionValue(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SqlEnum(Role))


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str | None] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id"), index=True)
    # A revision belongs to a single ECR throughout all resubmission cycles.
    draft_revision_id: Mapped[int] = mapped_column(ForeignKey("revisions.id"), unique=True)
    status: Mapped[ChangeStatus] = mapped_column(SqlEnum(ChangeStatus), default=ChangeStatus.DRAFT, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    review_cycle: Mapped[int] = mapped_column(default=0)
    part: Mapped[Part] = relationship()
    draft_revision: Mapped[Revision] = relationship()
    creator: Mapped[User] = relationship()
    decisions: Mapped[list["ChangeDecision"]] = relationship(
        back_populates="change_request", order_by="ChangeDecision.id", cascade="all, delete-orphan"
    )

    @property
    def review_passed(self) -> bool:
        return self.status in (ChangeStatus.IN_REVIEW, ChangeStatus.APPROVED, ChangeStatus.RELEASED) and any(
            decision.cycle == self.review_cycle and decision.stage == DecisionStage.REVIEW
            and decision.decision == DecisionValue.APPROVE for decision in self.decisions
        )


class ChangeDecision(Base):
    __tablename__ = "change_decisions"
    __table_args__ = (UniqueConstraint("change_request_id", "cycle", "stage", name="uq_decision_cycle_stage"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    change_request_id: Mapped[int] = mapped_column(ForeignKey("change_requests.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    stage: Mapped[DecisionStage] = mapped_column(SqlEnum(DecisionStage))
    decision: Mapped[DecisionValue] = mapped_column(SqlEnum(DecisionValue))
    comment: Mapped[str] = mapped_column(Text, default="")
    cycle: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    change_request: Mapped[ChangeRequest] = relationship(back_populates="decisions")
    actor: Mapped[User] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int] = mapped_column(index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    actor: Mapped[User] = relationship()


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("revisions.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(255), unique=True)
    file_type: Mapped[str] = mapped_column(String(10))
    size: Mapped[int]
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
