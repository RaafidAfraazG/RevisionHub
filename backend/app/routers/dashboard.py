from statistics import mean

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import AuditLog, ChangeRequest, ChangeStatus, Part, Revision, RevisionState
from ..schemas import AuditRead
from ..services.audit import audit_query
from ..services.compare import aware

router = APIRouter(tags=["Dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    revisions = {state.value: 0 for state in RevisionState}
    revisions.update({state.value: count for state, count in db.execute(
        select(Revision.state, func.count()).group_by(Revision.state))})
    changes = {status.value: 0 for status in ChangeStatus}
    changes.update({status.value: count for status, count in db.execute(
        select(ChangeRequest.status, func.count()).group_by(ChangeRequest.status))})
    # First submission through release, including any rejected/resubmitted cycles.
    submissions = dict(db.execute(select(AuditLog.entity_id, func.min(AuditLog.timestamp)).where(
        AuditLog.entity_type == "CHANGE_REQUEST", AuditLog.action == "ECR_SUBMITTED"
    ).group_by(AuditLog.entity_id)).all())
    durations = []
    for change in db.scalars(select(ChangeRequest).where(ChangeRequest.status == ChangeStatus.RELEASED)):
        start, end = submissions.get(change.id), change.draft_revision.released_at
        if start and end and aware(end) >= aware(start):
            durations.append((aware(end) - aware(start)).total_seconds() / 3600)
    return dict(parts=db.scalar(select(func.count(Part.id))), revisions_by_state=revisions,
                ecrs_by_status=changes, average_release_hours=round(mean(durations), 2) if durations else None,
                released_ecr_sample_size=len(durations),
                recent_activity=[AuditRead.model_validate(entry) for entry in db.scalars(audit_query().limit(10))])
