from datetime import date

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class DistrictRent(Base):
    __tablename__ = "district_rents"
    __table_args__ = (UniqueConstraint("name", name="uq_district_rents_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    avg_rent_1room: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_rent_2room: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_rent_3room: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_utilities: Mapped[int] = mapped_column(Integer, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[date] = mapped_column(Date, nullable=False)


class RentSnapshot(Base):
    __tablename__ = "rent_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "city",
            "district_name",
            "captured_on",
            name="uq_rent_snapshots_city_district_captured_on",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Tallinn")
    district_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avg_rent_1room: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_rent_2room: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_rent_3room: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_utilities: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captured_on: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(500), nullable=False)
