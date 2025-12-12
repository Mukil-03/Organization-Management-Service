from datetime import timedelta
from typing import Dict, Optional

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorCollection

from ..utils import verify_password, create_access_token
from ..config import get_settings


class AuthService:
    def __init__(self, master_collection: AsyncIOMotorCollection):
        self.master_collection = master_collection

    async def get_admin_org(self, email: str) -> Optional[Dict]:
        return await self.master_collection.find_one({"admin.email": email})

    async def authenticate_admin(self, email: str, password: str) -> Dict:
        org = await self.get_admin_org(email)
        if not org:
            raise PermissionError("Invalid credentials")
        if not verify_password(password, org["admin"]["password"]):
            raise PermissionError("Invalid credentials")
        logger.info("Admin {} authenticated for org {}", email, org["organization_name"])
        return org

    async def issue_token(self, email: str, org_name: str) -> str:
        settings = get_settings()
        payload = {
            "admin_email": email,
            "organization_name": org_name,
            "role": "admin",
        }
        return create_access_token(payload, expires_minutes=settings.access_token_expire_minutes)


