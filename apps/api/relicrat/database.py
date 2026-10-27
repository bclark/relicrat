"""Database session dependency for API routes."""
import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@lru_cache
def session_factory() -> sessionmaker[Session]:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for inventory operations")
    engine = create_engine(url, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with session_factory()() as session:
        yield session
