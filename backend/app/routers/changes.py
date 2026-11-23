from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user
from ..database import get_db
from ..models import AuditLog, ChangeDecision, ChangeRequest, ChangeStatus, DecisionStage, Role, User
from ..schemas import AuditRead, ChangeCreate, ChangeDetail, ChangeRead, DecisionCreate
from ..services.audit import audit_query
from ..services.revisions import lock_mutations
from ..services import workflow

router = APIRouter(prefix="/changes", tags=["Change requests"])


def change_query():
    return select(ChangeRequest).options(
        selectinload(ChangeRequest.part), selectinload(ChangeRequest.draft_revision),
        selectinload(ChangeRequest.creator),
        selectinload(ChangeRequest.decisions).selectinload(ChangeDecision.actor),
    )


def require_change(db: Session, change_id: int) -> ChangeRequest:
    change = db.scalar(change_query().where(ChangeRequest.id == change_id))
    if change is None:
        raise HTTPException(404, "Change request not found.")
    return change


def detail(db: Session, change: ChangeRequest) -> ChangeDetail:
    result = ChangeDetail.model_validate(change)
    result.timeline = [AuditRead.model_validate(entry) for entry in db.scalars(audit_query().where(or_(
        (AuditLog.entity_type == "CHANGE_REQUEST") & (AuditLog.entity_id == change.id),
        AuditLog.details["change_request_id"].as_integer() == change.id,
    )))]
    return result


def commit_and_read(db: Session, change: ChangeRequest) -> ChangeDetail:
    change_id = change.id
    db.commit()
    db.expire_all()
    return detail(db, require_change(db, change_id))


@router.post("", response_model=ChangeDetail, status_code=status.HTTP_201_CREATED)
def create_change(payload: ChangeCreate, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workflow.require_role(actor, Role.ENGINEER)
    lock_mutations(db)
    return commit_and_read(db, workflow.create_change(db, actor, payload))


@router.get("", response_model=list[ChangeRead])
def list_changes(status: ChangeStatus | None = None, mine: bool = False,
                 actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = change_query().order_by(ChangeRequest.created_at.desc(), ChangeRequest.id.desc())
    if status is not None:
        query = query.where(ChangeRequest.status == status)
    if mine:
        query = query.where(ChangeRequest.created_by == actor.id)
    return db.scalars(query).all()


@router.get("/{change_id}", response_model=ChangeDetail)
def get_change(change_id: int, _actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return detail(db, require_change(db, change_id))


@router.post("/{change_id}/submit", response_model=ChangeDetail)
def submit_change(change_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workflow.require_role(actor, Role.ENGINEER)
    lock_mutations(db)
    return commit_and_read(db, workflow.submit_change(db, actor, require_change(db, change_id)))


@router.post("/{change_id}/review", response_model=ChangeDetail)
def review_change(change_id: int, payload: DecisionCreate,
                  actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workflow.require_role(actor, Role.REVIEWER)
    lock_mutations(db)
    return commit_and_read(db, workflow.decide_change(db, actor, require_change(db, change_id), DecisionStage.REVIEW, payload))


@router.post("/{change_id}/approve", response_model=ChangeDetail)
def approve_change(change_id: int, payload: DecisionCreate,
                   actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workflow.require_role(actor, Role.APPROVER)
    lock_mutations(db)
    return commit_and_read(db, workflow.decide_change(db, actor, require_change(db, change_id), DecisionStage.APPROVAL, payload))
