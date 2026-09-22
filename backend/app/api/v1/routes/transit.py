from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.schemas.transit import NearbyTransitResponse
from app.services.nearby_service import get_nearby

router = APIRouter(prefix="/transit", tags=["transit"])


@router.get("/nearby", response_model=NearbyTransitResponse)
def nearby(
    response: Response,
    lat: Annotated[float, Query(ge=59.2, le=59.7, allow_inf_nan=False)],
    lon: Annotated[float, Query(ge=24.3, le=25.1, allow_inf_nan=False)],
    session: Session = Depends(get_session),
) -> NearbyTransitResponse:
    """Up to 20 platforms within 800m, with routes scheduled today in Tallinn."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return get_nearby(session, lat, lon)
    except (LookupError, SQLAlchemyError) as exc:
        raise HTTPException(503, detail={"code": "transit_unavailable"},
                            headers={"Cache-Control": "no-store"}) from exc
