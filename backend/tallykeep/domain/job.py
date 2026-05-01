"""Job domain type (spec module 02)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from tallykeep.domain.enums import JobStatus


@dataclass
class Job:
    id: UUID
    job_type: str
    status: JobStatus
    parameters: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
