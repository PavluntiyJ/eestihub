from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.schemas.health import HealthResponse


router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness and database reachability",
    description=(
        "Runs a real `SELECT 1`, so it can fail. Returns 200 when the process "
        "and the database are both up, and 503 when the database query fails. "
        "Endpoints that do not touch the database keep returning 200 while "
        "this reports `degraded`."
    ),
    responses={503: {"description": "Database unreachable"}},
)
def get_health(
    response: Response, session: Session = Depends(get_session)
) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="degraded", database="unavailable")

    return HealthResponse(status="ok", database="ok")
