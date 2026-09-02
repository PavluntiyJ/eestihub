from collections.abc import Generator
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


DATABASE_POOL_RECYCLE_SECONDS = 300


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_recycle=DATABASE_POOL_RECYCLE_SECONDS,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def get_session() -> Generator[Session, None, None]:
    with get_session_factory()() as session:
        yield session


# Keep the seed script's public imports lazy without constructing the engine
# when the FastAPI application imports this module.
def __getattr__(name: str) -> Any:
    if name == "engine":
        return get_engine()
    if name == "SessionLocal":
        return get_session_factory()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    engine: Engine
    SessionLocal: sessionmaker[Session]
