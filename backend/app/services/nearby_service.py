"""Distance to individual GTFS platforms; no walking times or live arrivals."""

from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transit import TransitStop
from app.schemas.transit import NearbyRoute, NearbyStop, NearbyTransitResponse, TransitProvenance
from app.services.transit_data import feed_freshness, get_active_feed, routes_for_stops
from app.services.transit_import import as_aware_utc

RADIUS_M = 800
MAX_STOPS = 20
EARTH_RADIUS_M = 6_371_008.8


def distance_m(lat: float, lon: float, stop_lat: float, stop_lon: float) -> float:
    a = sin(radians(stop_lat - lat) / 2) ** 2 + cos(radians(lat)) * cos(
        radians(stop_lat)
    ) * sin(radians(stop_lon - lon) / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(min(1.0, max(0.0, a))))


def get_nearby(session: Session, lat: float, lon: float, *, now: datetime | None = None) -> NearbyTransitResponse:
    now = as_aware_utc(now or datetime.now(timezone.utc))
    today = now.astimezone(ZoneInfo("Europe/Tallinn")).date()
    feed = get_active_feed(session)
    if feed is None:
        raise LookupError("No active transit feed")
    # Capture one generation for every read. The box is a coarse query bound;
    # exact great-circle distance below decides inclusion, before rounding.
    stops = session.scalars(select(TransitStop).where(
        TransitStop.feed_id == feed.id,
        TransitStop.stop_lat.between(lat - 0.008, lat + 0.008),
        TransitStop.stop_lon.between(lon - 0.016, lon + 0.016),
        (TransitStop.location_type.is_(None)) | (TransitStop.location_type == "0"),
    )).all()
    ranked = sorted(
        ((distance_m(lat, lon, stop.stop_lat, stop.stop_lon), stop) for stop in stops),
        key=lambda item: (item[0], item[1].stop_id),
    )
    closest = [(distance, stop) for distance, stop in ranked if distance <= RADIUS_M][:MAX_STOPS]
    scheduled = routes_for_stops(session, feed.id, [stop.stop_id for _, stop in closest], today)
    result = []
    for distance, stop in closest:
        result.append(NearbyStop(
            id=stop.stop_id, name=stop.stop_name, longitude=stop.stop_lon,
            latitude=stop.stop_lat, straight_line_distance_m=round(distance),
            routes=[NearbyRoute(id=r.route_id, short_name=r.short_name,
                                long_name=r.long_name, mode=r.mode)
                    for r in scheduled[stop.stop_id]],
        ))
    return NearbyTransitResponse(service_date=today, stops=result, feed=TransitProvenance(
        source_url=feed.source_url, attribution=feed.attribution,
        license_url=feed.license_url, data_license=feed.data_license,
        transformation=feed.transformation,
        fetched_at=as_aware_utc(feed.fetched_at), checked_at=as_aware_utc(feed.checked_at),
        source_last_modified=as_aware_utc(feed.source_last_modified) if feed.source_last_modified else None,
        calendar_start=feed.calendar_start, calendar_end=feed.calendar_end,
        freshness=feed_freshness(feed, now_utc=now, today=today),
    ))
