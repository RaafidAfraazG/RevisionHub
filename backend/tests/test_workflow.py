from sqlalchemy import select

from app.models import Part, PartType, Revision, RevisionState, Role, User, utc_now


def login(client, username):
    response = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def draft_change(client, sessions):
    with sessions.begin() as db:
        part = Part(part_number="FRM-TEST", name="Frame", part_type=PartType.COMPONENT)
        db.add(part)
        db.flush()
        old = Revision(part_id=part.id, label="A", state=RevisionState.RELEASED, released_at=utc_now())
        draft = Revision(part_id=part.id, label="B")
        db.add_all([old, draft])
        db.flush()
        part_id, old_id, draft_id = part.id, old.id, draft.id
    response = client.post("/api/changes", json={
        "part_id": part_id, "draft_revision_id": draft_id,
        "title": "Refine frame", "reason": "Improve clearance", "description": "Geometry update",
    })
    assert response.status_code == 201
    return response.json(), old_id, draft_id


def test_full_release_obsoletes_previous_revision(client, sessions):
    change, old_id, draft_id = draft_change(client, sessions)
    path = f"/api/changes/{change['id']}"
    assert client.post(f"{path}/submit").json()["status"] == "IN_REVIEW"
    reviewer, approver = login(client, "reviewer1"), login(client, "approver1")
    response = client.post(f"{path}/review", headers=reviewer, json={"decision": "APPROVE", "comment": "Looks good"})
    assert response.status_code == 200
    assert response.json()["review_passed"] is True
    response = client.post(f"{path}/approve", headers=approver, json={"decision": "APPROVE", "comment": "Release approved"})
    assert response.status_code == 200
    assert response.json()["status"] == "RELEASED"
    assert client.get(f"/api/revisions/{draft_id}").json()["state"] == "RELEASED"
    assert client.get(f"/api/revisions/{draft_id}").json()["released_at"] is not None
    assert client.get(f"/api/revisions/{old_id}").json()["state"] == "OBSOLETE"
    assert {"REVISION_RELEASED", "REVISION_OBSOLETED"} <= {entry["action"] for entry in response.json()["timeline"]}


def test_wrong_role_and_creator_cannot_approve(client, sessions):
    change, _, _ = draft_change(client, sessions)
    path = f"/api/changes/{change['id']}"
    client.post(f"{path}/submit")
    reviewer, approver = login(client, "reviewer1"), login(client, "approver1")
    assert client.post(f"{path}/approve", headers=reviewer, json={"decision": "APPROVE"}).status_code == 403
    assert client.post(f"{path}/approve", headers=approver, json={"decision": "APPROVE"}).status_code == 409
    # Even if a creator's role changes later, they cannot approve their own ECR.
    with sessions.begin() as db:
        db.scalar(select(User).where(User.username == "engineer1")).role = Role.REVIEWER
    assert client.post(f"{path}/review", json={"decision": "APPROVE"}).status_code == 403
    assert client.post(f"{path}/review", headers=reviewer, json={"decision": "APPROVE"}).status_code == 200
    with sessions.begin() as db:
        db.scalar(select(User).where(User.username == "engineer1")).role = Role.APPROVER
    assert client.post(f"{path}/approve", json={"decision": "APPROVE"}).status_code == 403


def test_rejection_unlocks_draft_and_is_audited(client, sessions):
    change, _, draft_id = draft_change(client, sessions)
    path = f"/api/changes/{change['id']}"
    client.post(f"{path}/submit")
    reviewer = login(client, "reviewer1")
    assert client.post(f"{path}/review", headers=reviewer, json={"decision": "REJECT", "comment": "  "}).status_code == 400
    response = client.post(f"{path}/review", headers=reviewer, json={"decision": "REJECT", "comment": "Check the clearance"})
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert client.get(f"/api/revisions/{draft_id}").json()["state"] == "DRAFT"
    audit = client.get(f"/api/audit?entity_type=CHANGE_REQUEST&entity_id={change['id']}").json()
    assert audit[0]["action"] == "REVIEW_REJECTED"
    assert audit[0]["details"]["comment"] == "Check the clearance"
    resubmitted = client.post(f"{path}/submit").json()
    assert resubmitted["status"] == "IN_REVIEW"
    assert resubmitted["review_cycle"] == 2
    assert resubmitted["review_passed"] is False
