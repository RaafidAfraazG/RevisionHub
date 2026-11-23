"""Explicit ECR state machine. Callers commit once after a successful action.

All decisions, revision transitions, obsolescence and audit records participate
in that same transaction. No service action commits intermediate state.
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    ChangeDecision, ChangeRequest, ChangeStatus, DecisionStage, DecisionValue,
    Part, Revision, RevisionState, Role, User, utc_now,
)
from ..schemas import ChangeCreate, DecisionCreate
from .audit import record_audit
from .revisions import new_revision


TRANSITIONS = {
    "submit": {ChangeStatus.DRAFT: ChangeStatus.IN_REVIEW, ChangeStatus.REJECTED: ChangeStatus.IN_REVIEW},
    "review_approve": {ChangeStatus.IN_REVIEW: ChangeStatus.IN_REVIEW},
    "review_reject": {ChangeStatus.IN_REVIEW: ChangeStatus.REJECTED},
    "approval_approve": {ChangeStatus.IN_REVIEW: ChangeStatus.APPROVED},
    "approval_reject": {ChangeStatus.IN_REVIEW: ChangeStatus.REJECTED},
    "release": {ChangeStatus.APPROVED: ChangeStatus.RELEASED},
}


def require_role(actor: User, role: Role):
    if actor.role != role:
        raise HTTPException(403, f"This action requires the {role.value} role.")


def transition(change: ChangeRequest, action: str):
    target = TRANSITIONS[action].get(change.status)
    if target is None:
        raise HTTPException(409, f"Cannot {action.replace('_', ' ')} an ECR in {change.status.value} state.")
    change.status = target
    change.updated_at = utc_now()


def set_revision_state(db: Session, actor: User, revision: Revision, state: RevisionState,
                       change: ChangeRequest, action: str):
    previous = revision.state
    revision.state = state
    if state == RevisionState.RELEASED:
        revision.released_at = utc_now()
    record_audit(db, actor, action, "REVISION", revision.id,
                 from_state=previous.value, to_state=state.value, part_id=revision.part_id,
                 change_request_id=change.id, change_number=change.number)


def create_change(db: Session, actor: User, payload: ChangeCreate) -> ChangeRequest:
    require_role(actor, Role.ENGINEER)
    part = db.get(Part, payload.part_id)
    if part is None:
        raise HTTPException(404, "Part not found.")
    if payload.draft_revision_id is not None:
        revision = db.get(Revision, payload.draft_revision_id)
        if revision is None or revision.part_id != part.id:
            raise HTTPException(400, "The proposed revision must belong to the selected part.")
    else:
        revision = db.scalar(select(Revision).where(
            Revision.part_id == part.id, Revision.state == RevisionState.DRAFT,
            ~Revision.id.in_(select(ChangeRequest.draft_revision_id)),
        ).order_by(Revision.id.desc()).limit(1))
        if revision is None:
            revision = new_revision(db, part.id, payload.title)
            record_audit(db, actor, "REVISION_CREATED", "REVISION", revision.id,
                         part_id=part.id, label=revision.label, to_state="DRAFT")
    if revision.state != RevisionState.DRAFT:
        raise HTTPException(409, "An ECR must propose an existing DRAFT revision.")
    if db.scalar(select(ChangeRequest.id).where(ChangeRequest.draft_revision_id == revision.id)):
        raise HTTPException(409, "This revision already belongs to an ECR. Open that ECR to continue its workflow.")
    change = ChangeRequest(title=payload.title, description=payload.description, reason=payload.reason,
                           part_id=part.id, draft_revision_id=revision.id, created_by=actor.id)
    db.add(change)
    db.flush()
    change.number = f"ECR-{change.id:04d}"
    record_audit(db, actor, "ECR_CREATED", "CHANGE_REQUEST", change.id,
                 part_id=part.id, revision_id=revision.id, number=change.number, to_status="DRAFT")
    return change


def submit_change(db: Session, actor: User, change: ChangeRequest) -> ChangeRequest:
    require_role(actor, Role.ENGINEER)
    if change.created_by != actor.id:
        raise HTTPException(403, "Only the engineer who created this ECR may submit it.")
    if change.draft_revision.state != RevisionState.DRAFT:
        raise HTTPException(409, "Only a DRAFT revision can be submitted for review.")
    transition(change, "submit")
    change.review_cycle += 1
    set_revision_state(db, actor, change.draft_revision, RevisionState.IN_REVIEW, change, "REVISION_IN_REVIEW")
    record_audit(db, actor, "ECR_SUBMITTED", "CHANGE_REQUEST", change.id,
                 part_id=change.part_id, cycle=change.review_cycle, to_status="IN_REVIEW")
    return change


def decide_change(db: Session, actor: User, change: ChangeRequest,
                   stage: DecisionStage, payload: DecisionCreate) -> ChangeRequest:
    require_role(actor, Role.REVIEWER if stage == DecisionStage.REVIEW else Role.APPROVER)
    if actor.id == change.created_by:
        raise HTTPException(403, "You cannot review or approve your own ECR.")
    if change.status != ChangeStatus.IN_REVIEW or change.draft_revision.state != RevisionState.IN_REVIEW:
        raise HTTPException(409, "Decisions are only allowed while the ECR and revision are IN_REVIEW.")
    if stage == DecisionStage.REVIEW and change.review_passed:
        raise HTTPException(409, "This review cycle has already passed. The ECR is waiting for an approver.")
    if stage == DecisionStage.APPROVAL and not change.review_passed:
        raise HTTPException(409, "A reviewer must approve this review cycle before final approval.")
    comment = payload.comment.strip()
    if payload.decision == DecisionValue.REJECT and not comment:
        raise HTTPException(400, "A comment is required when rejecting an ECR.")
    db.add(ChangeDecision(change_request_id=change.id, actor_id=actor.id,
                          stage=stage, decision=payload.decision, comment=comment, cycle=change.review_cycle))
    action_prefix = "review" if stage == DecisionStage.REVIEW else "approval"
    transition(change, f"{action_prefix}_{payload.decision.value.lower()}")
    audit_action = f"{stage.value}_{'APPROVED' if payload.decision == DecisionValue.APPROVE else 'REJECTED'}"
    record_audit(db, actor, audit_action, "CHANGE_REQUEST", change.id,
                 part_id=change.part_id, cycle=change.review_cycle, comment=comment, to_status=change.status.value)
    if payload.decision == DecisionValue.REJECT:
        set_revision_state(db, actor, change.draft_revision, RevisionState.DRAFT, change, "REVISION_RETURNED_TO_DRAFT")
    elif stage == DecisionStage.APPROVAL:
        # Obsolete every prior release (also repairs legacy data with >1 release).
        previous_releases = db.scalars(select(Revision).where(
            Revision.part_id == change.part_id, Revision.state == RevisionState.RELEASED,
            Revision.id != change.draft_revision_id,
        )).all()
        for revision in previous_releases:
            set_revision_state(db, actor, revision, RevisionState.OBSOLETE, change, "REVISION_OBSOLETED")
        set_revision_state(db, actor, change.draft_revision, RevisionState.RELEASED, change, "REVISION_RELEASED")
        transition(change, "release")
        record_audit(db, actor, "ECR_RELEASED", "CHANGE_REQUEST", change.id,
                     part_id=change.part_id, revision_id=change.draft_revision_id, to_status="RELEASED")
    return change
