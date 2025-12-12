from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional

from .config import get_settings


class Database:
    def __init__(self) -> None:
        self._client: Optional[AsyncIOMotorClient] = None

    def get_client(self) -> AsyncIOMotorClient:
        if self._client is None:
            settings = get_settings()
            self._client = AsyncIOMotorClient(settings.mongodb_uri)
        return self._client

    def get_master_db(self) -> AsyncIOMotorDatabase:
        settings = get_settings()
        return self.get_client()[settings.master_db_name]


db = Database()


async def get_master_collection():
    return db.get_master_db()["organizations"]


