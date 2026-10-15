#!/usr/bin/env python3
"""Generate RAG evaluation charts with seaborn and matplotlib."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns


QUESTION_TYPES = [
    {"type": "Fact", "samples": 57, "pass_rate": 68.4, "overall_score": 0.871},
    {"type": "Responsibility", "samples": 16, "pass_rate": 62.5, "overall_score": 0.835},
    {"type": "Condition", "samples": 23, "pass_rate": 52.2, "overall_score": 0.794},
    {"type": "Procedure", "samples": 21, "pass_rate": 38.1, "overall_score": 0.774},
    {"type": "Summary", "samples": 13, "pass_rate": 30.8, "overall_score": 0.697},
    {"type": "Definition", "samples": 11, "pass_rate": 27.3, "overall_score": 0.670},
]

METRIC_SCORES = [
    {"metric": "Answer Relevancy", "score": 0.835},
    {"metric": "Contextual Recall", "score": 0.742},
    {"metric": "Faithfulness", "score": 0.838},
    {"metric": "Overall Score", "score": 0.807},
]

SCORE_DISTRIBUTION = [
    {"range": "Score 1.0", "samples": 64},
    {"range": "0.8 - 0.99", "samples": 31},
    {"range": "0.6 - 0.79", "samples": 21},
    {"range": "0.4 - 0.59", "samples": 19},
    {"range": "0.0 - 0.39", "samples": 6},
]

FAILURE_ANALYSIS = [
    {"failure_type": "Retrieval Failures", "samples": 0, "rate": 0.0},
    {"failure_type": "Generation Answer", "samples": 35, "rate": 24.8},
    {"failure_type": "Generation Grounding", "samples": 30, "rate": 21.3},
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate RAG evaluation charts.")
    parser.add_argument(
        "--output-dir",
        default="reports/evaluation/charts",
        help="Directory where PNG files will be written.",
    )
    parser.add_argument("--dpi", type=int, default=180, help="Output image DPI.")
    return parser


def setup_theme() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#CBD5E1",
            "axes.labelcolor": "#334155",
            "axes.titlecolor": "#0F172A",
            "xtick.color": "#475569",
            "ytick.color": "#475569",
            "font.family": "DejaVu Sans",
        }
    )


def annotate_horizontal_bars(ax: plt.Axes, values: list[float], suffix: str = "") -> None:
    x_max = max(values) if values else 0
    offset = max(x_max * 0.015, 0.5)
    for patch, value in zip(ax.patches, values):
        ax.text(
            patch.get_width() + offset,
            patch.get_y() + patch.get_height() / 2,
            f"{value:g}{suffix}",
            va="center",
            ha="left",
            fontsize=10,
            color="#0F172A",
        )


def annotate_vertical_bars(ax: plt.Axes, values: list[float], fmt: str = "{:.3f}") -> None:
    y_max = max(values) if values else 0
    offset = max(y_max * 0.025, 0.02)
    for patch, value in zip(ax.patches, values):
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            patch.get_height() + offset,
            fmt.format(value),
            va="bottom",
            ha="center",
            fontsize=10,
            color="#0F172A",
        )


def save_figure(fig: plt.Figure, path: Path, dpi: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def draw_question_type_distribution(output_dir: Path, dpi: int) -> Path:
    data = sorted(QUESTION_TYPES, key=lambda item: item["samples"], reverse=True)
    labels = [item["type"] for item in data]
    values = [item["samples"] for item in data]

    fig, ax = plt.subplots(figsize=(10, 5.8))
    sns.barplot(x=values, y=labels, ax=ax, palette="viridis", hue=labels, legend=False)
    annotate_horizontal_bars(ax, values)

    total = math.fsum(values)
    ax.set_title("Hình 5.3 - Phân bố câu hỏi theo loại", fontsize=15, fontweight="bold")
    ax.set_xlabel("Số mẫu")
    ax.set_ylabel("Loại câu hỏi")
    ax.set_xlim(0, max(values) * 1.18)
    ax.text(
        0.99,
        -0.14,
        f"Tổng số mẫu: {int(total)}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10,
        color="#475569",
    )

    path = output_dir / "rag-question-type-distribution.png"
    save_figure(fig, path, dpi)
    return path


def draw_metric_scores(output_dir: Path, dpi: int) -> Path:
    labels = [item["metric"] for item in METRIC_SCORES]
    values = [item["score"] for item in METRIC_SCORES]

    fig, ax = plt.subplots(figsize=(10, 5.8))
    sns.barplot(x=labels, y=values, ax=ax, palette="mako", hue=labels, legend=False)
    annotate_vertical_bars(ax, values)

    ax.axhline(0.7, color="#EF4444", linestyle="--", linewidth=1.4, label="Ngưỡng 0.70")
    ax.set_title("Hình 5.4 - Điểm trung bình của ba chỉ số đánh giá", fontsize=15, fontweight="bold")
    ax.set_xlabel("Chỉ số")
    ax.set_ylabel("Điểm trung bình")
    ax.set_ylim(0, 1.05)
    ax.tick_params(axis="x", rotation=12)
    ax.legend(loc="lower right", frameon=True)
    ax.text(
        0.01,
        -0.18,
        "Pass Rate: 50.4% (84/141 mẫu đạt)",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        color="#475569",
    )

    path = output_dir / "rag-average-scores-by-metric.png"
    save_figure(fig, path, dpi)
    return path


def draw_score_distribution(output_dir: Path, dpi: int) -> Path:
    labels = [item["range"] for item in SCORE_DISTRIBUTION]
    values = [item["samples"] for item in SCORE_DISTRIBUTION]

    fig, ax = plt.subplots(figsize=(10, 5.8))
    sns.barplot(x=values, y=labels, ax=ax, palette="crest", hue=labels, legend=False)
    annotate_horizontal_bars(ax, values, " mẫu")

    ax.set_title("Hình 5.5 - Phân bố điểm tổng hợp", fontsize=15, fontweight="bold")
    ax.set_xlabel("Số mẫu")
    ax.set_ylabel("Khoảng điểm")
    ax.set_xlim(0, max(values) * 1.22)
    ax.text(
        0.99,
        -0.14,
        "95/141 mẫu đạt từ 0.80 trở lên",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10,
        color="#475569",
    )

    path = output_dir / "rag-overall-score-distribution.png"
    save_figure(fig, path, dpi)
    return path


def draw_failure_analysis(output_dir: Path, dpi: int) -> Path:
    labels = [item["failure_type"] for item in FAILURE_ANALYSIS]
    values = [item["samples"] for item in FAILURE_ANALYSIS]

    fig, ax = plt.subplots(figsize=(10, 5.8))
    sns.barplot(x=values, y=labels, ax=ax, palette="rocket", hue=labels, legend=False)
    annotate_horizontal_bars(ax, values)

    for patch, item in zip(ax.patches, FAILURE_ANALYSIS):
        ax.text(
            patch.get_width() + 1.8,
            patch.get_y() + patch.get_height() / 2,
            f"{item['rate']:.1f}%",
            va="center",
            ha="left",
            fontsize=10,
            color="#475569",
        )

    ax.set_title("Phân tích lỗi đánh giá", fontsize=15, fontweight="bold")
    ax.set_xlabel("Số mẫu")
    ax.set_ylabel("Nhóm lỗi")
    ax.set_xlim(0, max(values) * 1.35 if max(values) else 10)

    path = output_dir / "rag-failure-analysis.png"
    save_figure(fig, path, dpi)
    return path


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)

    setup_theme()
    outputs = [
        draw_question_type_distribution(output_dir, args.dpi),
        draw_metric_scores(output_dir, args.dpi),
        draw_score_distribution(output_dir, args.dpi),
        draw_failure_analysis(output_dir, args.dpi),
    ]

    print("Generated charts:")
    for output in outputs:
        print(f"- {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
