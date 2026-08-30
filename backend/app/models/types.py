"""Portable column type helpers."""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=Enum)


def enum_column(enum_cls: type[E], *, length: int = 32) -> SAEnum:
    """Store an enum as VARCHAR + CHECK using its *values*.

    ``native_enum=False`` keeps SQLite and Postgres in agreement, and
    ``values_callable`` means the DB holds ``"youtube_short"`` rather than the
    Python member name ``"YOUTUBE_SHORT"``.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda cls: [member.value for member in cls],
        validate_strings=True,
    )
