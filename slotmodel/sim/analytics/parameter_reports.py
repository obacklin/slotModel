from __future__ import annotations
from dataclasses import dataclass, asdict

import numpy as np

from slotmodel.sim.eval import (
    PaylineEvaluator,
    scatter_bonus_trigger_mask,
)
from slotmodel.sim.paylines import PAYLINES
from slotmodel.sim.paytable import PAYTABLE
from slotmodel.sim.screens import ScreenModel, spin_batch
from slotmodel.sim.analytics import simulate_bonus_games

@dataclass(frozen=True, slots=True)
class ParameterReport:
    seed: int
    rtp_base: float
    rtp_bonus: float
    bonus_freq: float
    mean_bonus_payout: float

    payout_bands: PayoutBandProbs

    std_base: float
    std_bonus: float
    std_total: float

    bonus_freq_se: float
    mean_bonus_payout_se: float
    rtp_base_se: float
    rtp_bonus_se: float
    rtp_total_se: float

    total_base_spins: int
    bonus_entries: int
    total_bonus_games: int

    @property
    def rtp_total(self) -> float:
        return self.rtp_base + self.rtp_bonus
    
    def __str__(self) -> str:
        lines = [
            "=" * 50,
            "PARAMETER REPORT",
            "=" * 50,
            "",
            "RTP",
            "-" * 50,
            f"Base RTP:               {self.rtp_base:10.6f}",
            f"Bonus RTP:              {self.rtp_bonus:10.6f}",
            f"Total RTP:              {self.rtp_total:10.6f}",
            "",
            "BONUS",
            "-" * 50,
            f"Bonus frequency:        {self.bonus_freq:10.6f}",
            f"Mean bonus payout:      {self.mean_bonus_payout:10.6f}",
            "",
            "STANDARD DEVIATION",
            "-" * 50,
            f"Base:                   {self.std_base:10.6f}",
            f"Bonus:                  {self.std_bonus:10.6f}",
            f"Total:                  {self.std_total:10.6f}",
            "",
            "STANDARD ERRORS",
            "-" * 50,
            f"Bonus frequency SE:     {self.bonus_freq_se:10.6f}",
            f"Mean bonus payout SE:   {self.mean_bonus_payout_se:10.6f}",
            f"Base RTP SE:            {self.rtp_base_se:10.6f}",
            f"Bonus RTP SE:           {self.rtp_bonus_se:10.6f}",
            f"Total RTP SE:           {self.rtp_total_se:10.6f}",
            "",
            "PAYOUT BANDS",
            "-" * 50,
        ]

        for name, value in asdict(self.payout_bands).items():
            pretty_name = name.replace("_", " ").title()
            lines.append(f"{pretty_name:<25} {value:10.6f}")

        lines.extend([
            "",
            "SIMULATION",
            "-" * 50,
            f"Seed:                   {self.seed}",
            f"Base spins:             {self.total_base_spins:,}",
            f"Bonus entries:          {self.bonus_entries:,}",
            f"Bonus games simulated:  {self.total_bonus_games:,}",
            "=" * 50,
        ])

        return "\n".join(lines)


@dataclass(frozen = True, slots=True)
class PayoutBandProbs:
    p_0: float
    p_win: float
    p_0_to_1: float
    p_1_to_2: float
    p_2_to_5: float
    p_5_to_10: float
    p_over_10: float

    @property
    def band_sum(self) -> float:
        return(
            self.p_0
            + self.p_0_to_1
            + self.p_1_to_2
            + self.p_2_to_5
            + self.p_5_to_10
            + self.p_over_10
        )


def estimate_payout_bands(
        payouts: np.ndarray,
) -> PayoutBandProbs:

    return PayoutBandProbs(
        p_0=float(np.mean(payouts == 0.0)),
        p_win=float(np.mean(payouts > 0.0)),
        p_0_to_1=float(np.mean((payouts > 0.0) & (payouts <= 1.0))),
        p_1_to_2=float(np.mean((payouts > 1.0) & (payouts <= 2.0))),
        p_2_to_5=float(np.mean((payouts > 2.0) & (payouts <= 5.0))),
        p_5_to_10=float(np.mean((payouts > 5.0) & (payouts <= 10.0))),
        p_over_10=float(np.mean(payouts > 10.0))
    )


