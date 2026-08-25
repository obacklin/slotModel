from __future__ import annotations

import numpy as np

from slotmodel.runtime_tools import (
    PAYLINE_EVALUATOR_PROFILES,
    get_payline_evaluator_profile,
)


def test_named_evaluator_profiles_build_with_paytable_metadata() -> None:
    assert [profile.name for profile in PAYLINE_EVALUATOR_PROFILES] == [
        "high_vol",
        "low_vol",
    ]

    high = get_payline_evaluator_profile("high_vol").build()
    low = get_payline_evaluator_profile("low_vol").build()

    assert high.name == "high_vol"
    assert high.paytable_name == "PAYTABLE_HIGH_VOL"
    assert low.name == "low_vol"
    assert low.paytable_name == "PAYTABLE_LOW_VOL"
    assert not np.array_equal(high.payout_matrix, low.payout_matrix)
