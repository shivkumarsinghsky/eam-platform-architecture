"""Work Management bounded context: the work order lifecycle.

A work order (WO) is the unit of maintenance work. Its lifecycle is a state machine with guards that encode
common EAM business rules, for example:

- corrective work orders need a failure report (problem / cause / remedy codes) before completion,
- work can only start once it is scheduled and has an assigned technician (labor),
- a work order waiting for material (parts) cannot be started until the material arrives,
- closed and cancelled work orders are immutable (they feed cost and reliability history).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class WorkType(str, Enum):
    CORRECTIVE = "CM"  # fix a failure
    PREVENTIVE = "PM"  # scheduled, time- or meter-based
    PREDICTIVE = "PdM"  # triggered by condition monitoring
    INSPECTION = "INSP"
    EMERGENCY = "EM"


class Status(str, Enum):
    REQUESTED = "REQUESTED"  # work request raised by an operator or a monitoring rule
    APPROVED = "APPROVED"
    PLANNED = "PLANNED"  # job plan, labor and materials estimated
    WAITING_MATERIAL = "WAITING_MATERIAL"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"  # physical work done; actuals recorded
    CLOSED = "CLOSED"  # reviewed; costs final; history locked
    CANCELLED = "CANCELLED"


TRANSITIONS: dict[Status, set[Status]] = {
    Status.REQUESTED: {Status.APPROVED, Status.CANCELLED},
    Status.APPROVED: {Status.PLANNED, Status.CANCELLED},
    Status.PLANNED: {Status.SCHEDULED, Status.WAITING_MATERIAL, Status.CANCELLED},
    Status.WAITING_MATERIAL: {Status.PLANNED, Status.SCHEDULED, Status.CANCELLED},
    Status.SCHEDULED: {Status.IN_PROGRESS, Status.WAITING_MATERIAL, Status.PLANNED, Status.CANCELLED},
    Status.IN_PROGRESS: {Status.ON_HOLD, Status.COMPLETED},
    Status.ON_HOLD: {Status.IN_PROGRESS, Status.CANCELLED},
    Status.COMPLETED: {Status.CLOSED, Status.IN_PROGRESS},  # reopen if the fix did not hold
    Status.CLOSED: set(),
    Status.CANCELLED: set(),
}

# Emergency work skips approval and planning: raise → in progress immediately.
EMERGENCY_SHORTCUT = {Status.REQUESTED: {Status.IN_PROGRESS}}


class TransitionError(ValueError):
    """Raised when a status change or edit violates the lifecycle rules."""


@dataclass(frozen=True)
class FailureReport:
    """Problem / cause / remedy codes: the basis of reliability analysis (ISO 14224-style)."""

    problem_code: str
    cause_code: str
    remedy_code: str
    downtime_hours: Decimal = Decimal("0")


@dataclass(frozen=True)
class LaborActual:
    technician_id: str
    craft: str
    hours: Decimal
    rate: Decimal

    @property
    def cost(self) -> Decimal:
        return self.hours * self.rate


@dataclass(frozen=True)
class MaterialActual:
    item_number: str
    storeroom: str
    quantity: Decimal
    unit_cost: Decimal

    @property
    def cost(self) -> Decimal:
        return self.quantity * self.unit_cost


@dataclass(frozen=True)
class StatusChanged:
    work_order_id: str
    from_status: Status
    to_status: Status
    at: datetime
    by: str
    note: str | None = None


@dataclass
class WorkOrder:
    id: str
    asset_id: str
    work_type: WorkType
    description: str
    priority: int  # 1 (highest) .. 5
    status: Status = Status.REQUESTED
    assigned_to: str | None = None
    pm_id: str | None = None
    failure_report: FailureReport | None = None
    labor: list[LaborActual] = field(default_factory=list)
    materials: list[MaterialActual] = field(default_factory=list)
    history: list[StatusChanged] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 1 <= self.priority <= 5:
            raise ValueError("priority must be between 1 and 5")
        if not self.description.strip():
            raise ValueError("description is required")

    # ---- lifecycle -------------------------------------------------------------------------------------

    def transition(self, to: Status, *, at: datetime, by: str, note: str | None = None) -> StatusChanged:
        allowed = set(TRANSITIONS[self.status])
        if self.work_type is WorkType.EMERGENCY:
            allowed |= EMERGENCY_SHORTCUT.get(self.status, set())
        if to not in allowed:
            raise TransitionError(f"{self.id}: cannot move from {self.status.value} to {to.value}")
        self._check_guards(to)
        event = StatusChanged(self.id, self.status, to, at, by, note)
        self.status = to
        self.history.append(event)
        return event

    def _check_guards(self, to: Status) -> None:
        if to is Status.IN_PROGRESS and self.assigned_to is None:
            raise TransitionError("work cannot start without an assigned technician")
        if to is Status.COMPLETED:
            if self.work_type in (WorkType.CORRECTIVE, WorkType.EMERGENCY) and self.failure_report is None:
                raise TransitionError("corrective work requires a failure report (problem/cause/remedy)")
            if not self.labor:
                raise TransitionError("record labor actuals before completing the work order")

    # ---- edits -----------------------------------------------------------------------------------------

    def assign(self, technician_id: str) -> None:
        self._ensure_editable()
        self.assigned_to = technician_id

    def record_labor(self, actual: LaborActual) -> None:
        if self.status not in (Status.IN_PROGRESS, Status.COMPLETED):
            raise TransitionError("labor can only be recorded for work in progress or completed")
        if actual.hours <= 0:
            raise ValueError("labor hours must be positive")
        self.labor.append(actual)

    def issue_material(self, actual: MaterialActual) -> None:
        if self.status not in (Status.SCHEDULED, Status.IN_PROGRESS, Status.COMPLETED):
            raise TransitionError("materials are issued to scheduled or active work only")
        self.materials.append(actual)

    def report_failure(self, report: FailureReport) -> None:
        self._ensure_editable()
        self.failure_report = report

    def _ensure_editable(self) -> None:
        if self.status in (Status.CLOSED, Status.CANCELLED):
            raise TransitionError(f"{self.id} is {self.status.value} and can no longer be changed")

    # ---- costs -----------------------------------------------------------------------------------------

    @property
    def labor_cost(self) -> Decimal:
        return sum((a.cost for a in self.labor), Decimal("0"))

    @property
    def material_cost(self) -> Decimal:
        return sum((m.cost for m in self.materials), Decimal("0"))

    @property
    def total_cost(self) -> Decimal:
        return self.labor_cost + self.material_cost
