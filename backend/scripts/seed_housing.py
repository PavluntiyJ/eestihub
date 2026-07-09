from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, engine
from app.models import Base
from app.models.housing import DistrictRent
from app.services.housing_data import DISTRICT_RENTS, UPDATED_AT


def seed_housing(session: Session) -> None:
    updated_at = date.fromisoformat(UPDATED_AT)

    for district in DISTRICT_RENTS:
        existing = session.scalar(select(DistrictRent).where(DistrictRent.name == district.name))

        if existing is None:
            session.add(DistrictRent(**district._asdict(), updated_at=updated_at))
            continue

        existing.avg_rent_1room = district.avg_rent_1room
        existing.avg_rent_2room = district.avg_rent_2room
        existing.avg_rent_3room = district.avg_rent_3room
        existing.avg_utilities = district.avg_utilities
        existing.lat = district.lat
        existing.lon = district.lon
        existing.updated_at = updated_at

    session.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        seed_housing(session)


if __name__ == "__main__":
    main()
