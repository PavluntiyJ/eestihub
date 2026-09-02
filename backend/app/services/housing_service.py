from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.housing import DistrictRent as DistrictRentModel
from app.models.housing import RentSnapshot
from app.schemas.housing import (
    DistrictRent,
    DistrictRentTrend,
    HousingRentsResponse,
    HousingTrendsResponse,
    RentTrendPoint,
)
from app.services.housing_data import CITY


def get_housing_rents(session: Session) -> HousingRentsResponse:
    districts = list(
        session.scalars(select(DistrictRentModel).order_by(DistrictRentModel.name)).all()
    )
    legacy_updated_at = session.scalar(select(func.max(DistrictRentModel.updated_at)))

    if legacy_updated_at is None:
        raise LookupError("housing rents have not been seeded")

    snapshots = session.scalars(
        select(RentSnapshot)
        .where(RentSnapshot.city == CITY)
        .order_by(
            RentSnapshot.district_name,
            RentSnapshot.captured_on.desc(),
            RentSnapshot.id.desc(),
        )
    ).all()
    latest_by_district: dict[str, RentSnapshot] = {}
    for snapshot in snapshots:
        latest_by_district.setdefault(snapshot.district_name, snapshot)

    updated_at = max(
        (snapshot.captured_on for snapshot in latest_by_district.values()),
        default=legacy_updated_at,
    )

    response_districts: list[DistrictRent] = []
    for district in districts:
        snapshot = latest_by_district.get(district.name)
        response_districts.append(
            DistrictRent(
                name=district.name,
                avg_rent_1room=(
                    snapshot.avg_rent_1room
                    if snapshot is not None
                    else district.avg_rent_1room
                ),
                avg_rent_2room=(
                    snapshot.avg_rent_2room
                    if snapshot is not None
                    else district.avg_rent_2room
                ),
                avg_rent_3room=(
                    snapshot.avg_rent_3room
                    if snapshot is not None
                    else district.avg_rent_3room
                ),
                avg_utilities=(
                    snapshot.avg_utilities
                    if snapshot is not None and snapshot.avg_utilities is not None
                    else district.avg_utilities
                ),
                lat=district.lat,
                lon=district.lon,
            )
        )

    return HousingRentsResponse(
        city=CITY,
        updated_at=updated_at,
        districts=response_districts,
    )


def get_housing_trends(session: Session) -> HousingTrendsResponse:
    snapshots = session.scalars(
        select(RentSnapshot)
        .where(RentSnapshot.city == CITY)
        .order_by(RentSnapshot.district_name, RentSnapshot.captured_on)
    ).all()

    if not snapshots:
        raise LookupError("housing rent snapshots have not been ingested")

    by_district: dict[str, list[RentTrendPoint]] = defaultdict(list)
    for snapshot in snapshots:
        by_district[snapshot.district_name].append(
            RentTrendPoint(
                captured_on=snapshot.captured_on,
                avg_rent_1room=snapshot.avg_rent_1room,
                avg_rent_2room=snapshot.avg_rent_2room,
                avg_rent_3room=snapshot.avg_rent_3room,
                avg_utilities=snapshot.avg_utilities,
                source=snapshot.source,
            )
        )

    return HousingTrendsResponse(
        city=CITY,
        districts=[
            DistrictRentTrend(name=name, points=points)
            for name, points in by_district.items()
        ],
    )
