from __future__ import annotations

from dataclasses import dataclass

from slotmodel.sim.eval import DEFAULT_MAX_WIN, PaylineEvaluator
from slotmodel.sim.paylines import PAYLINES
from slotmodel.sim.paytable import PAYTABLE_HIGH_VOL, PAYTABLE_LOW_VOL, Paytable


@dataclass(frozen=True, slots=True)
class PaylineEvaluatorProfile:
    """Named paytable/evaluator configuration selectable at runtime."""

    name: str
    label: str
    paytable_name: str
    paytable: Paytable

    def build(self, *, max_win: float = DEFAULT_MAX_WIN) -> PaylineEvaluator:
        """Compile a fresh evaluator for this profile."""
        return PaylineEvaluator.from_definitions(
            paylines=PAYLINES,
            paytable=self.paytable,
            max_win=max_win,
            name=self.name,
            paytable_name=self.paytable_name,
        )


PAYLINE_EVALUATOR_PROFILES = (
    PaylineEvaluatorProfile(
        name="high_vol",
        label="High Volatility",
        paytable_name="PAYTABLE_HIGH_VOL",
        paytable=PAYTABLE_HIGH_VOL,
    ),
    PaylineEvaluatorProfile(
        name="low_vol",
        label="Low Volatility",
        paytable_name="PAYTABLE_LOW_VOL",
        paytable=PAYTABLE_LOW_VOL,
    ),
)

DEFAULT_PAYLINE_EVALUATOR_NAME = PAYLINE_EVALUATOR_PROFILES[0].name


def get_payline_evaluator_profile(name: str) -> PaylineEvaluatorProfile:
    """Resolve a serialized evaluator name to its runtime configuration."""
    normalized = str(name).strip().lower()
    for profile in PAYLINE_EVALUATOR_PROFILES:
        if profile.name == normalized:
            return profile

    allowed = ", ".join(profile.name for profile in PAYLINE_EVALUATOR_PROFILES)
    raise ValueError(
        f"Unknown payline evaluator {name!r}. Available evaluators: {allowed}."
    )
