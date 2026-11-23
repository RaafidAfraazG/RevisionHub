from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Part, Revision


def lock_mutations(db: Session):
    """Serialize workflow/BOM writes so state checks and graph edits are atomic.

    SQLite's legacy transaction mode does not BEGIN on auth SELECTs. Acquire the
    writer lock before reading mutable state. PostgreSQL locks parts in a stable
    order; all workflow and BOM writers use this same lock order.
    """
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        db.execute(select(Part.id).order_by(Part.id).with_for_update()).all()


def next_label(previous: str | None) -> str:
    number = 0
    for char in previous or "":
        number = number * 26 + ord(char) - ord("A") + 1
    number += 1
    result = ""
    while number:
        number, digit = divmod(number - 1, 26)
        result = chr(ord("A") + digit) + result
    return result


def new_revision(db: Session, part_id: int, change_note: str = "") -> Revision:
    previous = db.scalar(select(Revision).where(Revision.part_id == part_id)
                         .order_by(Revision.id.desc()).limit(1))
    revision = Revision(part_id=part_id, label=next_label(previous.label if previous else None),
                        change_note=change_note)
    db.add(revision)
    db.flush()
    return revision
