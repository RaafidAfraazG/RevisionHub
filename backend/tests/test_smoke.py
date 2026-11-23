def create_part(client, number):
    response = client.post("/api/parts", json={"part_number": number, "name": number, "part_type": "ASSEMBLY"})
    assert response.status_code == 201
    part = response.json()
    response = client.post(f"/api/parts/{part['id']}/revisions")
    assert response.status_code == 201
    return part, response.json()


def test_create_part_and_first_revision(client):
    part, revision = create_part(client, "PART-001")
    assert revision["label"] == "A"
    assert revision["state"] == "DRAFT"
    assert client.get(f"/api/parts/{part['id']}").json()["revisions"][0]["id"] == revision["id"]


def test_two_level_bom_tree(client):
    _, root = create_part(client, "BIKE")
    wheel_part, wheel = create_part(client, "WHEEL")
    spoke_part, _ = create_part(client, "SPOKE")
    assert client.post(f"/api/revisions/{root['id']}/bom", json={"child_part_id": wheel_part["id"], "quantity": 2}).status_code == 201
    assert client.post(f"/api/revisions/{wheel['id']}/bom", json={"child_part_id": spoke_part["id"], "quantity": 32}).status_code == 201
    response = client.get(f"/api/revisions/{root['id']}/bom-tree")
    assert response.status_code == 200
    tree = response.json()
    assert tree["children"][0]["part_number"] == "WHEEL"
    assert tree["children"][0]["quantity"] == 2
    assert tree["children"][0]["children"][0]["quantity"] == 32
    assert tree["children"][0]["children"][0]["revision_label"] == "A"


def test_cycle_is_rejected(client):
    parent_part, parent = create_part(client, "PARENT")
    child_part, child = create_part(client, "CHILD")
    assert client.post(f"/api/revisions/{parent['id']}/bom", json={"child_part_id": child_part["id"], "quantity": 1}).status_code == 201
    response = client.post(f"/api/revisions/{child['id']}/bom", json={"child_part_id": parent_part["id"], "quantity": 1})
    assert response.status_code == 400
    assert "cycle" in response.json()["detail"]
