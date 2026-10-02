"""Monitoring bounded context: condition rules that turn telemetry into work requests.

Naive thresholding ("raise a work request whenever vibration > 7.1 mm/s") floods planners with duplicates from
noisy signals. This rule adds:

- **sustain** – the condition must hold for a minimum duration before it triggers;
- **hysteresis** – once triggered, the rule re-arms only after the value falls below a lower reset level;
- **one open request** – while triggered, further readings do not create more requests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Reading:
    asset_id: str
    measurement: str
    value: float
    at: datetime


@dataclass(frozen=True)
class WorkRequest:
    asset_id: str
    rule_id: str
    description: str
    priority: int
    raised_at: datetime


@dataclass
class ConditionRule:
    id: str
    asset_id: str
    measurement: str
    trigger_above: float
    reset_below: float
    sustain: timedelta
    priority: int
    description: str
    _breach_started: datetime | None = field(default=None, init=False)
    _triggered: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.reset_below >= self.trigger_above:
            raise ValueError("reset_below must be lower than trigger_above (hysteresis band)")

    def evaluate(self, reading: Reading) -> WorkRequest | None:
        if reading.asset_id != self.asset_id or reading.measurement != self.measurement:
            return None
        if self._triggered:
            if reading.value < self.reset_below:
                self._triggered = False
                self._breach_started = None
            return None
        if reading.value <= self.trigger_above:
            self._breach_started = None
            return None
        if self._breach_started is None:
            self._breach_started = reading.at
        if reading.at - self._breach_started >= self.sustain:
            self._triggered = True
            return WorkRequest(
                asset_id=self.asset_id,
                rule_id=self.id,
                description=f"{self.description}: {self.measurement}={reading.value} > {self.trigger_above}",
                priority=self.priority,
                raised_at=reading.at,
            )
        return None
