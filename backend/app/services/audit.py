from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from ..models import AuditLog, ChangeRequest, Revision, User


def record_audit(db: Session, actor: User, action: str, entity_type: str,
                 entity_id: int, **details) -> AuditLog:
    entry = AuditLog(actor_id=actor.id, action=action, entity_type=entity_type,
                     entity_id=entity_id, details=details)
    db.add(entry)
    return entry


def audit_query(entity_type: str | None = None, entity_id: int | None = None):
    query = select(AuditLog).options(selectinload(AuditLog.actor))
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(AuditLog.entity_id == entity_id)
    return query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())


def part_audit(db: Session, part_id: int):
    revisions = select(Revision.id).where(Revision.part_id == part_id)
    changes = select(ChangeRequest.id).where(ChangeRequest.part_id == part_id)
    return db.scalars(audit_query().where(or_(
        (AuditLog.entity_type == "PART") & (AuditLog.entity_id == part_id),
        (AuditLog.entity_type == "REVISION") & AuditLog.entity_id.in_(revisions),
        (AuditLog.entity_type == "CHANGE_REQUEST") & AuditLog.entity_id.in_(changes),
    ))).all()
