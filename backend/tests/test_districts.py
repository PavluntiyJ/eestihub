from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import get_session
from app.main import app
from app.models import Base
from app.models.housing import DistrictRent, RentSnapshot
from app.services.district_service import district_context, DISTRICT_IDS
from scripts.seed_housing import seed_housing


@pytest.fixture()
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_housing(session)
        app.dependency_overrides[get_session] = lambda: session
        try:
            yield session
        finally:
            app.dependency_overrides.clear()
    engine.dispose()


def test_district_rows_keep_sources_and_dates_per_row(db):
    for name, day, rent in [('Kesklinn', date(2026, 9, 1), 800), ('Lasnamäe', date(2026, 5, 1), 550)]:
        db.add(RentSnapshot(city='Tallinn', district_name=name, captured_on=day,
                            avg_rent_1room=rent, avg_rent_2room=rent+200, avg_rent_3room=rent+400,
                            avg_utilities=None, source='https://example.com/'+name))
    db.commit()
    response = district_context(db, 2, date(2026, 9, 29))
    rows = {d.id: d for d in response.districts}
    assert len(rows) == 8
    assert rows['kesklinn'].rent == 1000
    assert rows['kesklinn'].freshness == 'current'
    assert rows['lasnamae'].freshness == 'stale'
    assert rows['lasnamae'].observed_on == date(2026, 5, 1)
    assert rows['pirita'].basis == 'legacy_estimate'
    assert rows['pirita'].source_url is None
    assert rows['pirita'].freshness == 'unknown'
    assert rows['kesklinn'].legacy_utilities == 210
    assert response.districts == sorted(response.districts, key=lambda d: (d.rent, d.name))


def test_missing_district_stays_unknown_and_last(db):
    db.execute(delete(DistrictRent).where(DistrictRent.name == 'Lasnamäe'))
    db.commit()
    rows = district_context(db, 1).districts
    assert len(rows) == 8
    assert rows[-1].id == 'lasnamae'
    assert rows[-1].rent is None
    assert rows[-1].basis == 'unknown'


@pytest.mark.parametrize('rooms', [1, 2, 3])
def test_room_query_is_parsed_from_string(db, rooms):
    with TestClient(app) as client:
        response = client.get('/api/v1/planner/districts', params={'rooms': rooms})
    assert response.status_code == 200
    assert response.json()['rooms'] == rooms


@pytest.mark.parametrize('rooms', ['0', '4', '1.5', 'nan'])
def test_invalid_room_query(db, rooms):
    with TestClient(app) as client:
        assert client.get('/api/v1/planner/districts', params={'rooms': rooms}).status_code == 422


def test_empty_database_and_outage_are_unavailable(db):
    db.execute(delete(DistrictRent)); db.commit()
    with TestClient(app) as client:
        response = client.get('/api/v1/planner/districts')
        assert response.status_code == 503
        assert response.headers['cache-control'] == 'no-store'
        Base.metadata.drop_all(db.get_bind())
        assert client.get('/api/v1/planner/districts').status_code == 503


def test_boundaries_are_attributed_wgs84_and_match_district_ids():
    with TestClient(app) as client:
        response = client.get('/api/v1/planner/district-boundaries')
    assert response.status_code == 200
    data = response.json()
    assert data['type'] == 'FeatureCollection'
    assert {f['properties']['id'] for f in data['features']} == set(DISTRICT_IDS.values())
    assert data['attribution'] == 'Maa- ja Ruumiamet, EHAK 2026-09-02'
    assert len(data['source_sha256']) == 64
    def visit(coords):
        if isinstance(coords[0], (float, int)):
            lon, lat = coords
            assert 24.3 < lon < 25.1 and 59.2 < lat < 59.7
        else:
            for value in coords:
                visit(value)
    for feature in data['features']:
        assert feature['geometry']['type'] in ('Polygon', 'MultiPolygon')
        visit(feature['geometry']['coordinates'])
