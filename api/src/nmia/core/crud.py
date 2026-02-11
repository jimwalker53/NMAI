"""Generic CRUD utility functions for SQLAlchemy models."""

from __future__ import annotations

from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from nmia.core.db import Base

ModelT = TypeVar("ModelT", bound=Base)


def get_by_id(db: Session, model: type[ModelT], id: UUID) -> ModelT | None:
    """Retrieve a single record by its primary key (id column).

    Returns the model instance or ``None`` if not found.
    """
    return db.query(model).filter(model.id == id).first()


def get_all(
    db: Session,
    model: type[ModelT],
    filters: dict[str, Any] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ModelT]:
    """Retrieve a list of records with optional column-value filters.

    Parameters
    ----------
    db:
        Active database session.
    model:
        The SQLAlchemy model class to query.
    filters:
        Optional dict of ``{column_name: value}`` equality filters.
    limit:
        Maximum number of records to return (default 100).
    offset:
        Number of records to skip (default 0).
    """
    query = db.query(model)
    if filters:
        for column_name, value in filters.items():
            column = getattr(model, column_name, None)
            if column is not None:
                query = query.filter(column == value)
    return query.offset(offset).limit(limit).all()


def create(db: Session, model: type[ModelT], **kwargs: Any) -> ModelT:
    """Create a new record and flush it to the database.

    Returns the newly created model instance with its generated id.
    """
    instance = model(**kwargs)
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def update(db: Session, instance: ModelT, **kwargs: Any) -> ModelT:
    """Update fields on an existing model instance.

    Only keyword arguments whose keys match actual model attributes are applied.
    Returns the updated instance after committing the transaction.
    """
    for key, value in kwargs.items():
        if hasattr(instance, key):
            setattr(instance, key, value)
    db.commit()
    db.refresh(instance)
    return instance


def soft_delete(db: Session, instance: ModelT) -> ModelT:
    """Soft-delete a record by setting ``is_active=False`` if the model
    supports it.  If the model does not have an ``is_active`` column the
    instance is returned unchanged.

    Returns the updated instance.
    """
    if hasattr(instance, "is_active"):
        instance.is_active = False  # type: ignore[attr-defined]
        db.commit()
        db.refresh(instance)
    return instance
