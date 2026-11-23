import csv
from datetime import datetime, timezone
from io import StringIO

from app.models import Revision, RevisionState
from test_smoke import create_part


def add(client, revision, part, quantity):
    assert client.post(f"/api/revisions/{revision['id']}/bom",
                       json={"child_part_id": part["id"], "quantity": quantity}).status_code == 201


def test_compare_added_removed_and_quantity_changes(client, sessions):
    root, old = create_part(client, "ROOT")
    new = client.post(f"/api/parts/{root['id']}/revisions").json()
    branch, branch_a = create_part(client, "BRANCH")
    shared, _ = create_part(client, "SHARED")
    removed, _ = create_part(client, "REMOVED")
    added, _ = create_part(client, "ADDED")
    add(client, branch_a, shared, 3)
    add(client, old, branch, 2)
    add(client, old, shared, 1)
    add(client, new, branch, 4)
    add(client, new, shared, 1)
    add(client, old, removed, 1)
    add(client, new, added, 5)
    # A historical child release must remain resolvable after obsolescence.
    with sessions.begin() as db:
        db.get(Revision, branch_a['id']).state = RevisionState.OBSOLETE
        db.get(Revision, branch_a['id']).released_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        db.get(Revision, old['id']).released_at = datetime(2021, 1, 1, tzinfo=timezone.utc)
    branch_b = client.post(f"/api/parts/{branch['id']}/revisions").json()
    add(client, branch_b, shared, 3)
    with sessions.begin() as db:
        db.get(Revision, branch_b['id']).state = RevisionState.RELEASED
        db.get(Revision, branch_b['id']).released_at = datetime(2022, 1, 1, tzinfo=timezone.utc)
    response = client.get(f"/api/revisions/{old['id']}/compare/{new['id']}")
    assert response.status_code == 200
    diff = response.json()
    assert [row['part_number'] for row in diff['ADDED']] == ['ADDED']
    assert [row['part_number'] for row in diff['REMOVED']] == ['REMOVED']
    assert [(row['part_number'], row['old_qty'], row['new_qty']) for row in diff['QTY_CHANGED']] == [
        ('BRANCH', 2, 4), ('SHARED', 7, 13)]
    assert diff['QTY_CHANGED'][1]['old_paths'][0]['path'] == ['ROOT', 'BRANCH', 'SHARED']
    assert [(row['part_number'], row['old_revision'], row['new_revision'])
            for row in diff['REVISION_CHANGED']] == [('BRANCH', ['A'], ['B'])]
    assert diff['summary'] == dict(ADDED=1, REMOVED=1, QTY_CHANGED=2, REVISION_CHANGED=1)
    assert client.get(f"/api/revisions/{old['id']}/compare/{branch_a['id']}").status_code == 400


def test_bom_csv_headers_and_rows(client):
    _, root = create_part(client, "ROOT")
    branch, branch_revision = create_part(client, "BRANCH")
    child, _ = create_part(client, "CHILD")
    add(client, root, branch, 2)
    add(client, branch_revision, child, 3)
    add(client, root, child, 1)
    response = client.get(f"/api/revisions/{root['id']}/bom.csv")
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/csv')
    assert 'attachment;' in response.headers['content-disposition']
    rows = list(csv.reader(StringIO(response.text)))
    assert rows[0] == ['level', 'part_number', 'name', 'revision', 'state', 'quantity', 'total_quantity']
    assert rows[1:] == [
        ['0', 'ROOT', 'ROOT', 'A', 'DRAFT', '1', '1'],
        ['1', 'BRANCH', 'BRANCH', 'A', 'DRAFT', '2', '2'],
        ['2', 'CHILD', 'CHILD', 'A', 'DRAFT', '3', '6'],
        ['1', 'CHILD', 'CHILD', 'A', 'DRAFT', '1', '1'],
    ]
