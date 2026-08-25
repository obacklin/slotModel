from __future__ import annotations
from dataclasses import dataclass, asdict

import numpy as np

from slotmodel.sim.eval import (
    PaylineEvaluator,
    scatter_bonus_trigger_mask,
)
from slotmodel.sim.paylines import PAYLINES
from slotmodel.sim.screens import ScreenModel, spin_batch
from slotmodel.sim.analytics.bonus_game import simulate_bonus_games


@dataclass(frozen=True, slots=True)
class PayoutBandProbs:
    p_0: float
    p_win: float
    p_0_to_1: float
    p_1_to_2: float
    p_2_to_5: float
    p_5_to_10: float
    p_10_to_20: float
    p_20_to_30: float
    p_30_to_50: float
    p_over_50: float

    @property
    def band_sum(self) -> float:
        return (
            self.p_0
            + self.p_0_to_1
            + self.p_1_to_2
            + self.p_2_to_5
            + self.p_5_to_10
            + self.p_10_to_20
            + self.p_20_to_30
            + self.p_30_to_50
            + self.p_over_50
        )


@dataclass(frozen=True, slots=True)
class BonusPayoutBandProbs:
    p_0: float
    p_win: float
    p_0_to_10: float
    p_10_to_25: float
    p_25_to_50: float
    p_50_to_100: float
    p_100_to_250: float
    p_250_to_500: float
    p_500_to_1000: float
    p_over_1000: float

    @property
    def band_sum(self) -> float:
        return (
            self.p_0
            + self.p_0_to_10
            + self.p_10_to_25
            + self.p_25_to_50
            + self.p_50_to_100
            + self.p_100_to_250
            + self.p_250_to_500
            + self.p_500_to_1000
            + self.p_over_1000
        )


@dataclass(frozen=True, slots=True)
class TailStatistics:
    p95: float
    p99: float
    p999: float
    max_observed: float
    max_win_freq: float


