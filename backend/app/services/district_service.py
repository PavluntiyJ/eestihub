from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.housing import DistrictRent, RentSnapshot
from app.schemas.districts import DistrictContext, DistrictsResponse
from app.services.housing_data import DISTRICT_RENTS

# Application IDs remain stable across source refreshes and translations.
DISTRICT_IDS = dict(zip(
    [d.name for d in DISTRICT_RENTS],
    ['kesklinn', 'pohja-tallinn', 'kristiine', 'mustamae', 'lasnamae', 'haabersti', 'nomme', 'pirita'],
    strict=True,
))


def district_context(session: Session, rooms: int, today: date | None = None) -> DistrictsResponse:
    today = today or date.today()
    legacy = {d.name: d for d in session.scalars(select(DistrictRent)).all()}
    latest = {}
    for row in session.scalars(select(RentSnapshot).where(RentSnapshot.city == 'Tallinn')
                              .order_by(RentSnapshot.captured_on.desc(), RentSnapshot.id.desc())).all():
        latest.setdefault(row.district_name, row)
    if not legacy and not latest:
        raise LookupError('district data unavailable')
    rows = []
    for district in DISTRICT_RENTS:
        baseline = legacy.get(district.name)
        snapshot = latest.get(district.name)
        row = snapshot or baseline
        observed = snapshot.captured_on if snapshot else baseline.updated_at if baseline else None
        # A baseline date does not establish an observation or freshness.
        freshness = ('current' if 0 <= (today - observed).days <= 90 else 'stale') if snapshot else 'unknown'
        rows.append(DistrictContext(
            id=DISTRICT_IDS[district.name], name=district.name,
            longitude=district.lon, latitude=district.lat,
            rent=getattr(row, f'avg_rent_{rooms}room') if row else None,
            observed_on=observed, source_url=snapshot.source if snapshot else None,
            basis='published_aggregate' if snapshot else 'legacy_estimate' if baseline else 'unknown',
            freshness=freshness, legacy_utilities=baseline.avg_utilities if baseline else None,
        ))
    rows.sort(key=lambda d: (d.rent is None, d.rent or 0, d.name))
    return DistrictsResponse(rooms=rooms, districts=rows)
