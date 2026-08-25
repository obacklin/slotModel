from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from slotmodel.paths import REELS_CANDIDATES_DIR
from slotmodel.runtime_tools.payline_evaluators import (
    get_payline_evaluator_profile,
)
from slotmodel.sim.analytics import ParameterReport, sim_report
from slotmodel.sim.reels import read_reels
from slotmodel.sim.screens import ScreenModel


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Reel JSON to evaluate. For the GUI to discover the reel set automatically,
# this file must be directly inside config/reels/candidates.
REELS_PATH = REELS_CANDIDATES_DIR / "high_vol.json"

# Monte Carlo sample sizes.
BASE_SPINS = 5_000_000
BONUS_GAMES = 5_000_000

# Simulation settings.
SEED = 42
WINDOW_OFFSETS = np.asarray([0, 1, 2], dtype=np.int32)
MIN_SCATTER = 3
INITIAL_FREE_SPINS = 10
RETRIGGER_FREE_SPINS = 10
MAX_WIN = 10_000.0

# Explicitly choose the named evaluator used for this reel set. The name must
# match one of the profiles in slotmodel/runtime_tools/payline_evaluators.py.
PAYLINE_EVALUATOR = "high_vol"
EVALUATOR_PROFILE = get_payline_evaluator_profile(PAYLINE_EVALUATOR)
EVALUATOR = EVALUATOR_PROFILE.build(max_win=MAX_WIN)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _metric_values(report: ParameterReport) -> dict[str, float]:
    """Return the same derived metric set used by find_candidate.py."""

    base = report.payout_bands
    bonus = report.bonus_payout_bands

    return {
        "rtp_total": report.rtp_total,
        "rtp_base": report.rtp_base,
        "rtp_bonus": report.rtp_bonus,
        "bonus_freq": report.bonus_freq,
        "mean_bonus_payout": report.mean_bonus_payout,
        "mean_free_spins": report.mean_free_spins,
        "base_win_prob": base.p_win,
        "base_0_to_1_prob": base.p_0_to_1,
        "base_1_to_2_prob": base.p_1_to_2,
        "base_2_to_5_prob": base.p_2_to_5,
        "base_5_to_10_prob": base.p_5_to_10,
        "base_10_to_20_prob": base.p_10_to_20,
        "base_20_to_30_prob": base.p_20_to_30,
        "base_30_to_50_prob": base.p_30_to_50,
        "base_over_50_prob": base.p_over_50,
        "base_0_to_2_prob": base.p_0_to_1 + base.p_1_to_2,
        "base_0_to_5_prob": base.p_0_to_1 + base.p_1_to_2 + base.p_2_to_5,
        "base_5_to_20_prob": base.p_5_to_10 + base.p_10_to_20,
        "base_20_to_50_prob": base.p_20_to_30 + base.p_30_to_50,
        "base_over_10_prob": (
            base.p_10_to_20
            + base.p_20_to_30
            + base.p_30_to_50
            + base.p_over_50
        ),
        "bonus_win_prob": bonus.p_win,
        "bonus_0_to_10_prob": bonus.p_0_to_10,
        "bonus_10_to_25_prob": bonus.p_10_to_25,
        "bonus_25_to_50_prob": bonus.p_25_to_50,
        "bonus_50_to_100_prob": bonus.p_50_to_100,
        "bonus_100_to_250_prob": bonus.p_100_to_250,
        "bonus_250_to_500_prob": bonus.p_250_to_500,
        "bonus_500_to_1000_prob": bonus.p_500_to_1000,
        "bonus_over_1000_prob": bonus.p_over_1000,
        "bonus_over_50_prob": (
            bonus.p_50_to_100
            + bonus.p_100_to_250
            + bonus.p_250_to_500
            + bonus.p_500_to_1000
            + bonus.p_over_1000
        ),
        "bonus_over_100_prob": (
            bonus.p_100_to_250
            + bonus.p_250_to_500
            + bonus.p_500_to_1000
            + bonus.p_over_1000
        ),
        "bonus_over_250_prob": (
            bonus.p_250_to_500
            + bonus.p_500_to_1000
            + bonus.p_over_1000
        ),
    }


def _report_payload(report: ParameterReport, reels_path: Path) -> dict[str, Any]:
    """Build a payload compatible with gui/pages/statistics_page.py."""

    simulation = {
        "base_spins": BASE_SPINS,
        "bonus_games": BONUS_GAMES,
        "min_scatter": MIN_SCATTER,
        "initial_free_spins": INITIAL_FREE_SPINS,
        "retrigger_free_spins": RETRIGGER_FREE_SPINS,
        "max_win": MAX_WIN,
        "window_offsets": WINDOW_OFFSETS.tolist(),
    }

    return {
        "profile": reels_path.stem,
        "profile_path": str(reels_path),
        "paytable": EVALUATOR.paytable_name,
        "seed": SEED,
        "simulation": simulation,
        # These fields exist in find_candidate.py reports, but there is no GA
        # generation or target-fit score when evaluating a pre-existing set.
        "best_generation": None,
        "evaluation": {
            "score": None,
            "metrics": _metric_values(report),
            "normalized_errors": {},
            "targets": {},
            "report": asdict(report),
        },
    }


def main() -> None:
    reels_path = Path(REELS_PATH)
    if not reels_path.is_absolute():
        reels_path = PROJECT_ROOT / reels_path
    reels_path = reels_path.resolve()

    reels = read_reels(reels_path)

    if len(reels) != EVALUATOR.reel_count:
        raise ValueError(
            f"Evaluator expects {EVALUATOR.reel_count} reels, "
            f"but {reels_path} contains {len(reels)}."
        )

    model = ScreenModel.from_reels(
        reels=reels,
        window_offsets=WINDOW_OFFSETS,
    )

    print(f"Reels:       {reels_path}")
    print(f"Base spins:  {BASE_SPINS:,}")
    print(f"Bonus games: {BONUS_GAMES:,}")
    print(f"Evaluator:   {EVALUATOR.name}")
    print(f"Paytable:    {EVALUATOR.paytable_name}")

    report = sim_report(
        model=model,
        total_spins=BASE_SPINS,
        total_bonus_games=BONUS_GAMES,
        evaluator=EVALUATOR,
        seed=SEED,
        min_scatter=MIN_SCATTER,
        initial_free_spins=INITIAL_FREE_SPINS,
        retrigger_free_spins=RETRIGGER_FREE_SPINS,
        max_win=MAX_WIN,
    )

    report_path = reels_path.with_name(f"{reels_path.stem}_report.json")
    report_path.write_text(
        json.dumps(_report_payload(report, reels_path), indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n" + str(report))
    print(f"\nSaved report: {report_path}")

    if reels_path.parent != REELS_CANDIDATES_DIR.resolve():
        print(
            "Note: the report was generated successfully, but the GUI only "
            "auto-discovers reel JSON files directly inside "
            f"{REELS_CANDIDATES_DIR}."
        )


if __name__ == "__main__":
    main()