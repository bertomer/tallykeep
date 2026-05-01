"""SQLAlchemy declarative base.

All persistence models inherit from `Base`. Naming convention follows spec module 03:
table names are singular `snake_case` (e.g. `holding`, not `holdings`).
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Naming convention so Alembic generates stable index/constraint names across
# environments. Without this, autogenerate produces inconsistent identifiers.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
