#!/usr/bin/env python3
"""Prepare a representative 43-document subset from docs_to_upload and visualize it."""

from __future__ import annotations

import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT_DIR / "docs_to_upload/_dut_vanban_manifest.csv"
OUTPUT_DIR = ROOT_DIR / "dataset"
OUTPUT_CSV = OUTPUT_DIR / "_subset_manifest.csv"
OUTPUT_IMAGE = OUTPUT_DIR / "subset_distribution.png"

# Target distribution mapping (represents 43 documents across 18 fields)
TARGET_COUNTS = {
    "Tổ chức, hành chính": 10,
    "Đào tạo": 5,
    "Thanh tra, kiểm tra": 4,
    "Thi đua, khen thưởng": 3,
    "Pháp chế": 3,
    "Công tác sinh viên": 2,
    "Tài chính, kế toán": 2,
    "Khoa học Công nghệ": 2,
    "Đảm bảo chất lượng, KĐCL": 2,
    "Tuyển sinh": 2,
    "Cơ sở vật chất, xây dựng": 1,
    "Công nghệ thông tin, CĐS": 1,
    "Học liệu, truyền thông": 1,
    "Hợp tác quốc tế": 1,
    "Khác": 1,
    "Văn thư, lưu trữ": 1,
    "Khảo thí": 1,
    "Sở hữu trí tuệ": 1,
}

def main():
    if not CSV_PATH.exists():
        print(f"Error: Manifest file not found at {CSV_PATH}")
        return 1

    # Create destination directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Read original manifest
    df = pd.read_csv(CSV_PATH)
    df['field'] = df['field'].fillna('Không xác định').astype(str).str.strip()

    # Deduplicate by local_path to select unique document files
    unique_docs = df.drop_duplicates(subset=['local_path']).copy()

    selected_rows = []
    for field, target in TARGET_COUNTS.items():
        # Get all documents for this field
        field_docs = unique_docs[unique_docs['field'] == field]
        # Sample up to target count
        sampled = field_docs.head(target)
        selected_rows.append(sampled)
        print(f"Field '{field}': sampled {len(sampled)}/{len(field_docs)} documents.")

    subset_df = pd.concat(selected_rows, ignore_index=True)
    
    # Copy files
    copied_count = 0
    for _, row in subset_df.iterrows():
        source_rel_path = str(row['local_path'])
        source_path = ROOT_DIR / source_rel_path
        
        # Determine destination filename
        filename = source_path.name
        dest_path = OUTPUT_DIR / filename
        
        if source_path.exists():
            shutil.copy2(source_path, dest_path)
            copied_count += 1
        else:
            print(f"Warning: Source file not found: {source_path}")

    # Generate new subset manifest
    # Update local_path to point to the new dataset folder
    subset_df['local_path'] = subset_df['filename'].apply(lambda name: f"dataset/{name}")
    subset_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSuccessfully copied {copied_count} files to {OUTPUT_DIR}")
    print(f"Saved subset manifest to: {OUTPUT_CSV}")

    # Generate visualization
    field_counts = subset_df['field'].value_counts()
    total_docs = len(subset_df)

    sns.set_theme(style="whitegrid")
    plt.rcParams['font.family'] = 'DejaVu Sans'

    fig, ax = plt.subplots(figsize=(12, 7))
    sns.barplot(
        x=field_counts.values,
        y=field_counts.index,
        hue=field_counts.index,
        palette="viridis",
        legend=False,
        ax=ax
    )

    # Add labels
    for i, v in enumerate(field_counts.values):
        percentage = (v / total_docs) * 100
        ax.text(v + 0.1, i, f" {v} ({percentage:.1f}%)", va='center', fontweight='bold', color='#333333')

    ax.set_title("Phân bộ số lượng tài liệu rút gọn theo Lĩnh vực (Field)", fontsize=16, fontweight='bold', pad=20, color='#1a1a1a')
    ax.set_xlabel("Số lượng tài liệu (bản)", fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel("Lĩnh vực", fontsize=12, fontweight='bold', labelpad=10)

    # Set x-axis limit slightly larger to accommodate labels
    ax.set_xlim(0, max(field_counts.values) + 2)

    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE, dpi=300)
    print(f"Saved distribution visualization to: {OUTPUT_IMAGE}")
    return 0

if __name__ == "__main__":
    exit(main())