@dataclass(frozen=True, slots=True)
class ParameterReport:
    seed: int
    payline_evaluator_name: str
    paytable_name: str
    rtp_base: float
    rtp_bonus: float
    bonus_freq: float
    mean_bonus_payout: float
    mean_free_spins: float

    payout_bands: PayoutBandProbs
    bonus_payout_bands: BonusPayoutBandProbs

    base_tail: TailStatistics
    bonus_tail: TailStatistics

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
            f"Payline evaluator:      {self.payline_evaluator_name}",
            f"Paytable:               {self.paytable_name}",
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
            f"Mean free spins:        {self.mean_free_spins:10.6f}",
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
            "BASE PAYOUT BANDS",
            "-" * 50,
        ]

        for name, value in asdict(self.payout_bands).items():
            pretty_name = name.replace("_", " ").title()
            lines.append(f"{pretty_name:<25} {value:10.6f}")

        lines.extend([
            "",
            "BONUS PAYOUT BANDS",
            "-" * 50,
        ])

        for name, value in asdict(self.bonus_payout_bands).items():
            pretty_name = name.replace("_", " ").title()
            lines.append(f"{pretty_name:<25} {value:10.6f}")

        lines.extend([
            "",
            "TAIL STATISTICS",
            "-" * 50,
            f"Base p95:               {self.base_tail.p95:10.6f}",
            f"Base p99:               {self.base_tail.p99:10.6f}",
            f"Base p99.9:             {self.base_tail.p999:10.6f}",
            f"Base max observed:      {self.base_tail.max_observed:10.6f}",
            f"Base max-win frequency: {self.base_tail.max_win_freq:10.6f}",
            f"Bonus p95:              {self.bonus_tail.p95:10.6f}",
            f"Bonus p99:              {self.bonus_tail.p99:10.6f}",
            f"Bonus p99.9:            {self.bonus_tail.p999:10.6f}",
            f"Bonus max observed:     {self.bonus_tail.max_observed:10.6f}",
            f"Bonus max-win frequency:{self.bonus_tail.max_win_freq:10.6f}",
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


def estimate_payout_bands(
    payouts: np.ndarray,
) -> PayoutBandProbs:
    return PayoutBandProbs(
        p_0=float(np.mean(payouts == 0.0)),
        p_win=float(np.mean(payouts > 0.0)),
        p_0_to_1=float(np.mean((payouts > 0.0) & (payouts < 1.0))),
        p_1_to_2=float(np.mean((payouts >= 1.0) & (payouts < 2.0))),
        p_2_to_5=float(np.mean((payouts >= 2.0) & (payouts < 5.0))),
        p_5_to_10=float(np.mean((payouts >= 5.0) & (payouts < 10.0))),
        p_10_to_20=float(np.mean((payouts >= 10.0) & (payouts < 20.0))),
        p_20_to_30=float(np.mean((payouts >= 20.0) & (payouts < 30.0))),
        p_30_to_50=float(np.mean((payouts >= 30.0) & (payouts < 50.0))),
        p_over_50=float(np.mean(payouts >= 50.0)),
    )


def estimate_bonus_payout_bands(
    payouts: np.ndarray,
) -> BonusPayoutBandProbs:
    return BonusPayoutBandProbs(
        p_0=float(np.mean(payouts == 0.0)),
        p_win=float(np.mean(payouts > 0.0)),
        p_0_to_10=float(np.mean((payouts > 0.0) & (payouts < 10.0))),
        p_10_to_25=float(np.mean((payouts >= 10.0) & (payouts < 25.0))),
        p_25_to_50=float(np.mean((payouts >= 25.0) & (payouts < 50.0))),
        p_50_to_100=float(np.mean((payouts >= 50.0) & (payouts < 100.0))),
        p_100_to_250=float(np.mean((payouts >= 100.0) & (payouts < 250.0))),
        p_250_to_500=float(np.mean((payouts >= 250.0) & (payouts < 500.0))),
        p_500_to_1000=float(np.mean((payouts >= 500.0) & (payouts < 1000.0))),
        p_over_1000=float(np.mean(payouts >= 1000.0)),
    )


def estimate_tail_statistics(
    payouts: np.ndarray,
    max_win: float,
) -> TailStatistics:
    p95, p99, p999 = np.quantile(
        payouts,
        [0.95, 0.99, 0.999],
    )

    return TailStatistics(
        p95=float(p95),
        p99=float(p99),
        p999=float(p999),
        max_observed=float(np.max(payouts)),
        max_win_freq=float(np.mean(payouts >= max_win)),
    )


def sim_report(
    model: ScreenModel,
    total_spins: int,
    total_bonus_games: int,
    evaluator: PaylineEvaluator,
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

    if not np.isclose(evaluator.max_win, max_win):
        raise ValueError("evaluator.max_win must match max_win.")

    # Base game
    base_batch = spin_batch(
        model=model,
        batch_size=total_spins,
        rng=base_rng,
    )
    base_evaluation = evaluator.evaluate(base_batch.screens)
    base_payouts = base_evaluation.total_multiplier_per_spin

    trigger_mask = scatter_bonus_trigger_mask(
        screens=base_batch.screens,
        min_scatter_count=min_scatter,
    )

    bonus_entries = int(np.count_nonzero(trigger_mask))

    rtp_base = float(np.mean(base_payouts))
    bonus_freq = float(np.mean(trigger_mask))
    payout_bands = estimate_payout_bands(base_payouts)
    base_tail = estimate_tail_statistics(base_payouts, max_win=max_win)

    std_base = (
        float(np.std(base_payouts, ddof=1))
        if total_spins > 1
        else 0.0
    )

    rtp_base_se = float(std_base / np.sqrt(total_spins))

    bonus_freq_se = float(np.sqrt(
        bonus_freq * (1.0 - bonus_freq) / total_spins
    ))

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
        min_scatter_count=min_scatter,
    )

    bonus_payouts = bonus_result.payout_multipliers
    mean_bonus_payout = bonus_result.mean_payout_multiplier
    mean_free_spins = float(np.mean(bonus_result.free_spin_counts))

    bonus_payout_bands = estimate_bonus_payout_bands(bonus_payouts)
    bonus_tail = estimate_tail_statistics(bonus_payouts, max_win=max_win)

    std_bonus = (
        float(np.std(bonus_payouts, ddof=1))
        if total_bonus_games > 1
        else 0.0
    )

    mean_bonus_payout_se = float(std_bonus / np.sqrt(total_bonus_games))

    rtp_bonus = bonus_freq * mean_bonus_payout

    # Bonus RTP standard error
    var_p_hat = bonus_freq_se**2
    var_mu_hat = mean_bonus_payout_se**2

    rtp_bonus_variance = (
        (mean_bonus_payout**2) * var_p_hat
        + (bonus_freq**2) * var_mu_hat
        + var_p_hat * var_mu_hat
    )
    rtp_bonus_se = float(np.sqrt(max(rtp_bonus_variance, 0.0)))

    # Complete one-spin variance/volatility
    bonus_second_moment = float(
        np.mean(np.square(bonus_payouts, dtype=np.float64))
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
        payline_evaluator_name=evaluator.name,
        paytable_name=evaluator.paytable_name,
        rtp_base=rtp_base,
        rtp_bonus=rtp_bonus,
        bonus_freq=bonus_freq,
        mean_bonus_payout=mean_bonus_payout,
        mean_free_spins=mean_free_spins,
        payout_bands=payout_bands,
        bonus_payout_bands=bonus_payout_bands,
        base_tail=base_tail,
        bonus_tail=bonus_tail,
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