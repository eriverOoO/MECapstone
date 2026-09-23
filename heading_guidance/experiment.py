"""세 guidance 알고리즘의 자동 및 Monte Carlo 비교 실험."""

import argparse
import csv
import math
import random
import statistics
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt

import config
from heading_controller import Direction, HeadingController
from guidance_algorithms import create_guidance_algorithm
from imu_simulator import IMUSimulator
from metrics import ExperimentSample, PerformanceMetrics, calculate_metrics


ALGORITHMS = ("continuous", "discrete", "pulse")


@dataclass(frozen=True)
class TrialResult:
    algorithm: str
    run: int
    metrics: PerformanceMetrics
    samples: list[ExperimentSample]


def make_controller(algorithm: str) -> HeadingController:
    return HeadingController(
        config.DEADBAND_DEG,
        config.HYSTERESIS_REENTRY_DEG,
        config.MAX_INTENSITY_ERROR_DEG,
        config.PWM_MAX,
        create_guidance_algorithm(algorithm),
    )


def run_trial(
    algorithm: str,
    run_number: int,
    initial_heading: float,
    target_heading: float,
    seed: int,
) -> TrialResult:
    """진동에 비례해 회전하는 단순 가상 사용자 한 명을 시뮬레이션한다."""

    controller = make_controller(algorithm)
    imu = IMUSimulator(initial_heading, random_seed=seed)
    user_random = random.Random(seed + 1_000_003)
    dt = config.SIMULATION_DT_SEC
    delay_steps = round(config.USER_REACTION_DELAY_SEC / dt)
    delayed_commands: list[tuple[Direction, float]] = []
    samples: list[ExperimentSample] = []
    inside_since: float | None = None
    steps = round(config.SIMULATION_MAX_TIME_SEC / dt)

    for step in range(steps + 1):
        now = step * dt
        reading = imu.sample(now)
        command = controller.update(target_heading, reading.filtered_heading, now)
        samples.append(ExperimentSample(now, command.error_deg, command.intensity))
        delayed_commands.append((command.direction, command.intensity))

        if abs(command.error_deg) <= config.DEADBAND_DEG:
            inside_since = now if inside_since is None else inside_since
            if now - inside_since >= config.SETTLING_HOLD_TIME_SEC:
                break
        else:
            inside_since = None

        delayed_index = len(delayed_commands) - 1 - delay_steps
        if delayed_index >= 0:
            direction, intensity = delayed_commands[delayed_index]
        else:
            direction, intensity = Direction.OFF, 0.0
        sign = 1.0 if direction == Direction.RIGHT else -1.0 if direction == Direction.LEFT else 0.0
        turn_rate = sign * config.USER_MAX_TURN_RATE_DEG_PER_SEC * intensity
        turn_rate += user_random.gauss(0.0, config.USER_TURN_NOISE_STD_DEG_PER_SEC)
        imu.set_true_heading(imu.true_heading + turn_rate * dt)

    return TrialResult(
        algorithm,
        run_number,
        calculate_metrics(samples),
        samples,
    )


def _finite(values: list[float]) -> list[float]:
    return [value for value in values if math.isfinite(value)]


def summarize_trials(trials: list[TrialResult]) -> list[dict[str, str | int | float]]:
    rows: list[dict[str, str | int | float]] = []
    for algorithm in ALGORITHMS:
        algorithm_trials = [trial for trial in trials if trial.algorithm == algorithm]
        for metric_name in PerformanceMetrics.__dataclass_fields__:
            raw_values = [float(getattr(trial.metrics, metric_name)) for trial in algorithm_trials]
            values = _finite(raw_values)
            rows.append(
                {
                    "algorithm": algorithm,
                    "metric": metric_name,
                    "runs": len(raw_values),
                    "valid_runs": len(values),
                    "mean": statistics.fmean(values) if values else math.nan,
                    "std": statistics.pstdev(values) if values else math.nan,
                    "min": min(values, default=math.nan),
                    "max": max(values, default=math.nan),
                }
            )
    return rows


def save_results(
    trials: list[TrialResult], output_directory: str | Path
) -> tuple[Path, Path, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    trials_path = directory / "algorithm_trials.csv"
    summary_path = directory / "algorithm_comparison.csv"
    graph_path = directory / "algorithm_comparison.png"

    with trials_path.open("w", newline="", encoding="utf-8") as output:
        fieldnames = ("algorithm", "run", *PerformanceMetrics.__dataclass_fields__.keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for trial in trials:
            writer.writerow(
                {"algorithm": trial.algorithm, "run": trial.run, **trial.metrics.as_dict()}
            )

    summary_rows = summarize_trials(trials)
    with summary_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=("algorithm", "metric", "runs", "valid_runs", "mean", "std", "min", "max"),
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    selected_metrics = ("time_to_alignment", "mae", "total_vibration_time")
    figure, axes = plt.subplots(1, 3, figsize=(13, 4))
    for axis, metric_name in zip(axes, selected_metrics):
        metric_rows = [row for row in summary_rows if row["metric"] == metric_name]
        means = [float(row["mean"]) for row in metric_rows]
        stds = [float(row["std"]) for row in metric_rows]
        axis.bar(ALGORITHMS, means, yerr=stds, capsize=4)
        axis.set_title(metric_name.replace("_", " ").title())
        axis.grid(axis="y", alpha=0.3)
    figure.suptitle("Guidance Algorithm Comparison (mean ± standard deviation)")
    figure.tight_layout()
    figure.savefig(graph_path, dpi=150)
    plt.close(figure)
    return trials_path, summary_path, graph_path


def print_summary(trials: list[TrialResult]) -> None:
    summary = summarize_trials(trials)
    print("\nAlgorithm comparison")
    for algorithm in ALGORITHMS:
        print(f"\n{algorithm.title()}")
        for name in ("mae", "rmse", "time_to_alignment", "settling_time", "maximum_error", "total_vibration_time"):
            row = next(
                item for item in summary if item["algorithm"] == algorithm and item["metric"] == name
            )
            print(
                f"  {name:22s} mean={float(row['mean']):7.3f} "
                f"std={float(row['std']):7.3f} min={float(row['min']):7.3f} max={float(row['max']):7.3f}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare heading guidance algorithms")
    parser.add_argument("--runs", type=int, default=1, help="Monte Carlo runs per algorithm")
    parser.add_argument("--initial", type=float, default=config.DEFAULT_CURRENT_HEADING_DEG)
    parser.add_argument("--target", type=float, default=config.DEFAULT_TARGET_HEADING_DEG)
    parser.add_argument("--seed", type=int, default=config.MONTE_CARLO_SEED)
    args = parser.parse_args()
    if args.runs <= 0:
        parser.error("--runs must be positive")

    trials = [
        run_trial(
            algorithm,
            run,
            args.initial,
            args.target,
            args.seed + run,
        )
        for run in range(1, args.runs + 1)
        for algorithm in ALGORITHMS
    ]
    print_summary(trials)
    trials_path, summary_path, graph_path = save_results(trials, config.RESULTS_DIRECTORY)
    print(f"\nTrial CSV: {trials_path}")
    print(f"Summary CSV: {summary_path}")
    print(f"Comparison graph: {graph_path}")


if __name__ == "__main__":
    main()
