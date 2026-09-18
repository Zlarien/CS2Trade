import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

import dependencies
from db.models import User
from main import app

STEAMID64 = "76561198034202275"


@pytest.fixture
def client(db_sessionmaker):
    async def override_db_session():
        async with db_sessionmaker() as session:
            yield session

    app.dependency_overrides[dependencies.get_db_session] = override_db_session
    app.dependency_overrides[dependencies.get_current_steamid64] = lambda: STEAMID64
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def _seed_user(db_sessionmaker):
    async with db_sessionmaker() as session:
        session.add(User(steamid64=STEAMID64))
        await session.commit()


def test_list_excluded_items_starts_empty(client: TestClient) -> None:
    response = client.get("/me/excluded-items")
    assert response.status_code == 200
    assert response.json() == []


def test_add_and_list_excluded_item(client: TestClient) -> None:
    create = client.post("/me/excluded-items", json={"asset_id": "111", "reason": "cadeau"})
    assert create.status_code == 201
    assert create.json() == {"asset_id": "111", "reason": "cadeau"}

    listing = client.get("/me/excluded-items")
    assert listing.json() == [{"asset_id": "111", "reason": "cadeau"}]


def test_add_excluded_item_is_idempotent(client: TestClient) -> None:
    client.post("/me/excluded-items", json={"asset_id": "111", "reason": "cadeau"})
    client.post("/me/excluded-items", json={"asset_id": "111", "reason": "cadeau"})

    listing = client.get("/me/excluded-items")
    assert len(listing.json()) == 1


def test_remove_excluded_item(client: TestClient) -> None:
    client.post("/me/excluded-items", json={"asset_id": "111"})

    delete_response = client.delete("/me/excluded-items/111")
    assert delete_response.status_code == 204

    listing = client.get("/me/excluded-items")
    assert listing.json() == []


def test_excluded_items_require_auth() -> None:
    app.dependency_overrides.clear()
    client = TestClient(app)
    response = client.get("/me/excluded-items")
    assert response.status_code == 401
