from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from ..config import get_settings
from ..db import db
from ..schemas import OrgCreateRequest, OrgResponse, OrgUpdateRequest
from ..services.org_service import OrgService
from ..utils import decode_access_token

router = APIRouter(prefix="/org", tags=["organizations"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login")


async def get_org_service() -> OrgService:
    master_db = db.get_master_db()
    return OrgService(master_db["organizations"], master_db)


async def get_current_admin(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload


@router.post("/create", response_model=OrgResponse)
async def create_org(payload: OrgCreateRequest):
    service = await get_org_service()
    try:
        org_doc = await service.create_organization(payload.organization_name, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return OrgResponse(
        organization_name=org_doc["organization_name"],
        collection_name=org_doc["collection_name"],
        admin_email=org_doc["admin"]["email"],
        created_at=org_doc["created_at"],
    )


@router.get("/get", response_model=OrgResponse)
async def get_org(organization_name: str):
    service = await get_org_service()
    org_doc = await service.get_organization(organization_name)
    if not org_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrgResponse(
        organization_name=org_doc["organization_name"],
        collection_name=org_doc["collection_name"],
        admin_email=org_doc["admin"]["email"],
        created_at=org_doc["created_at"],
    )


@router.put("/update", response_model=OrgResponse)
async def update_org(payload: OrgUpdateRequest, admin=Depends(get_current_admin)):
    service = await get_org_service()
    try:
        updated = await service.update_organization(
            organization_name=payload.organization_name,
            requester_email=admin["admin_email"],
            new_email=payload.email,
            new_password=payload.password,
            new_organization_name=payload.new_organization_name,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return OrgResponse(
        organization_name=updated["organization_name"],
        collection_name=updated["collection_name"],
        admin_email=updated["admin"]["email"],
        created_at=updated["created_at"],
    )


@router.delete("/delete")
async def delete_org(organization_name: str, admin=Depends(get_current_admin)):
    service = await get_org_service()
    try:
        await service.delete_organization(organization_name, requester_email=admin["admin_email"])
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return {"message": "Organization deleted"}


