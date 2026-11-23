import csv
from io import StringIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import BomLine, Part, Revision, RevisionState, User
from ..schemas import BomLineCreate, BomLineRead, BomNode, RevisionDetail
from ..services.bom import build_bom_tree, would_create_cycle
from ..services.audit import record_audit
from ..services.revisions import lock_mutations
from ..services.compare import compare_revisions, flatten_tree

router = APIRouter(prefix="/revisions", tags=["Revisions & BOM"])


def require_revision(db: Session, revision_id: int) -> Revision:
    revision = db.get(Revision, revision_id)
    if revision is None:
        raise HTTPException(404, "Revision not found.")
    return revision


def require_draft(revision: Revision):
    if revision.state != RevisionState.DRAFT:
        raise HTTPException(409, "Only DRAFT revisions can have their BOM edited.")


@router.get("/{revision_id}", response_model=RevisionDetail)
def get_revision(revision_id: int, db: Session = Depends(get_db)):
    return require_revision(db, revision_id)


@router.post("/{revision_id}/bom", response_model=BomLineRead, status_code=status.HTTP_201_CREATED)
def add_bom_line(revision_id: int, payload: BomLineCreate,
                 actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lock_mutations(db)
    revision = require_revision(db, revision_id)
    require_draft(revision)
    if db.get(Part, payload.child_part_id) is None:
        raise HTTPException(404, "Child part not found.")
    if would_create_cycle(db, revision.part_id, payload.child_part_id):
        raise HTTPException(400, "This BOM line would create a cycle: a part cannot contain itself directly or indirectly.")
    line = BomLine(parent_revision_id=revision_id, **payload.model_dump())
    db.add(line)
    try:
        db.flush()
        record_audit(db, actor, "BOM_LINE_ADDED", "REVISION", revision_id,
                     part_id=revision.part_id, line_id=line.id, child_part_id=line.child_part_id, quantity=line.quantity)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This child part is already in the revision's BOM.")
    return line


@router.delete("/{revision_id}/bom/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bom_line(revision_id: int, line_id: int,
                    actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lock_mutations(db)
    revision = require_revision(db, revision_id)
    require_draft(revision)
    line = db.get(BomLine, line_id)
    if line is None or line.parent_revision_id != revision_id:
        raise HTTPException(404, "BOM line not found in this revision.")
    record_audit(db, actor, "BOM_LINE_REMOVED", "REVISION", revision_id,
                 part_id=revision.part_id, line_id=line.id, child_part_id=line.child_part_id, quantity=line.quantity)
    db.delete(line)
    db.commit()
    return Response(status_code=204)


@router.get("/{revision_id}/bom-tree", response_model=BomNode)
def get_bom_tree(revision_id: int, db: Session = Depends(get_db)):
    return build_bom_tree(db, require_revision(db, revision_id))


@router.get("/{revision_id}/compare/{other_id}")
def compare(revision_id: int, other_id: int, db: Session = Depends(get_db)):
    return compare_revisions(db, require_revision(db, revision_id), require_revision(db, other_id))


@router.get("/{revision_id}/bom.csv")
def export_bom(revision_id: int, db: Session = Depends(get_db)):
    revision = require_revision(db, revision_id)
    rows = flatten_tree(build_bom_tree(db, revision))
    output = StringIO(newline="")
    writer = csv.writer(output)
    columns = ["level", "part_number", "name", "revision", "state", "quantity", "total_quantity"]
    writer.writerow(columns)
    for row in rows:
        # Prevent spreadsheet formula execution in user-controlled text fields.
        writer.writerow([("'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@"))
                          else value) for value in (row[column] for column in columns)])
    filename = quote(f"{revision.part.part_number}-rev-{revision.label}-bom.csv", safe="")
    return Response(output.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"})
