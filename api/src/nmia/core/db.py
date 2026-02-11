"""SQLAlchemy engine, session factory, declarative base, and FastAPI dependency."""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from nmia.settings import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base: Any = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a transactional database session.

    The session is committed on success and rolled-back on exception, then
    always closed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
