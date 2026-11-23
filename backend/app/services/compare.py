"""Multi-level BOM flattening and directional (old -> new) comparison.

Historical roots resolve children at the root's release time. A child that was
subsequently obsoleted still counts as a release at that time. Draft roots use
current releases, just like the interactive BOM. No root is included in a diff.
"""

from datetime import timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Part, Revision, RevisionState
from ..schemas import BomNode
from .bom import build_bom_tree


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def historical_tree(db: Session, root: Revision) -> BomNode:
    if root.released_at is None:
        return build_bom_tree(db, root)
    cutoff = aware(root.released_at)
    parts = {p.id: p for p in db.scalars(select(Part))}
    by_part: dict[int, list[Revision]] = {}
    for revision in db.scalars(select(Revision).options(selectinload(Revision.bom_lines)).order_by(Revision.id)):
        by_part.setdefault(revision.part_id, []).append(revision)

    def resolve(part_id):
        candidates = by_part.get(part_id, [])
        released = [r for r in candidates if r.released_at and aware(r.released_at) <= cutoff]
        available = [r for r in candidates if aware(r.created_at) <= cutoff]
        if released:
            return max(released, key=lambda r: (aware(r.released_at), r.id))
        # Imported/Phase 1 seed data can predate its children's timestamps.
        return (available[-1] if available else candidates[0]) if candidates else None

    def expand(part_id, revision, quantity=1, line_id=None, path=frozenset()):
        part = parts[part_id]
        node = BomNode(part_id=part_id, part_number=part.part_number, name=part.name,
                       revision_id=revision.id if revision else None,
                       revision_label=revision.label if revision else None,
                       state=revision.state if revision else None, quantity=quantity,
                       line_id=line_id, cycle_detected=part_id in path)
        if revision and not node.cycle_detected:
            node.children = [expand(line.child_part_id, resolve(line.child_part_id), line.quantity,
                                    line.id, path | {part_id}) for line in revision.bom_lines]
        return node

    return expand(root.part_id, root)


def flatten_tree(tree: BomNode) -> list[dict]:
    """One row per occurrence; level 0 root, per-parent and multiplied quantities."""
    rows = []

    def visit(node, level, multiplier, path):
        if node.cycle_detected:
            raise HTTPException(409, "BOM contains a cycle. Repair its structure before comparing or exporting.")
        total = multiplier * node.quantity
        path = [*path, node.part_number]
        rows.append(dict(level=level, part_number=node.part_number, name=node.name,
                         revision=node.revision_label, state=node.state.value if node.state else None,
                         quantity=node.quantity, total_quantity=total, path=path))
        for child in node.children:
            visit(child, level + 1, total, path)

    visit(tree, 0, 1, [])
    return rows


def aggregate(rows: list[dict]) -> dict[str, dict]:
    result = {}
    for row in rows:
        if row["level"] == 0:
            continue
        item = result.setdefault(row["part_number"], dict(part_number=row["part_number"], name=row["name"],
                                                        total_quantity=0, revisions=[], paths=[]))
        item["total_quantity"] += row["total_quantity"]
        if row["revision"] not in item["revisions"]:
            item["revisions"].append(row["revision"])
        item["paths"].append(dict(path=row["path"], quantity=row["quantity"], total_quantity=row["total_quantity"]))
    return result


def compare_revisions(db: Session, old: Revision, new: Revision) -> dict:
    if old.part_id != new.part_id:
        raise HTTPException(400, "Revisions must belong to the same part.")
    before = aggregate(flatten_tree(historical_tree(db, old)))
    after = aggregate(flatten_tree(historical_tree(db, new)))
    changes = {kind: [] for kind in ("ADDED", "REMOVED", "QTY_CHANGED", "REVISION_CHANGED")}
    for number in sorted(before.keys() | after.keys()):
        a, b = before.get(number), after.get(number)
        if a is None:
            changes["ADDED"].append(b)
        elif b is None:
            changes["REMOVED"].append(a)
        else:
            common = dict(part_number=number, name=b["name"], old_paths=a["paths"], new_paths=b["paths"])
            if a["total_quantity"] != b["total_quantity"]:
                changes["QTY_CHANGED"].append(dict(**common, old_qty=a["total_quantity"], new_qty=b["total_quantity"]))
            if a["revisions"] != b["revisions"]:
                changes["REVISION_CHANGED"].append(dict(**common, old_revision=a["revisions"], new_revision=b["revisions"]))
    return dict(old_revision_id=old.id, new_revision_id=new.id, **changes,
                summary={kind: len(items) for kind, items in changes.items()})
