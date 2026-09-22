"""Read helpers over activated GTFS generations.

All reads capture one active generation ID first so a concurrent refresh
cannot mix generations inside a single result. Routes here mean scheduled
on the supplied service date, never live departures.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transit import (
    TransitCalendar,
    TransitCalendarException,
    TransitFeed,
    TransitRoute,
    TransitState,
    TransitStopService,
)
from app.services.transit_import import as_aware_utc

Freshness = Literal["current", "stale", "unknown"]

CHECK_STALE_AFTER = timedelta(days=7)
LAST_MODIFIED_STALE_AFTER = timedelta(days=30)
LAST_MODIFIED_FUTURE_TOLERANCE = timedelta(hours=24)

_WEEKDAY_ATTRS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def get_active_feed_id(session: Session) -> int | None:
    return session.scalar(select(TransitState.active_feed_id).where(TransitState.id == 1))


def get_active_feed(session: Session) -> TransitFeed | None:
    feed_id = get_active_feed_id(session)
    if feed_id is None:
        return None
    return session.get(TransitFeed, feed_id)


def routes_for_stop(
    session: Session, feed_id: int, stop_id: str, service_date: date
) -> list[TransitRoute]:
    """Routes scheduled at a stop on a service date.

    Calendar weekday/range matches plus added exceptions, minus removed
    exceptions, applied before deduplication. Route-less stops and stops
    with no service that day return an empty list. Deterministic
    route_id order; no timetable or arrival computation.
    """
    return routes_for_stops(session, feed_id, [stop_id], service_date)[stop_id]


def routes_for_stops(
    session: Session, feed_id: int, stop_ids: list[str], service_date: date
) -> dict[str, list[TransitRoute]]:
    """Batch nearby platforms so a remote database needs at most four queries."""
    result: dict[str, list[TransitRoute]] = {stop_id: [] for stop_id in stop_ids}
    if not stop_ids:
        return result
    associations = session.scalars(
        select(TransitStopService).where(
            TransitStopService.feed_id == feed_id,
            TransitStopService.stop_id.in_(stop_ids),
        )
    ).all()
    if not associations:
        return result
    candidate_services = {row.service_id for row in associations}
    calendars = {
        row.service_id: row
        for row in session.scalars(
            select(TransitCalendar).where(
                TransitCalendar.feed_id == feed_id,
                TransitCalendar.service_id.in_(candidate_services),
            )
        ).all()
    }
    exceptions: dict[tuple[str, date], int] = {}
    for row in session.scalars(
        select(TransitCalendarException).where(
            TransitCalendarException.feed_id == feed_id,
            TransitCalendarException.service_id.in_(candidate_services),
            TransitCalendarException.exception_date == service_date,
        )
    ).all():
        exceptions[(row.service_id, row.exception_date)] = row.exception_type
    active_services: set[str] = set()
    weekday = _WEEKDAY_ATTRS[service_date.weekday()]
    for service_id in candidate_services:
        calendar = calendars.get(service_id)
        runs = (
            calendar is not None
            and getattr(calendar, weekday)
            and calendar.start_date <= service_date <= calendar.end_date
        )
        exception = exceptions.get((service_id, service_date))
        if exception == 1:
            runs = True
        elif exception == 2:
            runs = False
        if runs:
            active_services.add(service_id)
    if not active_services:
        return result
    route_ids = sorted(
        {
            row.route_id
            for row in associations
            if row.service_id in active_services
        }
    )
    routes = session.scalars(
        select(TransitRoute).where(
            TransitRoute.feed_id == feed_id,
            TransitRoute.route_id.in_(route_ids),
        )
    ).all()
    by_id = {route.route_id: route for route in routes}
    for stop_id in stop_ids:
        ids = sorted({row.route_id for row in associations
                      if row.stop_id == stop_id and row.service_id in active_services})
        result[stop_id] = [by_id[route_id] for route_id in ids if route_id in by_id]
    return result


def feed_freshness(
    feed: TransitFeed, *, now_utc: datetime, today: date
) -> Freshness:
    """Our freshness policy over stored evidence, never over HTTP 200.

    Known stale evidence takes precedence over unknown metadata: an old
    successful check, an old source modification, or today outside the
    effective calendar envelope is stale even when the modification stamp
    itself is missing or futuristic. Unknown applies only when nothing
    proves staleness but the source modification time is missing or more
    than 24 hours in the future.
    """
    now = as_aware_utc(now_utc)
    checked = as_aware_utc(feed.checked_at)
    if now - checked > CHECK_STALE_AFTER:
        return "stale"
    last_modified = feed.source_last_modified
    if last_modified is not None:
        last_modified = as_aware_utc(last_modified)
        if last_modified <= now + LAST_MODIFIED_FUTURE_TOLERANCE:
            if now - last_modified > LAST_MODIFIED_STALE_AFTER:
                return "stale"
    if feed.calendar_start is not None and today < feed.calendar_start:
        return "stale"
    if feed.calendar_end is not None and today > feed.calendar_end:
        return "stale"
    if last_modified is None:
        return "unknown"
    if last_modified > now + LAST_MODIFIED_FUTURE_TOLERANCE:
        return "unknown"
    return "current"