def sim_report(
    model: ScreenModel,
    total_spins: int,
    total_bonus_games: int,
    seed: int = 42,
    min_scatter: int = 3,
    initial_free_spins: int = 10,
    retrigger_free_spins: int = 10,
    max_win: float = 10_000.0,
) -> ParameterReport:

    if total_spins <= 0:
        raise ValueError("total_spins must be positive.")
    if total_bonus_games <= 0:
        raise ValueError("total_bonus_games must be positive.")
    if min_scatter <= 0:
        raise ValueError("min_scatter must be positive.")
    if initial_free_spins <= 0:
        raise ValueError("initial_free_spins must be positive.")
    if retrigger_free_spins <= 0:
        raise ValueError("retrigger_free_spins must be positive.")
    if not np.isfinite(max_win) or max_win <= 0.0:
        raise ValueError("max_win must be a positive finite value.")

    seed_seq = np.random.SeedSequence(seed)
    base_seed, bonus_seed = seed_seq.spawn(2)
    base_rng = np.random.default_rng(base_seed)
    bonus_rng = np.random.default_rng(bonus_seed)


    evaluator = PaylineEvaluator.from_definitions(
        paylines=PAYLINES,
        paytable=PAYTABLE,
        max_win=max_win
    )

    # Base game----------

    base_batch = spin_batch(
        model=model,
        batch_size=total_spins,
        rng=base_rng
    )
    base_evaluation = evaluator.evaluate(base_batch.screens)
    base_payouts = base_evaluation.total_multiplier_per_spin

    trigger_mask = scatter_bonus_trigger_mask(
        screens=base_batch.screens,
        min_scatter_count=min_scatter
    )

    bonus_entries = int(np.count_nonzero(trigger_mask))

    rtp_base = float(np.mean(base_payouts))
    bonus_freq = float(np.mean(trigger_mask))
    payout_bands = estimate_payout_bands(base_payouts)

    std_base = (
        float(np.std(base_payouts, ddof=1))
        if total_spins > 1
        else 0.0
    )

    rtp_base_se = float(std_base / np.sqrt(total_spins))

    bonus_freq_se = float(np.sqrt(
        bonus_freq * (1.0 - bonus_freq) / total_spins)
    )

    base_second_moment = float(
        np.mean(np.square(base_payouts, dtype=np.float64))
    )
    trigger_weighted_base_mean = float(
        np.mean(base_payouts * trigger_mask)
    )

    # Bonus game
    bonus_result = simulate_bonus_games(
        model=model,
        evaluator=evaluator,
        total_bonus_games=total_bonus_games,
        batch_size=total_bonus_games,
        rng=bonus_rng,
        initial_free_spins=initial_free_spins,
        retrigger_free_spins=retrigger_free_spins,
        min_scatter_count=min_scatter
    )

    bonus_payouts = bonus_result.payout_multipliers
    mean_bonus_payout = bonus_result.mean_payout_multiplier

    std_bonus = (
        float(np.std(bonus_payouts, ddof=1))
        if total_bonus_games > 1
        else 0.0
    )

    mean_bonus_payout_se = float(std_bonus / np.sqrt(total_bonus_games))

    rtp_bonus = bonus_freq * mean_bonus_payout

    # Bonus rtp standard error
    var_p_hat = bonus_freq_se**2
    var_mu_hat = mean_bonus_payout_se**2

    rtp_bonus_variance = (
        (mean_bonus_payout**2) * var_p_hat
        + (bonus_freq**2) * var_mu_hat
        + var_p_hat * var_mu_hat
    )
    rtp_bonus_se = float(np.sqrt(max(rtp_bonus_variance, 0.0)))

    # Complete one spin variance/volatility
    bonus_second_moment = float(
        np.mean(np.square(bonus_payouts,dtype=np.float64))
    )

    rtp_total = rtp_base + rtp_bonus

    total_second_moment = (
        base_second_moment 
        + 2.0 * trigger_weighted_base_mean * mean_bonus_payout
        + bonus_freq * bonus_second_moment
    )
    total_variance = max(total_second_moment - rtp_total**2, 0.0)
    std_total = float(np.sqrt(total_variance))

    # Standard error total RTP
    z = base_payouts + mean_bonus_payout * trigger_mask

    z_var = (
        float(np.var(z, ddof=1))
        if total_spins > 1
        else 0.0
    )

    expected_p_hat_squared = bonus_freq**2 + var_p_hat
    rtp_total_variance = (
        z_var / total_spins
        + expected_p_hat_squared * var_mu_hat
    )
    rtp_total_se = float(np.sqrt(max(rtp_total_variance, 0.0)))

    return ParameterReport(
        seed=seed,

        rtp_base=rtp_base,
        rtp_bonus=rtp_bonus,
        bonus_freq=bonus_freq,
        mean_bonus_payout=mean_bonus_payout,

        payout_bands=payout_bands,

        std_base=std_base,
        std_bonus=std_bonus,
        std_total=std_total,

        rtp_base_se=rtp_base_se,
        bonus_freq_se=bonus_freq_se,
        mean_bonus_payout_se=mean_bonus_payout_se,
        rtp_bonus_se=rtp_bonus_se,
        rtp_total_se=rtp_total_se,

        total_base_spins=total_spins,
        bonus_entries=bonus_entries,
        total_bonus_games=total_bonus_games,
    )
