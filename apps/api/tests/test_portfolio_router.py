import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

import dependencies
from db.models import InventorySnapshot, User
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


def test_portfolio_history_starts_empty(client: TestClient) -> None:
    response = client.get("/me/portfolio-history")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_portfolio_history_returns_snapshots_in_order(
    client: TestClient, db_sessionmaker
) -> None:
    async with db_sessionmaker() as session:
        session.add_all(
            [
                InventorySnapshot(
                    user_steamid64=STEAMID64, total_value=100.0, currency="EUR", item_count=10
                ),
                InventorySnapshot(
                    user_steamid64=STEAMID64, total_value=120.0, currency="EUR", item_count=11
                ),
            ]
        )
        await session.commit()

    response = client.get("/me/portfolio-history")

    assert response.status_code == 200
    body = response.json()
    assert [s["total_value"] for s in body] == [100.0, 120.0]


def test_portfolio_history_requires_auth() -> None:
    app.dependency_overrides.clear()
    client = TestClient(app)
    response = client.get("/me/portfolio-history")
    assert response.status_code == 401
