from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from slotmodel.optim.optimizer import (
    FitnessEvaluation,
    Optimizer,
    OptimizerConfig,
)
from slotmodel.sim.analytics import ParameterReport, sim_report  
from slotmodel.sim.eval import PaylineEvaluator  
from slotmodel.sim.paylines import PAYLINES  
from slotmodel.sim.paytable import PAYTABLE  
from slotmodel.sim.reels import read_reels  
from slotmodel.sim.reels.gen_reels import save_reels  
from slotmodel.sim.screens import ScreenModel  

TARGETS_DIR = PROJECT_ROOT / "config" / "targets"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "config" / "reels" / "candidates"
WINDOW_OFFSETS = np.asarray([0, 1, 2], dtype=np.int32)


@dataclass(frozen=True, slots=True)
class TargetTerm:
    value: float
    tolerance: float
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    score: float
    report: ParameterReport
    metrics: dict[str, float]
    normalized_errors: dict[str, float]


@dataclass(frozen=True, slots=True)
class SearchProfile:
    name: str
    description: str
    simulation: dict[str, Any]
    optimizer: dict[str, Any]
    targets: dict[str, TargetTerm]


@dataclass(frozen=True, slots=True)
class BestCandidate:
    """Best candidate observed over all evaluated generations."""

    generation: int
    reels: np.ndarray
    evaluation: CandidateEvaluation


def _metric_values(report: ParameterReport) -> dict[str, float]:
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
        "base_0_to_5_prob": (
            base.p_0_to_1 + base.p_1_to_2 + base.p_2_to_5
        ),
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


SUPPORTED_METRICS = frozenset({
    "rtp_total", "rtp_base", "rtp_bonus", "bonus_freq",
    "mean_bonus_payout", "mean_free_spins", "base_win_prob",
    "base_0_to_1_prob", "base_1_to_2_prob", "base_2_to_5_prob",
    "base_5_to_10_prob", "base_10_to_20_prob", "base_20_to_30_prob",
    "base_30_to_50_prob", "base_over_50_prob", "base_0_to_2_prob",
    "base_0_to_5_prob",
    "base_5_to_20_prob", "base_20_to_50_prob", "base_over_10_prob",
    "bonus_win_prob", "bonus_0_to_10_prob", "bonus_10_to_25_prob",
    "bonus_25_to_50_prob", "bonus_50_to_100_prob",
    "bonus_100_to_250_prob", "bonus_250_to_500_prob",
    "bonus_500_to_1000_prob", "bonus_over_1000_prob",
    "bonus_over_50_prob", "bonus_over_100_prob", "bonus_over_250_prob",
})


