"""Reporting bounded context: standard maintenance KPIs.

Definitions follow common maintenance-management practice (e.g. SMRP-style metric definitions);
they are written out explicitly because teams frequently disagree on them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Failure:
    asset_id: str
    failed_at: datetime
    restored_at: datetime

    @property
    def repair_hours(self) -> float:
        return (self.restored_at - self.failed_at).total_seconds() / 3600


def mttr_hours(failures: Sequence[Failure]) -> float:
    """Mean Time To Repair: average downtime per failure."""
    if not failures:
        return 0.0
    return sum(f.repair_hours for f in failures) / len(failures)


def mtbf_hours(failures: Sequence[Failure], period_hours: float) -> float | None:
    """Mean Time Between Failures: operating (up) time in the period divided by the number of failures."""
    if not failures:
        return None  # undefined: no failures observed in the period
    uptime = period_hours - sum(f.repair_hours for f in failures)
    return uptime / len(failures)


def availability(failures: Sequence[Failure], period_hours: float) -> float:
    """Inherent availability = uptime / period."""
    if period_hours <= 0:
        raise ValueError("period_hours must be positive")
    downtime = sum(f.repair_hours for f in failures)
    return max(0.0, (period_hours - downtime) / period_hours)


@dataclass(frozen=True)
class PMOccurrence:
    due: date
    completed: date | None
    grace_days: int = 0


def pm_compliance(occurrences: Sequence[PMOccurrence]) -> float:
    """Share of PM work orders due in the period that were completed within their grace window."""
    if not occurrences:
        return 1.0
    on_time = sum(
        1 for o in occurrences if o.completed is not None and (o.completed - o.due).days <= o.grace_days
    )
    return on_time / len(occurrences)


def planned_maintenance_percentage(planned_hours: float, total_hours: float) -> float:
    """Planned (PM + PdM + planned CM) labor hours as a share of all maintenance labor hours."""
    if total_hours <= 0:
        return 0.0
    return planned_hours / total_hours


def backlog_weeks(backlog_estimated_hours: float, weekly_craft_capacity_hours: float) -> float:
    """Ready backlog expressed in crew-weeks; 2–4 weeks is a commonly cited healthy range."""
    if weekly_craft_capacity_hours <= 0:
        raise ValueError("capacity must be positive")
    return backlog_estimated_hours / weekly_craft_capacity_hours
