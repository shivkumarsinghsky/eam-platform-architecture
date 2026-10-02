from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from eam.condition import ConditionRule, Reading
from eam.hierarchy import Hierarchy, Node
from eam.kpis import (
    Failure,
    PMOccurrence,
    availability,
    backlog_weeks,
    mtbf_hours,
    mttr_hours,
    planned_maintenance_percentage,
    pm_compliance,
)

PLANT = Hierarchy(
    [
        Node("SITE01", "SITE01", "North plant", "B"),
        Node("BOILER", "SITE01.BOILER", "Boiler house", "A"),
        Node("FW", "SITE01.BOILER.FW", "Feedwater system", "B"),
        Node("P101", "SITE01.BOILER.FW.P101", "Feed pump 101", "C"),
        Node("M101", "SITE01.BOILER.FW.P101.M101", "Motor 101", "C"),
        Node("HVAC", "SITE01.HVAC", "HVAC", "C"),
    ]
)


def test_descendants_and_ancestors():
    assert [n.id for n in PLANT.descendants("FW")] == ["FW", "P101", "M101"]
    assert [n.id for n in PLANT.descendants("FW", include_self=False)] == ["P101", "M101"]
    assert [n.id for n in PLANT.ancestors("M101")] == ["SITE01", "BOILER", "FW", "P101"]
    assert PLANT.node("M101").depth == 5


def test_cost_rollup():
    totals = PLANT.rollup({"M101": Decimal("400"), "P101": Decimal("100"), "HVAC": Decimal("50")})
    assert totals["FW"] == Decimal("500")
    assert totals["SITE01"] == Decimal("550")
    assert totals["HVAC"] == Decimal("50")


def test_criticality_is_inherited_from_the_most_critical_ancestor():
    assert PLANT.effective_criticality("M101") == "A"
    assert PLANT.effective_criticality("HVAC") == "B"


def test_hierarchy_validation():
    with pytest.raises(ValueError, match="parent"):
        Hierarchy([Node("X", "MISSING.X", "x")])
    with pytest.raises(ValueError, match="own id"):
        Hierarchy([Node("X", "Y", "x")])


def test_condition_rule_sustain_hysteresis_and_single_request():
    rule = ConditionRule(
        id="VIB-P101",
        asset_id="P101",
        measurement="vibration_mm_s",
        trigger_above=7.1,
        reset_below=4.5,
        sustain=timedelta(minutes=5),
        priority=2,
        description="High vibration",
    )
    t0 = datetime(2026, 10, 1, 8, 0)
    r = lambda minutes, v: Reading("P101", "vibration_mm_s", v, t0 + timedelta(minutes=minutes))  # noqa: E731
    assert rule.evaluate(r(0, 8.0)) is None  # breach starts
    assert rule.evaluate(r(2, 6.0)) is None  # dips below: sustain timer resets
    assert rule.evaluate(r(3, 8.2)) is None
    request = rule.evaluate(r(8, 8.4))
    assert request is not None and request.priority == 2
    assert rule.evaluate(r(9, 9.0)) is None  # already triggered
    assert rule.evaluate(r(10, 5.0)) is None  # inside hysteresis band: still triggered
    assert rule.evaluate(r(11, 4.0)) is None  # re-armed
    assert rule.evaluate(r(12, 7.5)) is None
    assert rule.evaluate(r(17, 7.6)) is not None
    assert rule.evaluate(Reading("P102", "vibration_mm_s", 99, t0)) is None


def test_condition_rule_requires_a_hysteresis_band():
    with pytest.raises(ValueError):
        ConditionRule(
            "r", "a", "m", trigger_above=5, reset_below=5, sustain=timedelta(0), priority=1, description="d"
        )


def test_reliability_kpis():
    t = datetime(2026, 10, 1)
    failures = [
        Failure("P101", t, t + timedelta(hours=4)),
        Failure("P101", t + timedelta(days=10), t + timedelta(days=10, hours=2)),
    ]
    period = 30 * 24.0
    assert mttr_hours(failures) == pytest.approx(3.0)
    assert mtbf_hours(failures, period) == pytest.approx((720 - 6) / 2)
    assert availability(failures, period) == pytest.approx(714 / 720)
    assert mtbf_hours([], period) is None
    assert mttr_hours([]) == 0.0


def test_planning_kpis():
    occ = [
        PMOccurrence(date(2026, 9, 1), date(2026, 9, 1)),
        PMOccurrence(date(2026, 9, 8), date(2026, 9, 12), grace_days=3),  # late
        PMOccurrence(date(2026, 9, 15), date(2026, 9, 17), grace_days=3),
        PMOccurrence(date(2026, 9, 22), None),  # not done
    ]
    assert pm_compliance(occ) == 0.5
    assert pm_compliance([]) == 1.0
    assert planned_maintenance_percentage(800, 1_000) == 0.8
    assert backlog_weeks(960, 320) == 3.0
    with pytest.raises(ValueError):
        backlog_weeks(1, 0)
