from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.schemas.housing import HousingRentsResponse, HousingTrendsResponse
from app.services.housing_service import get_housing_rents, get_housing_trends


router = APIRouter(prefix="/housing", tags=["housing"])
RENTS_CACHE_CONTROL = "public, max-age=86400, stale-while-revalidate=604800"


@router.get("/rents", response_model=HousingRentsResponse)
def housing_rents(
    response: Response, session: Session = Depends(get_session)
) -> HousingRentsResponse:
    response.headers["Cache-Control"] = RENTS_CACHE_CONTROL
    try:
        return get_housing_rents(session)
    except (LookupError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Housing rent data is unavailable",
        ) from exc


@router.get("/trends", response_model=HousingTrendsResponse)
def housing_trends(session: Session = Depends(get_session)) -> HousingTrendsResponse:
    try:
        return get_housing_trends(session)
    except (LookupError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Housing rent trend data is unavailable",
        ) from exc
