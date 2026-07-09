from fastapi import APIRouter

from app.api.v1.routes import health, taxes


router = APIRouter()
router.include_router(health.router)
router.include_router(taxes.router)
