from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class OrgCreateRequest(BaseModel):
    organization_name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=6)


class OrgUpdateRequest(BaseModel):
    organization_name: str
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    new_organization_name: Optional[str] = None


class OrgResponse(BaseModel):
    organization_name: str
    collection_name: str
    admin_email: EmailStr
    created_at: datetime


class OrgMetadata(BaseModel):
    organization_name: str
    collection_name: str
    admin: dict
    created_at: datetime


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


