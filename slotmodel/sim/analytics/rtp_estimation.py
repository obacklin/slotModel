from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from slotmodel.sim.analytics.bonus_game import simulate_bonus_games
from slotmodel.sim.eval import PaylineEvaluator, scatter_bonus_trigger_mask
from slotmodel.sim.paylines import PAYLINES
from slotmodel.sim.paytable import PAYTABLE_HIGH_VOL
from slotmodel.sim.screens import ScreenModel, spin_batch


@dataclass(frozen=True, slots=True)
class AdaptiveSamplingStage:
    """Cumulative Monte Carlo effort for one adaptive RTP stage."""

    base_spins: int
    bonus_games: int

    def __post_init__(self) -> None:
        if self.base_spins <= 0:
            raise ValueError("base_spins must be positive.")
        if self.bonus_games <= 0:
            raise ValueError("bonus_games must be positive.")


@dataclass(frozen=True, slots=True)
class AdaptiveRtpEstimate:
    """RTP estimate produced by staged Monte Carlo simulation."""

    seed: int
    rtp_base: float
    rtp_bonus: float
    bonus_freq: float
    mean_bonus_payout: float
    rtp_total_se: float
    confidence_low: float
    confidence_high: float
    base_spins: int
    bonus_games: int
    stage_index: int
    stopped_early: bool
    stop_reason: str

    @property
    def rtp_total(self) -> float:
        return self.rtp_base + self.rtp_bonus


@dataclass(slots=True)
class _RunningRtpState:
    base_count: int = 0
    base_sum: float = 0.0
    base_sum_sq: float = 0.0
    trigger_count: int = 0
    trigger_weighted_base_sum: float = 0.0

    bonus_count: int = 0
    bonus_sum: float = 0.0
    bonus_sum_sq: float = 0.0

    def add_base(self, payouts: np.ndarray, trigger_mask: np.ndarray) -> None:
        payout_values = np.asarray(payouts, dtype=np.float64)
        triggers = np.asarray(trigger_mask, dtype=np.bool_)

        self.base_count += int(payout_values.size)
        self.base_sum += float(np.sum(payout_values, dtype=np.float64))
        self.base_sum_sq += float(
            np.sum(np.square(payout_values, dtype=np.float64), dtype=np.float64)
        )
        self.trigger_count += int(np.count_nonzero(triggers))
        self.trigger_weighted_base_sum += float(
            np.sum(payout_values[triggers], dtype=np.float64)
        )

    def add_bonus(self, payouts: np.ndarray) -> None:
        payout_values = np.asarray(payouts, dtype=np.float64)

        self.bonus_count += int(payout_values.size)
        self.bonus_sum += float(np.sum(payout_values, dtype=np.float64))
        self.bonus_sum_sq += float(
            np.sum(np.square(payout_values, dtype=np.float64), dtype=np.float64)
        )


def _sample_variance(count: int, total: float, total_sq: float) -> float:
    if count <= 1:
        return 0.0

    centered_sum_sq = total_sq - (total * total / count)
    return max(centered_sum_sq / (count - 1), 0.0)


def _validate_stages(
    stages: Iterable[AdaptiveSamplingStage],
) -> tuple[AdaptiveSamplingStage, ...]:
    resolved = tuple(stages)

    if not resolved:
        raise ValueError("At least one adaptive sampling stage is required.")

    previous_base = 0
    previous_bonus = 0

    for stage in resolved:
        if stage.base_spins <= previous_base:
            raise ValueError(
                "Adaptive stage base_spins must be strictly increasing."
            )
        if stage.bonus_games <= previous_bonus:
            raise ValueError(
                "Adaptive stage bonus_games must be strictly increasing."
            )

        previous_base = stage.base_spins
        previous_bonus = stage.bonus_games

    return resolved


def _estimate_from_state(
    state: _RunningRtpState,
    *,
    seed: int,
    confidence_z: float,
    stage_index: int,
    stopped_early: bool,
    stop_reason: str,
) -> AdaptiveRtpEstimate:
    if state.base_count <= 0 or state.bonus_count <= 0:
        raise RuntimeError("Adaptive RTP state is incomplete.")

    n_base = state.base_count
    n_bonus = state.bonus_count

    rtp_base = state.base_sum / n_base
    bonus_freq = state.trigger_count / n_base
    mean_bonus_payout = state.bonus_sum / n_bonus
    rtp_bonus = bonus_freq * mean_bonus_payout
    rtp_total = rtp_base + rtp_bonus

    bonus_variance = _sample_variance(
        n_bonus,
        state.bonus_sum,
        state.bonus_sum_sq,
    )
    mean_bonus_payout_variance = bonus_variance / n_bonus

    bonus_freq_variance = (
        bonus_freq * (1.0 - bonus_freq) / n_base
    )

    z_sum = state.base_sum + mean_bonus_payout * state.trigger_count
    z_sum_sq = (
        state.base_sum_sq
        + 2.0
        * mean_bonus_payout
        * state.trigger_weighted_base_sum
        + mean_bonus_payout**2 * state.trigger_count
    )
    z_variance = _sample_variance(n_base, z_sum, z_sum_sq)

    expected_p_hat_squared = bonus_freq**2 + bonus_freq_variance
    total_variance = (
        z_variance / n_base
        + expected_p_hat_squared * mean_bonus_payout_variance
    )
    rtp_total_se = float(np.sqrt(max(total_variance, 0.0)))

    confidence_delta = confidence_z * rtp_total_se

    return AdaptiveRtpEstimate(
        seed=seed,
        rtp_base=float(rtp_base),
        rtp_bonus=float(rtp_bonus),
        bonus_freq=float(bonus_freq),
        mean_bonus_payout=float(mean_bonus_payout),
        rtp_total_se=rtp_total_se,
        confidence_low=float(rtp_total - confidence_delta),
        confidence_high=float(rtp_total + confidence_delta),
        base_spins=n_base,
        bonus_games=n_bonus,
        stage_index=stage_index,
        stopped_early=stopped_early,
        stop_reason=stop_reason,
    )


