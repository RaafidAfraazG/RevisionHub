"""Part-level cycle validation and revision-aware BOM expansion."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import BomLine, Part, Revision, RevisionState
from ..schemas import BomNode


def would_create_cycle(db: Session, parent_part_id: int, child_part_id: int) -> bool:
    # Include every revision: a part must never contain itself through historical
    # or draft structures, even when that revision is not currently selected.
    edges: dict[int, set[int]] = defaultdict(set)
    for parent, child in db.execute(
        select(Revision.part_id, BomLine.child_part_id)
        .join(BomLine, BomLine.parent_revision_id == Revision.id)
    ):
        edges[parent].add(child)
    pending, visited = [child_part_id], set()
    while pending:
        current = pending.pop()
        if current == parent_part_id:
            return True
        if current not in visited:
            visited.add(current)
            pending.extend(edges[current])
    return False


def build_bom_tree(db: Session, root: Revision) -> BomNode:
    # Load once, then walk an adjacency map rather than issuing a query per node.
    parts = {part.id: part for part in db.scalars(select(Part))}
    revisions = list(db.scalars(select(Revision).options(selectinload(Revision.bom_lines)).order_by(Revision.id)))
    latest: dict[int, Revision] = {}
    released: dict[int, Revision] = {}
    for revision in revisions:
        latest[revision.part_id] = revision
        if revision.state == RevisionState.RELEASED:
            released[revision.part_id] = revision
    selected = latest | released

    def expand(part: Part, revision: Revision | None, quantity: int,
               line_id: int | None, path: frozenset[int]) -> BomNode:
        cyclic = part.id in path
        node = BomNode(
            part_id=part.id, revision_id=revision.id if revision else None,
            line_id=line_id, part_number=part.part_number, name=part.name,
            revision_label=revision.label if revision else None,
            state=revision.state if revision else None, quantity=quantity,
            cycle_detected=cyclic,
        )
        if cyclic or revision is None:
            return node
        node.children = [
            expand(parts[line.child_part_id], selected.get(line.child_part_id),
                   line.quantity, line.id, path | {part.id})
            for line in revision.bom_lines
        ]
        return node

    return expand(parts[root.part_id], root, 1, None, frozenset())
