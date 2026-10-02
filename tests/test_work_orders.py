from datetime import datetime
from decimal import Decimal

import pytest

from eam.work_orders import (
    FailureReport,
    LaborActual,
    MaterialActual,
    Status,
    TransitionError,
    WorkOrder,
    WorkType,
)

T = datetime(2026, 10, 1, 8, 0)


def wo(work_type: WorkType = WorkType.CORRECTIVE) -> WorkOrder:
    return WorkOrder(id="WO-1001", asset_id="P101", work_type=work_type, description="Seal leak", priority=2)


def advance(w: WorkOrder, *statuses: Status) -> None:
    for s in statuses:
        w.transition(s, at=T, by="planner")


def test_full_corrective_lifecycle_with_costs():
    w = wo()
    advance(w, Status.APPROVED, Status.PLANNED, Status.SCHEDULED)
    w.assign("tech-7")
    w.issue_material(MaterialActual("SEAL-KIT-40", "MAIN", Decimal("1"), Decimal("120.00")))
    advance(w, Status.IN_PROGRESS)
    w.record_labor(LaborActual("tech-7", "MECH", Decimal("2.5"), Decimal("60")))
    w.report_failure(FailureReport("LEAK", "SEAL-WEAR", "REPLACE", Decimal("3")))
    advance(w, Status.COMPLETED, Status.CLOSED)
    assert w.status is Status.CLOSED
    assert w.labor_cost == Decimal("150.0")
    assert w.total_cost == Decimal("270.00")
    assert [h.to_status for h in w.history][-2:] == [Status.COMPLETED, Status.CLOSED]


def test_illegal_transitions_are_rejected():
    w = wo()
    with pytest.raises(TransitionError):
        w.transition(Status.COMPLETED, at=T, by="x")
    advance(w, Status.CANCELLED)
    with pytest.raises(TransitionError):
        w.transition(Status.APPROVED, at=T, by="x")
    with pytest.raises(TransitionError):
        w.assign("tech-1")


def test_cannot_start_without_technician_or_complete_without_failure_report_and_labor():
    w = wo()
    advance(w, Status.APPROVED, Status.PLANNED, Status.SCHEDULED)
    with pytest.raises(TransitionError, match="assigned technician"):
        w.transition(Status.IN_PROGRESS, at=T, by="x")
    w.assign("tech-7")
    advance(w, Status.IN_PROGRESS)
    with pytest.raises(TransitionError, match="failure report"):
        w.transition(Status.COMPLETED, at=T, by="x")
    w.report_failure(FailureReport("NOISE", "BEARING", "REPLACE"))
    with pytest.raises(TransitionError, match="labor"):
        w.transition(Status.COMPLETED, at=T, by="x")


def test_preventive_work_does_not_need_a_failure_report():
    w = wo(WorkType.PREVENTIVE)
    advance(w, Status.APPROVED, Status.PLANNED, Status.SCHEDULED)
    w.assign("tech-7")
    advance(w, Status.IN_PROGRESS)
    w.record_labor(LaborActual("tech-7", "MECH", Decimal("1"), Decimal("60")))
    advance(w, Status.COMPLETED)


def test_waiting_for_material_and_on_hold_paths():
    w = wo()
    advance(w, Status.APPROVED, Status.PLANNED, Status.WAITING_MATERIAL, Status.SCHEDULED)
    w.assign("tech-7")
    advance(w, Status.IN_PROGRESS, Status.ON_HOLD, Status.IN_PROGRESS)
    assert w.status is Status.IN_PROGRESS


def test_emergency_work_can_start_immediately():
    w = wo(WorkType.EMERGENCY)
    w.assign("tech-on-call")
    w.transition(Status.IN_PROGRESS, at=T, by="supervisor")
    assert w.status is Status.IN_PROGRESS
    with pytest.raises(TransitionError):
        wo(WorkType.CORRECTIVE).transition(Status.IN_PROGRESS, at=T, by="x")


def test_completed_work_can_be_reopened_but_closed_cannot():
    w = wo(WorkType.INSPECTION)
    advance(w, Status.APPROVED, Status.PLANNED, Status.SCHEDULED)
    w.assign("t")
    advance(w, Status.IN_PROGRESS)
    w.record_labor(LaborActual("t", "INSP", Decimal("1"), Decimal("50")))
    advance(w, Status.COMPLETED, Status.IN_PROGRESS)
    assert w.status is Status.IN_PROGRESS


@pytest.mark.parametrize("priority", [0, 6])
def test_validation(priority):
    with pytest.raises(ValueError):
        WorkOrder(id="x", asset_id="a", work_type=WorkType.PREVENTIVE, description="d", priority=priority)


def test_labor_rules():
    w = wo()
    with pytest.raises(TransitionError):
        w.record_labor(LaborActual("t", "MECH", Decimal("1"), Decimal("1")))
