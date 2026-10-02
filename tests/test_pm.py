from datetime import date

import pytest

from eam.pm import PMState, PreventiveMaintenance, ScheduleType, evaluate, forecast, next_due_date


def pm(**kw) -> PreventiveMaintenance:
    base = dict(id="PM-P101-90D", asset_id="P101", job_plan="JP-PUMP-INSPECT", start_date=date(2026, 1, 1))
    base.update(kw)
    return PreventiveMaintenance(**base)


def test_floating_schedule_counts_from_last_completion():
    p = pm(frequency_days=30, schedule_type=ScheduleType.FLOATING)
    assert next_due_date(p, PMState()) == date(2026, 1, 1)
    # work done 10 days late: the next due date moves with it
    assert next_due_date(p, PMState(last_completed=date(2026, 1, 11), last_due=date(2026, 1, 1))) == date(
        2026, 2, 10
    )


def test_fixed_schedule_keeps_the_original_cadence():
    p = pm(frequency_days=30, schedule_type=ScheduleType.FIXED)
    late = PMState(last_completed=date(2026, 1, 11), last_due=date(2026, 1, 1))
    early = PMState(last_completed=date(2026, 1, 29), last_due=date(2026, 1, 31))
    assert next_due_date(p, late) == date(2026, 1, 31)
    assert next_due_date(p, early) == date(2026, 3, 2)


def test_generation_respects_lead_time_and_is_idempotent_by_due_date():
    p = pm(frequency_days=90, lead_days=7)
    state = PMState(last_completed=date(2026, 1, 1), last_due=date(2026, 1, 1))
    assert not evaluate(p, state, date(2026, 3, 22)).generate
    d = evaluate(p, state, date(2026, 3, 25))
    assert d.generate and d.due_date == date(2026, 4, 1)
    assert (
        d.idempotency_key == evaluate(p, state, date(2026, 3, 30)).idempotency_key == "PM-P101-90D:2026-04-01"
    )


def test_meter_based_and_whichever_first():
    p = pm(frequency_days=365, meter_interval=500.0)  # 500 running hours or yearly
    state = PMState(last_completed=date(2026, 1, 1), last_completed_meter=1_200.0, last_due=date(2026, 1, 1))
    assert not evaluate(p, state, date(2026, 2, 1), current_meter=1_650.0).generate
    hit = evaluate(p, state, date(2026, 2, 1), current_meter=1_710.0)
    assert hit.generate and hit.reason == "meter interval reached"
    assert hit.idempotency_key == evaluate(p, state, date(2026, 2, 2), current_meter=1_750.0).idempotency_key


def test_meter_only_pm_has_no_calendar_forecast():
    p = pm(meter_interval=250.0)
    assert next_due_date(p, PMState()) is None
    assert forecast(p, PMState(), 3) == []


def test_forecast():
    p = pm(frequency_days=30, start_date=date(2026, 1, 1))
    assert forecast(p, PMState(), 3) == [date(2026, 1, 1), date(2026, 1, 31), date(2026, 3, 2)]


@pytest.mark.parametrize(
    "kw", [{}, {"frequency_days": 0}, {"meter_interval": -1.0}, {"frequency_days": 7, "lead_days": -1}]
)
def test_invalid_pm_definitions(kw):
    with pytest.raises(ValueError):
        pm(**kw)
