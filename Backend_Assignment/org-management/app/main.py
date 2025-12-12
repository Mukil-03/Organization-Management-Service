from fastapi import FastAPI

from .routers.org_router import router as org_router
from .routers.auth_router import router as auth_router

app = FastAPI(title="Organization Management Service")


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(org_router)


