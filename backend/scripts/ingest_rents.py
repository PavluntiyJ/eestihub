import csv
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, engine
from app.models import Base
from app.models.housing import RentSnapshot


DATA_FILE = Path(__file__).parent / "data" / "rent_snapshots.csv"
REQUIRED_COLUMNS = {
    "city",
    "district_name",
    "captured_on",
    "avg_rent_1room",
    "avg_rent_2room",
    "avg_rent_3room",
    "avg_utilities",
    "source",
}


def _positive_int(value: str, field_name: str, line_number: int) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"line {line_number}: {field_name} must be an integer") from exc

    if parsed <= 0:
        raise ValueError(f"line {line_number}: {field_name} must be positive")
    return parsed


def _optional_positive_int(value: str, field_name: str, line_number: int) -> int | None:
    if not value.strip():
        return None
    return _positive_int(value, field_name, line_number)


def ingest_rents(session: Session, csv_path: Path = DATA_FILE) -> None:
    with csv_path.open(encoding="utf-8", newline="") as source_file:
        reader = csv.DictReader(source_file)
        if reader.fieldnames is None or set(reader.fieldnames) != REQUIRED_COLUMNS:
            raise ValueError("rent snapshot CSV has unexpected columns")

        for line_number, row in enumerate(reader, start=2):
            city = row["city"].strip()
            district_name = row["district_name"].strip()
            source = row["source"].strip()
            if not city or not district_name or not source:
                raise ValueError(
                    f"line {line_number}: city, district_name and source are required"
                )

            try:
                captured_on = date.fromisoformat(row["captured_on"].strip())
            except ValueError as exc:
                raise ValueError(
                    f"line {line_number}: captured_on must be an ISO date"
                ) from exc

            values = {
                "avg_rent_1room": _positive_int(
                    row["avg_rent_1room"], "avg_rent_1room", line_number
                ),
                "avg_rent_2room": _positive_int(
                    row["avg_rent_2room"], "avg_rent_2room", line_number
                ),
                "avg_rent_3room": _positive_int(
                    row["avg_rent_3room"], "avg_rent_3room", line_number
                ),
                "avg_utilities": _optional_positive_int(
                    row["avg_utilities"], "avg_utilities", line_number
                ),
                "source": source,
            }
            existing = session.scalar(
                select(RentSnapshot).where(
                    RentSnapshot.city == city,
                    RentSnapshot.district_name == district_name,
                    RentSnapshot.captured_on == captured_on,
                )
            )

            if existing is None:
                session.add(
                    RentSnapshot(
                        city=city,
                        district_name=district_name,
                        captured_on=captured_on,
                        **values,
                    )
                )
                session.flush()
                continue

            for field_name, value in values.items():
                setattr(existing, field_name, value)

    session.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        ingest_rents(session)


if __name__ == "__main__":
    main()
