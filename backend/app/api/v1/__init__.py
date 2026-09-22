from fastapi import APIRouter

from app.api.v1.routes import addresses, eresidency, health, housing, planner, taxes, transit


router = APIRouter()
router.include_router(addresses.router)
router.include_router(eresidency.router)
router.include_router(health.router)
router.include_router(housing.router)
router.include_router(planner.router)
router.include_router(taxes.router)
router.include_router(transit.router)
