import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Role, User


@pytest.fixture
def sessions(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    password = hash_password("password123")
    with factory.begin() as db:
        for role in Role:
            db.add(User(username=f"{role.value.lower()}1", full_name=role.value.title(),
                        role=role, hashed_password=password))
    yield factory
    engine.dispose()


@pytest.fixture
def client(sessions):
    def override_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    # The fixture owns its isolated schema; do not run the real DB lifespan.
    test_client = TestClient(app)
    response = test_client.post("/api/auth/login", json={"username": "engineer1", "password": "password123"})
    assert response.status_code == 200
    test_client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()
