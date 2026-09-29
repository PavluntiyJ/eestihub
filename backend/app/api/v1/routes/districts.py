from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.schemas.districts import DistrictsResponse
from app.services.district_service import district_context

router = APIRouter(prefix='/planner', tags=['planner'])


@router.get('/districts', response_model=DistrictsResponse)
def districts(rooms: int = Query(1, ge=1, le=3), session: Session = Depends(get_session)):
    try:
        return district_context(session, rooms)
    except (LookupError, SQLAlchemyError) as exc:
        raise HTTPException(503, detail={'code': 'districts_unavailable'}, headers={'Cache-Control': 'no-store'}) from exc


@router.get('/district-boundaries')
def boundaries():
    path = Path(__file__).resolve().parents[3] / 'data' / 'districts.geojson'
    if not path.is_file():
        raise HTTPException(503, detail={'code': 'boundaries_unavailable'})
    return FileResponse(path, media_type='application/geo+json', headers={'Cache-Control': 'public, max-age=86400'})
