from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Part, User
from ..schemas import AuditRead
from ..services.audit import audit_query, part_audit

router = APIRouter(tags=["Audit"], dependencies=[Depends(get_current_user)])


@router.get("/audit", response_model=list[AuditRead])
def list_audit(entity_type: str | None = None, entity_id: int | None = Query(default=None, gt=0),
               db: Session = Depends(get_db)):
    return db.scalars(audit_query(entity_type, entity_id)).all()


@router.get("/parts/{part_id}/audit", response_model=list[AuditRead])
def get_part_audit(part_id: int, db: Session = Depends(get_db)):
    if db.get(Part, part_id) is None:
        raise HTTPException(404, "Part not found.")
    return part_audit(db, part_id)
