import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from ..utils import get_password_hash, safe_collection_name


class OrgService:
    def __init__(self, master_collection: AsyncIOMotorCollection, master_db: AsyncIOMotorDatabase):
        self.master_collection = master_collection
        self.master_db = master_db

    async def organization_exists(self, organization_name: str) -> Optional[Dict]:
        return await self.master_collection.find_one({"organization_name": organization_name})

    async def create_organization(self, organization_name: str, email: str, password: str) -> Dict:
        if await self.organization_exists(organization_name):
            raise ValueError("Organization already exists")

        collection_name = safe_collection_name(organization_name)
        org_collection = self.master_db[collection_name]
        await org_collection.insert_one({"_meta": "initialized"})  # ensure collection creation

        hashed_password = get_password_hash(password)
        now = datetime.now(timezone.utc)
        org_doc = {
            "organization_name": organization_name,
            "collection_name": collection_name,
            "admin": {"email": email, "password": hashed_password},
            "created_at": now,
        }
        await self.master_collection.insert_one(org_doc)
        logger.info("Created organization {}", organization_name)
        return org_doc

    async def get_organization(self, organization_name: str) -> Optional[Dict]:
        return await self.master_collection.find_one({"organization_name": organization_name})

    async def update_organization(
        self,
        organization_name: str,
        requester_email: str,
        new_email: Optional[str] = None,
        new_password: Optional[str] = None,
        new_organization_name: Optional[str] = None,
    ) -> Dict:
        org = await self.organization_exists(organization_name)
        if not org:
            raise LookupError("Organization not found")

        if org["admin"]["email"] != requester_email:
            raise PermissionError("Unauthorized")

        update_fields = {}
        target_collection_name = org["collection_name"]
        # Handle rename
        if new_organization_name:
            if await self.organization_exists(new_organization_name):
                raise ValueError("New organization name already exists")

            new_collection_name = safe_collection_name(new_organization_name)
            old_collection = self.master_db[org["collection_name"]]
            new_collection = self.master_db[new_collection_name]

            cursor = old_collection.find({})
            async for doc in cursor:
                try:
                    await new_collection.insert_one(doc)
                except DuplicateKeyError:
                    doc_copy = doc.copy()
                    doc_copy.pop("_id", None)
                    await new_collection.insert_one(doc_copy)

            await old_collection.drop()
            target_collection_name = new_collection_name
            update_fields["organization_name"] = new_organization_name
            update_fields["collection_name"] = new_collection_name
            logger.info("Renamed organization {} to {}", organization_name, new_organization_name)

        if new_email:
            update_fields["admin.email"] = new_email
        if new_password:
            update_fields["admin.password"] = get_password_hash(new_password)

        if update_fields:
            await self.master_collection.update_one(
                {"organization_name": organization_name},
                {"$set": update_fields},
            )

        updated_name = update_fields.get("organization_name", organization_name)
        updated = await self.get_organization(updated_name)
        if not updated:
            raise RuntimeError("Failed to fetch updated organization")
        return updated

    async def delete_organization(self, organization_name: str, requester_email: str) -> None:
        org = await self.organization_exists(organization_name)
        if not org:
            raise LookupError("Organization not found")
        if org["admin"]["email"] != requester_email:
            raise PermissionError("Unauthorized")

        collection_name = org["collection_name"]
        await self.master_db[collection_name].drop()
        await self.master_collection.delete_one({"organization_name": organization_name})
        logger.info("Deleted organization {}", organization_name)


