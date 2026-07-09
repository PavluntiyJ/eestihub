from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.housing import DistrictRent as DistrictRentModel
from app.schemas.housing import DistrictRent, HousingRentsResponse
from app.services.housing_data import CITY


def get_housing_rents(session: Session) -> HousingRentsResponse:
    districts = list(
        session.scalars(select(DistrictRentModel).order_by(DistrictRentModel.name)).all()
    )
    updated_at = session.scalar(select(func.max(DistrictRentModel.updated_at)))

    if updated_at is None:
        raise LookupError("housing rents have not been seeded")

    return HousingRentsResponse(
        city=CITY,
        updated_at=updated_at,
        districts=[
            DistrictRent(
                name=district.name,
                avg_rent_1room=district.avg_rent_1room,
                avg_rent_2room=district.avg_rent_2room,
                avg_rent_3room=district.avg_rent_3room,
                avg_utilities=district.avg_utilities,
                lat=district.lat,
                lon=district.lon,
            )
            for district in districts
        ],
    )
