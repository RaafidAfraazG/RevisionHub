from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user
from ..database import get_db
from ..models import Part, User
from ..schemas import PartCreate, PartDetail, PartListItem, PartSummary, RevisionCreate, RevisionSummary
from ..services.audit import record_audit
from ..services.revisions import lock_mutations, new_revision

router = APIRouter(prefix="/parts", tags=["Parts"])


@router.post("", response_model=PartSummary, status_code=status.HTTP_201_CREATED)
def create_part(payload: PartCreate, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    part = Part(**payload.model_dump())
    db.add(part)
    try:
        db.flush()
        record_audit(db, actor, "PART_CREATED", "PART", part.id, part_number=part.part_number)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A part with this part number already exists.")
    return part


@router.get("", response_model=list[PartListItem])
def list_parts(q: str | None = None, db: Session = Depends(get_db)):
    query = select(Part).options(selectinload(Part.revisions)).order_by(Part.part_number)
    if q and q.strip():
        term = q.strip()
        query = query.where(or_(Part.part_number.icontains(term, autoescape=True), Part.name.icontains(term, autoescape=True)))
    return [
        PartListItem(**PartSummary.model_validate(part).model_dump(),
                     latest_revision=RevisionSummary.model_validate(part.revisions[-1]) if part.revisions else None)
        for part in db.scalars(query)
    ]


@router.get("/{part_id}", response_model=PartDetail)
def get_part(part_id: int, db: Session = Depends(get_db)):
    part = db.get(Part, part_id)
    if part is None:
        raise HTTPException(404, "Part not found.")
    return part


@router.post("/{part_id}/revisions", response_model=RevisionSummary, status_code=status.HTTP_201_CREATED)
def create_revision(part_id: int, payload: RevisionCreate | None = None,
                    actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lock_mutations(db)
    part = db.scalar(select(Part).where(Part.id == part_id).with_for_update())
    if part is None:
        raise HTTPException(404, "Part not found.")
    try:
        revision = new_revision(db, part_id, payload.change_note if payload else "")
        record_audit(db, actor, "REVISION_CREATED", "REVISION", revision.id,
                     part_id=part_id, label=revision.label, to_state="DRAFT")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Another revision was created concurrently. Please retry.")
    return revision
