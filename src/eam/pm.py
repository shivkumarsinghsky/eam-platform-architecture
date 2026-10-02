"""Maintenance Planning bounded context: preventive maintenance (PM) scheduling.

A PM defines recurring work for an asset. Two triggers are common and may be combined ("whichever first"):

- **time-based** – every N days. *Fixed* schedules are anchored to the original start date (due dates do not
  drift when work is late, typical for statutory inspections); *floating* schedules count from the last
  completion (avoids bunching when work is late, typical for wear-based tasks).
- **meter-based** – every N units of a meter (running hours, cycles, kilometres).

Work orders are generated ``lead_days`` before the due date, and generation is idempotent per (PM, due date).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


class ScheduleType(str, Enum):
    FIXED = "FIXED"
    FLOATING = "FLOATING"


@dataclass(frozen=True)
class PreventiveMaintenance:
    id: str
    asset_id: str
    job_plan: str
    start_date: date
    frequency_days: int | None = None
    schedule_type: ScheduleType = ScheduleType.FLOATING
    meter_interval: float | None = None
    lead_days: int = 7

    def __post_init__(self) -> None:
        if self.frequency_days is None and self.meter_interval is None:
            raise ValueError("a PM needs a time frequency, a meter interval, or both")
        if self.frequency_days is not None and self.frequency_days <= 0:
            raise ValueError("frequency_days must be positive")
        if self.meter_interval is not None and self.meter_interval <= 0:
            raise ValueError("meter_interval must be positive")
        if self.lead_days < 0:
            raise ValueError("lead_days cannot be negative")


@dataclass(frozen=True)
class PMState:
    """What the scheduler knows about the PM's history."""

    last_completed: date | None = None
    last_completed_meter: float | None = None
    #: Due date of the occurrence that was last completed (needed by FIXED schedules).
    last_due: date | None = None


def next_due_date(pm: PreventiveMaintenance, state: PMState) -> date | None:
    """Next calendar due date, or None for meter-only PMs."""
    if pm.frequency_days is None:
        return None
    freq = timedelta(days=pm.frequency_days)
    if pm.schedule_type is ScheduleType.FLOATING:
        return (state.last_completed or pm.start_date) + (freq if state.last_completed else timedelta(0))
    # FIXED: the next slot on the original cadence, independent of when the work was actually done.
    return pm.start_date if state.last_due is None else state.last_due + freq


def meter_due(pm: PreventiveMaintenance, state: PMState, current_meter: float | None) -> bool:
    if pm.meter_interval is None or current_meter is None:
        return False
    baseline = state.last_completed_meter or 0.0
    return current_meter - baseline >= pm.meter_interval


@dataclass(frozen=True)
class GenerationDecision:
    generate: bool
    due_date: date | None
    reason: str
    #: Natural key that makes work order generation idempotent.
    idempotency_key: str | None = None


def evaluate(
    pm: PreventiveMaintenance, state: PMState, today: date, current_meter: float | None = None
) -> GenerationDecision:
    """Should a work order be generated today? Time and meter triggers combine as 'whichever comes first'."""
    if meter_due(pm, state, current_meter):
        assert pm.meter_interval is not None
        # Key on the threshold crossed (not the reading), so repeated readings do not create duplicates.
        threshold = (state.last_completed_meter or 0.0) + pm.meter_interval
        return GenerationDecision(True, today, "meter interval reached", f"{pm.id}:meter:{threshold:g}")
    due = next_due_date(pm, state)
    if due is not None and today >= due - timedelta(days=pm.lead_days):
        return GenerationDecision(
            True, due, f"due {due.isoformat()} within lead time", f"{pm.id}:{due.isoformat()}"
        )
    return GenerationDecision(False, due, "not yet due")


def forecast(pm: PreventiveMaintenance, state: PMState, count: int) -> list[date]:
    """Projected calendar due dates, assuming each occurrence is completed on its due date."""
    if pm.frequency_days is None:
        return []
    dates: list[date] = []
    current = state
    for _ in range(count):
        due = next_due_date(pm, current)
        assert due is not None
        dates.append(due)
        current = PMState(last_completed=due, last_completed_meter=current.last_completed_meter, last_due=due)
    return dates
