import os
import pytest
from httpx import AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.main import app
from app import config
from app import db
from app.utils import safe_collection_name


@pytest.fixture(scope="module", autouse=True)
def setup_env():
    os.environ["SECRET_KEY"] = "testsecret"
    os.environ["MASTER_DB_NAME"] = "test_master"
    os.environ["ALGORITHM"] = "HS256"
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture(autouse=True)
def mock_db():
    client = AsyncMongoMockClient()
    db.db._client = client  # type: ignore
    return client


@pytest.fixture
def client(event_loop):
    c = AsyncClient(app=app, base_url="http://testserver")
    yield c
    event_loop.run_until_complete(c.aclose())


async def create_org_helper(client: AsyncClient):
    return await client.post(
        "/org/create",
        json={
            "organization_name": "Acme Corp",
            "email": "admin@acme.com",
            "password": "password123",
        },
    )


@pytest.mark.asyncio
async def test_org_create_success(client):
    res = await create_org_helper(client)
    assert res.status_code == 200
    data = res.json()
    assert data["collection_name"] == safe_collection_name("Acme Corp")
    master_db = db.db.get_master_db()
    stored = await master_db["organizations"].find_one({"organization_name": "Acme Corp"})
    assert stored is not None
    assert stored["admin"]["email"] == "admin@acme.com"
    collections = await master_db.list_collection_names()
    assert safe_collection_name("Acme Corp") in collections


@pytest.mark.asyncio
async def test_org_create_duplicate(client):
    await create_org_helper(client)
    res = await create_org_helper(client)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_get_org_not_found(client):
    res = await client.get("/org/get", params={"organization_name": "Missing"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_org_name_and_copy(client):
    await create_org_helper(client)
    login = await client.post("/admin/login", json={"email": "admin@acme.com", "password": "password123"})
    token = login.json()["access_token"]

    res = await client.put(
        "/org/update",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organization_name": "Acme Corp",
            "new_organization_name": "New Acme",
        },
    )
    assert res.status_code == 200
    new_coll = safe_collection_name("New Acme")
    master_db = db.db.get_master_db()
    collections = await master_db.list_collection_names()
    assert new_coll in collections
    assert safe_collection_name("Acme Corp") not in collections
    updated_doc = await master_db["organizations"].find_one({"organization_name": "New Acme"})
    assert updated_doc is not None
    assert updated_doc["collection_name"] == new_coll


@pytest.mark.asyncio
async def test_delete_org_permissions(client):
    await create_org_helper(client)
    login = await client.post("/admin/login", json={"email": "admin@acme.com", "password": "password123"})
    token = login.json()["access_token"]

    # another token for different org
    master_db = db.db.get_master_db()
    await master_db["organizations"].insert_one(
        {
            "organization_name": "Other",
            "collection_name": "org_other",
            "admin": {"email": "other@org.com", "password": login.json()["access_token"]},
            "created_at": "2023-01-01T00:00:00Z",
        }
    )
    res_forbidden = await client.delete(
        "/org/delete",
        params={"organization_name": "Other"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_forbidden.status_code == 403

    res = await client.delete(
        "/org/delete",
        params={"organization_name": "Acme Corp"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert await master_db["organizations"].find_one({"organization_name": "Acme Corp"}) is None


