from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import ChangeStatus, DecisionStage, DecisionValue, PartType, RevisionState, Role


class OrmSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PartCreate(BaseModel):
    part_number: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    part_type: PartType

    @field_validator("part_number", "name", "description", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class PartSummary(OrmSchema):
    id: int
    part_number: str
    name: str
    description: str
    part_type: PartType
    created_at: datetime


class RevisionSummary(OrmSchema):
    id: int
    part_id: int
    label: str
    state: RevisionState
    change_note: str
    created_at: datetime
    released_at: datetime | None


class PartListItem(PartSummary):
    latest_revision: RevisionSummary | None = None


class PartDetail(PartSummary):
    revisions: list[RevisionSummary]


class RevisionCreate(BaseModel):
    change_note: str = Field(default="", max_length=10000)


class BomLineCreate(BaseModel):
    child_part_id: int = Field(gt=0)
    quantity: int = Field(gt=0, strict=True, le=2147483647)


class BomLineRead(OrmSchema):
    id: int
    parent_revision_id: int
    child_part_id: int
    quantity: int
    child_part: PartSummary


class RevisionDetail(RevisionSummary):
    part: PartSummary
    bom_lines: list[BomLineRead]


class BomNode(BaseModel):
    part_id: int
    revision_id: int | None
    line_id: int | None
    part_number: str
    name: str
    revision_label: str | None
    state: RevisionState | None
    quantity: int
    children: list["BomNode"] = Field(default_factory=list)
    cycle_detected: bool = False


class UserRead(OrmSchema):
    id: int
    username: str
    full_name: str
    role: Role


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class ChangeCreate(BaseModel):
    part_id: int = Field(gt=0)
    draft_revision_id: int | None = Field(default=None, gt=0)
    title: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=10000)
    description: str = Field(default="", max_length=10000)

    @field_validator("title", "reason", "description", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class DecisionCreate(BaseModel):
    decision: DecisionValue
    comment: str = Field(default="", max_length=10000)


class DecisionRead(OrmSchema):
    id: int
    actor_id: int
    actor: UserRead
    stage: DecisionStage
    decision: DecisionValue
    comment: str
    cycle: int
    created_at: datetime


class AuditRead(OrmSchema):
    id: int
    timestamp: datetime
    actor_id: int
    actor: UserRead
    action: str
    entity_type: str
    entity_id: int
    details: dict


class ChangeRead(OrmSchema):
    id: int
    number: str
    title: str
    description: str
    reason: str
    part_id: int
    part: PartSummary
    draft_revision_id: int
    draft_revision: RevisionSummary
    status: ChangeStatus
    created_by: int
    creator: UserRead
    created_at: datetime
    updated_at: datetime
    review_cycle: int
    review_passed: bool


class ChangeDetail(ChangeRead):
    decisions: list[DecisionRead]
    timeline: list[AuditRead] = Field(default_factory=list)


class AttachmentRead(OrmSchema):
    id: int
    revision_id: int
    filename: str
    file_type: str
    size: int
    uploaded_by: int
    uploaded_at: datetime