def load_profile(path: Path) -> SearchProfile:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"Target profile does not exist: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("Target profile root must be a JSON object.")

    name = str(raw.get("name", path.stem))
    description = str(raw.get("description", ""))
    simulation = dict(raw.get("simulation", {}))
    optimizer = dict(raw.get("optimizer", {}))
    raw_targets = raw.get("targets")

    if not isinstance(raw_targets, dict) or not raw_targets:
        raise ValueError("Target profile must contain a non-empty 'targets' object.")

    targets: dict[str, TargetTerm] = {}
    for metric_name, spec in raw_targets.items():
        if metric_name not in SUPPORTED_METRICS:
            allowed = ", ".join(sorted(SUPPORTED_METRICS))
            raise ValueError(
                f"Unknown target metric {metric_name!r}. Supported metrics: {allowed}"
            )
        if not isinstance(spec, dict):
            raise ValueError(f"Target {metric_name!r} must be a JSON object.")

        try:
            target = TargetTerm(
                value=float(spec["value"]),
                tolerance=float(spec["tolerance"]),
                weight=float(spec.get("weight", 1.0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid target definition for {metric_name!r}.") from exc

        if not np.isfinite(target.value):
            raise ValueError(f"Target {metric_name!r} value must be finite.")
        if not np.isfinite(target.tolerance) or target.tolerance <= 0.0:
            raise ValueError(f"Target {metric_name!r} tolerance must be positive.")
        if not np.isfinite(target.weight) or target.weight <= 0.0:
            raise ValueError(f"Target {metric_name!r} weight must be positive.")

        targets[metric_name] = target

    return SearchProfile(
        name=name,
        description=description,
        simulation=simulation,
        optimizer=optimizer,
        targets=targets,
    )


def score_report(
    report: ParameterReport,
    targets: Mapping[str, TargetTerm],
) -> CandidateEvaluation:
    metrics = _metric_values(report)
    normalized_errors: dict[str, float] = {}
    weighted_squared_error = 0.0
    total_weight = 0.0

    for name, target in targets.items():
        error = (metrics[name] - target.value) / target.tolerance
        normalized_errors[name] = float(error)
        weighted_squared_error += target.weight * error * error
        total_weight += target.weight

    score = float(np.sqrt(weighted_squared_error / total_weight))
    return CandidateEvaluation(
        score=score,
        report=report,
        metrics=metrics,
        normalized_errors=normalized_errors,
    )


def resolve_profile_path(value: str) -> Path:
    supplied = Path(value)
    if supplied.is_file():
        return supplied.resolve()

    name = value if value.endswith(".json") else f"{value}.json"
    return TARGETS_DIR / name


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find a reel-set candidate matching a volatility target profile."
    )
    parser.add_argument(
        "target",
        help=(
            "Profile name (high_vol or low_vol) or a path to a target JSON file."
        ),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--population-size", type=_positive_int)
    parser.add_argument("--generations", type=_positive_int)
    parser.add_argument("--workers", type=_positive_int)
    parser.add_argument("--base-spins", type=_positive_int)
    parser.add_argument("--bonus-games", type=_positive_int)
    parser.add_argument("--final-base-spins", type=_positive_int)
    parser.add_argument("--final-bonus-games", type=_positive_int)
    parser.add_argument(
        "--skip-final-validation",
        action="store_true",
        help="Skip the larger final Monte Carlo validation run.",
    )
    return parser.parse_args()


def _override(settings: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        settings[key] = value


def _print_target_table(
    evaluation: CandidateEvaluation,
    targets: Mapping[str, TargetTerm],
) -> None:
    print("\nTarget fit")
    print("-" * 78)
    print(f"{'metric':<26} {'actual':>12} {'target':>12} {'tol':>10} {'z-error':>10}")
    print("-" * 78)
    for name, target in targets.items():
        actual = evaluation.metrics[name]
        error = evaluation.normalized_errors[name]
        print(
            f"{name:<26} {actual:12.6f} {target.value:12.6f} "
            f"{target.tolerance:10.6f} {error:10.3f}"
        )
    print("-" * 78)
    print(f"weighted RMS normalized error: {evaluation.score:.4f}")


def _serialize_evaluation(
    evaluation: CandidateEvaluation,
    targets: Mapping[str, TargetTerm],
) -> dict[str, Any]:
    return {
        "score": evaluation.score,
        "metrics": evaluation.metrics,
        "normalized_errors": evaluation.normalized_errors,
        "targets": {name: asdict(target) for name, target in targets.items()},
        "report": asdict(evaluation.report),
    }


def _print_generation(optimizer: Optimizer, generation: int) -> None:
    index = optimizer.best_index()
    payload = optimizer.evaluation_payloads()[index]

    if not isinstance(payload, CandidateEvaluation):
        print(
            f"generation {generation:>3}: "
            f"best score = {optimizer.best_fitness():.4f}"
        )
        return

    metrics = payload.metrics
    print(
        f"generation {generation:>3}: "
        f"score={payload.score:7.4f}  "
        f"RTP={metrics['rtp_total']:.4f}  "
        f"bonus_RTP={metrics['rtp_bonus']:.4f}  "
        f"bonus_f={metrics['bonus_freq']:.4f}  "
        f"base_hit={metrics['base_win_prob']:.4f}"
    )


def _update_best_candidate(
    optimizer: Optimizer,
    generation: int,
    best_seen: BestCandidate | None,
) -> BestCandidate:
    """Return the best candidate observed up to this generation."""

    index = optimizer.best_index()
    payload = optimizer.evaluation_payloads()[index]
    if not isinstance(payload, CandidateEvaluation):
        raise RuntimeError(
            "Optimizer did not retain candidate evaluation metadata."
        )

    if best_seen is not None:
        if optimizer.config.maximize:
            improved = payload.score > best_seen.evaluation.score
        else:
            improved = payload.score < best_seen.evaluation.score

        if not improved:
            return best_seen

    return BestCandidate(
        generation=generation,
        reels=optimizer.best_reels(),
        evaluation=payload,
    )


def main() -> None:
    args = parse_args()
    profile_path = resolve_profile_path(args.target)
    profile = load_profile(profile_path)

    sim_cfg = dict(profile.simulation)
    ga_cfg = dict(profile.optimizer)

    _override(ga_cfg, "population_size", args.population_size)
    _override(ga_cfg, "generations", args.generations)
    _override(ga_cfg, "max_workers", args.workers)
    _override(sim_cfg, "base_spins", args.base_spins)
    _override(sim_cfg, "bonus_games", args.bonus_games)
    _override(sim_cfg, "final_base_spins", args.final_base_spins)
    _override(sim_cfg, "final_bonus_games", args.final_bonus_games)

    required_sim = {
        "base_spins", "bonus_games", "final_base_spins", "final_bonus_games",
        "min_scatter", "initial_free_spins", "retrigger_free_spins", "max_win",
    }
    missing_sim = sorted(required_sim - sim_cfg.keys())
    if missing_sim:
        raise ValueError(f"Missing simulation settings: {', '.join(missing_sim)}")

    required_ga = {
        "population_size", "generations", "crossover_rate", "mutation_rate",
        "tournament_size", "elite_count", "max_workers",
        "initial_candidate_concentration", "initial_reel_concentration",
    }
    missing_ga = sorted(required_ga - ga_cfg.keys())
    if missing_ga:
        raise ValueError(f"Missing optimizer settings: {', '.join(missing_ga)}")

    evaluator = PaylineEvaluator.from_definitions(
        paylines=PAYLINES,
        paytable=PAYTABLE,
        max_win=float(sim_cfg["max_win"]),
    )

    def fitness(candidate: np.ndarray, evaluation_seed: int) -> FitnessEvaluation:
        model = ScreenModel(reels=candidate, window_offsets=WINDOW_OFFSETS)
        report = sim_report(
            model=model,
            total_spins=int(sim_cfg["base_spins"]),
            total_bonus_games=int(sim_cfg["bonus_games"]),
            seed=evaluation_seed,
            min_scatter=int(sim_cfg["min_scatter"]),
            initial_free_spins=int(sim_cfg["initial_free_spins"]),
            retrigger_free_spins=int(sim_cfg["retrigger_free_spins"]),
            max_win=float(sim_cfg["max_win"]),
            evaluator=evaluator,
        )
        evaluation = score_report(report, profile.targets)
        return FitnessEvaluation(value=evaluation.score, payload=evaluation)

    template_reels = read_reels()
    default_reel_len = int(template_reels[0].size)
    reel_len = int(ga_cfg.get("reel_length", default_reel_len))
    n_reels = len(template_reels)

    if reel_len <= 0:
        raise ValueError("optimizer.reel_length must be a positive integer.")

    optimizer = Optimizer(
        OptimizerConfig(
            reel_len=reel_len,
            n_reels=n_reels,
            population_size=int(ga_cfg["population_size"]),
            crossover_rate=float(ga_cfg["crossover_rate"]),
            mutation_rate=float(ga_cfg["mutation_rate"]),
            tournament_size=int(ga_cfg["tournament_size"]),
            elite_count=int(ga_cfg["elite_count"]),
            maximize=False,
            max_generation=int(ga_cfg["generations"]),
            max_workers=int(ga_cfg["max_workers"]),
            initial_candidate_concentration=float(
                ga_cfg["initial_candidate_concentration"]
            ),
            initial_reel_concentration=float(ga_cfg["initial_reel_concentration"]),
        ),
        fitness_fun=fitness,
        seed=args.seed,
    )

    print(f"Profile: {profile.name} ({profile_path})")
    if profile.description:
        print(profile.description)
    print(
        "GA: "
        f"population={ga_cfg['population_size']}, "
        f"generations={ga_cfg['generations']}, "
        f"workers={ga_cfg['max_workers']}, "
        f"reel_length={reel_len}"
    )
    print(
        "Evaluation: "
        f"base_spins={int(sim_cfg['base_spins']):,}, "
        f"bonus_games={int(sim_cfg['bonus_games']):,}"
    )

    optimizer.populate()

    # Evaluate generation zero, then evolve for the requested number of steps.
    # Keep the best performing candiate across all generations
    optimizer.fitness()
    _print_generation(optimizer, 0)
    best_seen: BestCandidate | None = _update_best_candidate(
        optimizer, 0, None
    )

    for generation in range(1, int(ga_cfg["generations"]) + 1):
        optimizer.step()
        _print_generation(optimizer, generation)
        best_seen = _update_best_candidate(
            optimizer, generation, best_seen
        )

    if best_seen is None:
        raise RuntimeError("Optimizer did not produce a best candidate.")

    best_reels = best_seen.reels
    best_payload = best_seen.evaluation
    print(
        "\nBest observed candidate: "
        f"generation={best_seen.generation}, "
        f"score={best_payload.score:.4f}"
    )

    final_evaluation = best_payload
    if not args.skip_final_validation:
        final_model = ScreenModel(reels=best_reels, window_offsets=WINDOW_OFFSETS)
        final_report = sim_report(
            model=final_model,
            total_spins=int(sim_cfg["final_base_spins"]),
            total_bonus_games=int(sim_cfg["final_bonus_games"]),
            seed=args.seed + 1_000_003,
            min_scatter=int(sim_cfg["min_scatter"]),
            initial_free_spins=int(sim_cfg["initial_free_spins"]),
            retrigger_free_spins=int(sim_cfg["retrigger_free_spins"]),
            max_win=float(sim_cfg["max_win"]),
            evaluator=evaluator,
        )
        final_evaluation = score_report(final_report, profile.targets)
        print(
            "\nFinal validation: "
            f"base_spins={int(sim_cfg['final_base_spins']):,}, "
            f"bonus_games={int(sim_cfg['final_bonus_games']):,}"
        )

    _print_target_table(final_evaluation, profile.targets)
    print("\n" + str(final_evaluation.report))

    output_path = args.output
    if output_path is None:
        output_path = DEFAULT_OUTPUT_DIR / f"{profile.name}.json"
    elif not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    reels_tuple = tuple(reel.copy() for reel in best_reels)
    save_reels(reels_tuple, output_path)

    report_path = output_path.with_name(f"{output_path.stem}_report.json")
    report_payload = {
        "profile": profile.name,
        "profile_path": str(profile_path),
        "seed": args.seed,
        "simulation": sim_cfg,
        "optimizer": ga_cfg,
        "best_generation": best_seen.generation,
        "search_evaluation": _serialize_evaluation(
            best_payload, profile.targets
        ),
        "evaluation": _serialize_evaluation(final_evaluation, profile.targets),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nSaved reels:  {output_path}")
    print(f"Saved report: {report_path}")


if __name__ == "__main__":
    main()