from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class TransitFeed(Base):
    """One validated GTFS snapshot generation.

    Rows are never updated in place except checked_at on an idempotent
    re-check; old generations are retained, never pruned in M08.
    """

    __tablename__ = "transit_feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_last_modified: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agency_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    calendar_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    calendar_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    stop_count: Mapped[int] = mapped_column(Integer, nullable=False)
    route_count: Mapped[int] = mapped_column(Integer, nullable=False)
    trip_count: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_time_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    attribution: Mapped[str] = mapped_column(Text, nullable=False)
    data_license: Mapped[str] = mapped_column(String(64), nullable=False)
    license_url: Mapped[str] = mapped_column(String(500), nullable=False)
    transformation: Mapped[str] = mapped_column(Text, nullable=False)


class TransitState(Base):
    """Singleton row pointing at the active feed generation."""

    __tablename__ = "transit_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active_feed_id: Mapped[int | None] = mapped_column(
        ForeignKey("transit_feeds.id"), nullable=True
    )


class TransitStop(Base):
    __tablename__ = "transit_stops"
    __table_args__ = (
        UniqueConstraint("feed_id", "stop_id", name="uq_transit_stops_feed_stop"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_id: Mapped[int] = mapped_column(
        ForeignKey("transit_feeds.id"), nullable=False, index=True
    )
    # Opaque provider strings; leading zeros preserved, never coerced.
    stop_id: Mapped[str] = mapped_column(String(64), nullable=False)
    stop_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stop_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stop_lat: Mapped[float] = mapped_column(Float, nullable=False)
    stop_lon: Mapped[float] = mapped_column(Float, nullable=False)
    parent_station: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location_type: Mapped[str | None] = mapped_column(String(16), nullable=True)


class TransitRoute(Base):
    __tablename__ = "transit_routes"
    __table_args__ = (
        UniqueConstraint("feed_id", "route_id", name="uq_transit_routes_feed_route"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_id: Mapped[int] = mapped_column(
        ForeignKey("transit_feeds.id"), nullable=False, index=True
    )
    route_id: Mapped[str] = mapped_column(String(128), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    long_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    route_type: Mapped[int] = mapped_column(Integer, nullable=False)
    # Derived mode: tram, bus, trolleybus or other. Raw type retained.
    mode: Mapped[str] = mapped_column(String(16), nullable=False)


class TransitStopService(Base):
    """Deduplicated scheduled (stop, route, service) relationships."""

    __tablename__ = "transit_stop_services"
    __table_args__ = (
        UniqueConstraint(
            "feed_id",
            "stop_id",
            "route_id",
            "service_id",
            name="uq_transit_stop_services_all",
        ),
        Index("ix_transit_stop_services_feed_stop", "feed_id", "stop_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_id: Mapped[int] = mapped_column(
        ForeignKey("transit_feeds.id"), nullable=False, index=True
    )
    stop_id: Mapped[str] = mapped_column(String(64), nullable=False)
    route_id: Mapped[str] = mapped_column(String(128), nullable=False)
    service_id: Mapped[str] = mapped_column(String(128), nullable=False)


class TransitCalendar(Base):
    __tablename__ = "transit_calendars"
    __table_args__ = (
        UniqueConstraint(
            "feed_id", "service_id", name="uq_transit_calendars_feed_service"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_id: Mapped[int] = mapped_column(
        ForeignKey("transit_feeds.id"), nullable=False, index=True
    )
    service_id: Mapped[str] = mapped_column(String(128), nullable=False)
    monday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tuesday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    wednesday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    thursday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    friday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    saturday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sunday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)


class TransitCalendarException(Base):
    __tablename__ = "transit_calendar_exceptions"
    __table_args__ = (
        UniqueConstraint(
            "feed_id",
            "service_id",
            "exception_date",
            name="uq_transit_exceptions_feed_service_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_id: Mapped[int] = mapped_column(
        ForeignKey("transit_feeds.id"), nullable=False, index=True
    )
    service_id: Mapped[str] = mapped_column(String(128), nullable=False)
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    # 1 = added service, 2 = removed service.
    exception_type: Mapped[int] = mapped_column(Integer, nullable=False)