def estimate_rtp_adaptive(
    model: ScreenModel,
    *,
    target_min: float,
    target_max: float,
    stages: Iterable[AdaptiveSamplingStage],
    seed: int = 42,
    confidence_z: float = 2.576,
    min_scatter: int = 3,
    initial_free_spins: int = 10,
    retrigger_free_spins: int = 10,
    max_win: float = 10_000.0,
    evaluator: PaylineEvaluator | None = None,
) -> AdaptiveRtpEstimate:
    """
    Estimate total RTP with cumulative Monte Carlo stages.

    A candidate stops after a non-final stage only when the confidence
    interval is wholly below or wholly above the target interval.  Any
    candidate whose interval still overlaps the target proceeds to the next
    cumulative stage.
    """

    resolved_stages = _validate_stages(stages)

    if not np.isfinite(target_min) or not np.isfinite(target_max):
        raise ValueError("Target RTP bounds must be finite.")
    if target_min > target_max:
        raise ValueError("target_min cannot exceed target_max.")
    if not np.isfinite(confidence_z) or confidence_z <= 0.0:
        raise ValueError("confidence_z must be a positive finite value.")
    if min_scatter <= 0:
        raise ValueError("min_scatter must be positive.")
    if initial_free_spins <= 0:
        raise ValueError("initial_free_spins must be positive.")
    if retrigger_free_spins <= 0:
        raise ValueError("retrigger_free_spins must be positive.")
    if not np.isfinite(max_win) or max_win <= 0.0:
        raise ValueError("max_win must be a positive finite value.")

    if evaluator is None:
        evaluator = PaylineEvaluator.from_definitions(
            paylines=PAYLINES,
            paytable=PAYTABLE_HIGH_VOL,
            max_win=max_win,
            name="high_vol",
            paytable_name="PAYTABLE_HIGH_VOL",
        )
    elif not np.isclose(evaluator.max_win, max_win):
        raise ValueError("evaluator.max_win must match max_win.")

    seed_seq = np.random.SeedSequence(seed)
    base_seed, bonus_seed = seed_seq.spawn(2)
    base_rng = np.random.default_rng(base_seed)
    bonus_rng = np.random.default_rng(bonus_seed)

    state = _RunningRtpState()
    completed_base = 0
    completed_bonus = 0

    for stage_index, stage in enumerate(resolved_stages):
        base_increment = stage.base_spins - completed_base
        bonus_increment = stage.bonus_games - completed_bonus

        base_batch = spin_batch(
            model=model,
            batch_size=base_increment,
            rng=base_rng,
        )
        base_evaluation = evaluator.evaluate(base_batch.screens)
        base_payouts = base_evaluation.total_multiplier_per_spin
        trigger_mask = scatter_bonus_trigger_mask(
            screens=base_batch.screens,
            min_scatter_count=min_scatter,
        )
        state.add_base(base_payouts, trigger_mask)

        bonus_result = simulate_bonus_games(
            model=model,
            evaluator=evaluator,
            total_bonus_games=bonus_increment,
            batch_size=bonus_increment,
            rng=bonus_rng,
            initial_free_spins=initial_free_spins,
            retrigger_free_spins=retrigger_free_spins,
            min_scatter_count=min_scatter,
        )
        state.add_bonus(bonus_result.payout_multipliers)

        completed_base = stage.base_spins
        completed_bonus = stage.bonus_games

        estimate = _estimate_from_state(
            state,
            seed=seed,
            confidence_z=confidence_z,
            stage_index=stage_index,
            stopped_early=False,
            stop_reason="max_samples",
        )

        is_final_stage = stage_index == len(resolved_stages) - 1
        if is_final_stage:
            return estimate

        if estimate.confidence_high < target_min:
            return _estimate_from_state(
                state,
                seed=seed,
                confidence_z=confidence_z,
                stage_index=stage_index,
                stopped_early=True,
                stop_reason="below_target",
            )

        if estimate.confidence_low > target_max:
            return _estimate_from_state(
                state,
                seed=seed,
                confidence_z=confidence_z,
                stage_index=stage_index,
                stopped_early=True,
                stop_reason="above_target",
            )

    raise RuntimeError("Adaptive RTP estimation did not produce a result.")