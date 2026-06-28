#!/usr/bin/env python3
"""Visualize the generated evaluation gold dataset distribution and print samples."""

import sys
import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Visualize gold dataset distribution.")
    parser.add_argument("--dataset", default="dataset/generated_dataset.json", help="Path to gold dataset JSON")
    parser.add_argument("--output-img", default="dataset/gold_dataset_distribution.png", help="Path to save distribution graph")
    return parser

def main() -> int:
    args = build_parser().parse_args()
    dataset_path = Path(args.dataset)
    output_img_path = Path(args.output_img)

    if not dataset_path.exists():
        print(f"Error: Dataset file not found at {dataset_path}")
        return 1

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = data.get("samples", [])
    total_samples = len(samples)
    print(f"=== Gold Dataset Analysis ===")
    print(f"Dataset Name: {data.get('name')}")
    print(f"Dataset ID: {data.get('dataset_id')}")
    print(f"Total Samples: {total_samples}")

    if not samples:
        print("No samples found in the dataset.")
        return 0

    # 1. Gather stats
    difficulty_counter = Counter()
    type_counter = Counter()
    doc_counter = Counter()
    refusal_counter = Counter()

    for s in samples:
        tags = s.get("tags", [])
        # Difficulty is easy or medium
        diff = "easy"
        if "medium" in tags:
            diff = "medium"
        elif "easy" in tags:
            diff = "easy"
        difficulty_counter[diff] += 1

        # Question Type
        q_type = "fact"
        for t in ["fact", "condition", "procedure", "definition", "responsibility", "summary"]:
            if t in tags:
                q_type = t
                break
        type_counter[q_type] += 1

        # Refusal status
        should_refuse = s.get("should_refuse", False)
        refusal_counter["Refusal/No Answer" if should_refuse else "Answerable"] += 1

        # Source Document
        source_file = s.get("metadata", {}).get("source_file", "unknown")
        doc_counter[source_file] += 1

    # Print summary table
    print("\n--- Breakdown by Difficulty ---")
    for k, v in difficulty_counter.items():
        print(f"  {k:15}: {v} ({v/total_samples*100:.1f}%)")

    print("\n--- Breakdown by Question Type ---")
    for k, v in type_counter.items():
        print(f"  {k:15}: {v} ({v/total_samples*100:.1f}%)")

    print("\n--- Refusal Status ---")
    for k, v in refusal_counter.items():
        print(f"  {k:20}: {v} ({v/total_samples*100:.1f}%)")

    print(f"\n--- Top 10 Documents with Most Questions ---")
    for k, v in doc_counter.most_common(10):
        print(f"  {v:2} qns : {k}")

    # 2. Draw distribution chart
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left plot: Question Type Distribution
    types_sorted = sorted(type_counter.items(), key=lambda x: x[1], reverse=True)
    if types_sorted:
        x_types = [t[0] for t in types_sorted]
        y_types = [t[1] for t in types_sorted]
        sns.barplot(x=y_types, y=x_types, ax=axes[0], hue=x_types, palette="viridis", legend=False)
    axes[0].set_title("Question Type Distribution", fontsize=14, fontweight="bold", pad=15)
    axes[0].set_xlabel("Number of Questions")

    # Right plot: Difficulty and Refusal Pie Chart
    diff_labels = list(difficulty_counter.keys())
    diff_sizes = list(difficulty_counter.values())
    if diff_sizes:
        axes[1].pie(
            diff_sizes, 
            labels=diff_labels, 
            autopct='%1.1f%%', 
            startangle=140, 
            colors=["#66b3ff", "#ff9999"], 
            textprops={'fontsize': 12}
        )
    axes[1].set_title("Difficulty Distribution", fontsize=14, fontweight="bold", pad=15)

    plt.tight_layout()
    output_img_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_img_path, dpi=150)
    print(f"\nDistribution graph saved to: {output_img_path}")

    # 3. Print 3 Samples
    print("\n=== Sample Questions (First 3) ===")
    for idx, s in enumerate(samples[:3], 1):
        print(f"\n[{idx}] Document: {s.get('metadata', {}).get('source_file')}")
        print(f"    Difficulty: {'medium' if 'medium' in s.get('tags', []) else 'easy'} | Type: {s.get('tags', [None])[2] or 'fact'}")
        print(f"    Q: {s.get('query')}")
        print(f"    Expected A: {s.get('expected_answer')}")
        evidence = s.get("metadata", {}).get("answer_evidence", "")
        if evidence:
            print(f"    Evidence: \"{evidence}\"")

    return 0

if __name__ == "__main__":
    sys.exit(main())
