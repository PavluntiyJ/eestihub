from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.schemas.housing import HousingRentsResponse
from app.services.housing_service import get_housing_rents


router = APIRouter(prefix="/housing", tags=["housing"])


@router.get("/rents", response_model=HousingRentsResponse)
def housing_rents(session: Session = Depends(get_session)) -> HousingRentsResponse:
    try:
        return get_housing_rents(session)
    except (LookupError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Housing rent data is unavailable",
        ) from exc
