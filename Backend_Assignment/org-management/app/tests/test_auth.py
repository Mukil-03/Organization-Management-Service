import os
import pytest
from httpx import AsyncClient
from jose import jwt
from mongomock_motor import AsyncMongoMockClient

from app.main import app
from app.config import get_settings
from app import config
from app import db
from app.utils import get_password_hash


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


@pytest.mark.asyncio
async def test_admin_login_success_and_token(client):
    settings = get_settings()
    master_db = db.db.get_master_db()
    await master_db["organizations"].insert_one(
        {
            "organization_name": "Acme",
            "collection_name": "org_acme",
            "admin": {
                "email": "admin@acme.com",
                "password": get_password_hash("password123"),
            },
            "created_at": "2023-01-01T00:00:00Z",
        }
    )

    res = await client.post(
        "/admin/login",
        json={"email": "admin@acme.com", "password": "password123"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert decoded["admin_email"] == "admin@acme.com"
    assert decoded["organization_name"] == "Acme"


