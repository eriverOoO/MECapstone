"""CSV 실험 로그를 세 개의 그래프로 시각화한다."""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def plot_log(log_path: str | Path, show: bool = True) -> Path:
    """로그를 읽어 그래프 PNG를 저장하고 선택적으로 화면에 표시한다."""

    path = Path(log_path)
    with path.open(newline="", encoding="utf-8") as log_file:
        rows = list(csv.DictReader(log_file))
    if not rows:
        raise ValueError(f"log has no data rows: {path}")

    elapsed = [float(row["elapsed_seconds"]) for row in rows]
    target = [float(row["target_heading"]) for row in rows]
    true_heading = [float(row.get("true_heading", row["current_heading"])) for row in rows]
    measured = [float(row.get("measured_heading", row["current_heading"])) for row in rows]
    filtered = [float(row.get("filtered_heading", row["current_heading"])) for row in rows]
    error = [float(row["heading_error"]) for row in rows]
    left = [float(row["left_intensity"]) for row in rows]
    right = [float(row["right_intensity"]) for row in rows]

    figure, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    axes[0].plot(elapsed, target, label="Target Heading")
    axes[0].plot(elapsed, true_heading, label="True Heading")
    axes[0].plot(elapsed, measured, alpha=0.45, label="Measured Heading")
    axes[0].plot(elapsed, filtered, label="Filtered Heading")
    axes[0].set_ylabel("Heading (deg)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(elapsed, error, color="tab:purple", label="Heading Error")
    axes[1].axhline(0.0, color="black", linewidth=0.8)
    axes[1].set_ylabel("Error (deg)")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(elapsed, left, label="Left Motor")
    axes[2].plot(elapsed, right, label="Right Motor")
    axes[2].set_xlabel("Elapsed time (s)")
    axes[2].set_ylabel("Intensity (0-1)")
    axes[2].set_ylim(-0.05, 1.05)
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    figure.suptitle(f"Heading Guidance Log: {path.name}")
    figure.tight_layout()
    output_path = path.with_suffix(".png")
    figure.savefig(output_path, dpi=150)
    if show:
        plt.show()
    plt.close(figure)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot a heading guidance CSV log")
    parser.add_argument("log_file", help="path to heading_log_*.csv")
    parser.add_argument("--no-show", action="store_true", help="save PNG without opening a window")
    args = parser.parse_args()
    output = plot_log(args.log_file, show=not args.no_show)
    print(f"Graph saved: {output}")


if __name__ == "__main__":
    main()
