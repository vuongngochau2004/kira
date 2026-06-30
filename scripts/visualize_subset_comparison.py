#!/usr/bin/env python3
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    # Paths to manifests
    full_csv = "docs_to_upload/_dut_vanban_manifest.csv"
    sub_csv = "dataset/_subset_manifest.csv"

    if not os.path.exists(full_csv) or not os.path.exists(sub_csv):
        print("Lỗi: Không tìm thấy tệp CSV manifest.")
        return 1

    # Load data
    df_full = pd.read_csv(full_csv)
    df_sub = pd.read_csv(sub_csv)

    # Normalize fields
    df_full['field'] = df_full['field'].fillna('Không xác định').astype(str).str.strip()
    df_sub['field'] = df_sub['field'].fillna('Không xác định').astype(str).str.strip()

    # Group rare fields into "Khác"
    major_fields = ["Tổ chức, hành chính", "Đào tạo", "Thanh tra, kiểm tra", "Thi đua, khen thưởng", "Pháp chế"]
    df_full['field'] = df_full['field'].apply(lambda x: x if x in major_fields else "Khác")
    df_sub['field'] = df_sub['field'].apply(lambda x: x if x in major_fields else "Khác")

    # Calculate proportions
    pct_full = df_full['field'].value_counts(normalize=True) * 100
    pct_sub = df_sub['field'].value_counts(normalize=True) * 100

    # Get actual number of documents
    num_full = len(df_full)
    num_sub = len(df_sub)

    # Build comparison DataFrame
    categories = sorted(list(set(df_full['field'].unique()) | set(df_sub['field'].unique())))
    
    data = []
    for cat in categories:
        data.append({
            'Lĩnh vực': cat,
            'Tập dữ liệu': f'Tập Gốc ({num_full} tài liệu)',
            'Tỷ lệ (%)': pct_full.get(cat, 0.0),
            'Số lượng': int(df_full['field'].value_counts().get(cat, 0))
        })
        data.append({
            'Lĩnh vực': cat,
            'Tập dữ liệu': f'Tập Mẫu ({num_sub} tài liệu)',
            'Tỷ lệ (%)': pct_sub.get(cat, 0.0),
            'Số lượng': int(df_sub['field'].value_counts().get(cat, 0))
        })
        
    df_compare = pd.DataFrame(data)

    # Sort categories by Full Dataset proportion descending
    sorted_categories = pct_full.index.tolist()
    
    # Set aesthetics
    sns.set_theme(style="whitegrid")
    plt.rcParams['font.family'] = 'DejaVu Sans'
    
    fig, ax = plt.subplots(figsize=(14, 10))

    # Color palette
    colors = ["#1f77b4", "#ff7f0e"] # Premium blue and orange
    
    # Plot grouped bar chart
    sns.barplot(
        data=df_compare,
        y='Lĩnh vực',
        x='Tỷ lệ (%)',
        hue='Tập dữ liệu',
        order=sorted_categories,
        palette=colors,
        alpha=0.9,
        edgecolor='black',
        linewidth=0.8,
        ax=ax
    )

    # Add numeric labels at the end of each bar
    num_cats = len(sorted_categories)
    for idx, p in enumerate(ax.patches):
        width = p.get_width()
        if width > 0.1: # Skip zero values
            # Find the corresponding item in DataFrame to show actual count
            # Matplotlib patches are drawn in order of hues and then y-order
            hue_idx = idx // num_cats
            cat_idx = idx % num_cats
            
            cat = sorted_categories[cat_idx]
            dataset_name = f'Tập Gốc ({num_full} tài liệu)' if hue_idx == 0 else f'Tập Mẫu ({num_sub} tài liệu)'
            
            # Find count from df_compare
            match = df_compare[(df_compare['Lĩnh vực'] == cat) & (df_compare['Tập dữ liệu'] == dataset_name)]
            if not match.empty:
                count = match.iloc[0]['Số lượng']
                label_text = f"{width:.1f}% ({count} file)"
            else:
                label_text = f"{width:.1f}%"

            ax.text(
                width + 0.3,
                p.get_y() + p.get_height() / 2,
                label_text,
                va='center',
                ha='left',
                fontsize=9,
                fontweight='bold',
                color='#333333'
            )

    # Styling title, labels, and ticks
    ax.set_title(
        f"SO SÁNH PHÂN PHỐI LĨNH VỰC TÀI LIỆU\nTẬP GỐC ({num_full} FILE) vs TẬP MẪU ({num_sub} FILE)",
        fontsize=16,
        fontweight='bold',
        pad=25,
        color='#1a1a1a'
    )
    ax.set_xlabel("Tỷ lệ phần trăm (%) trên tổng số tài liệu", fontsize=12, fontweight='bold', labelpad=15)
    ax.set_ylabel("Lĩnh vực", fontsize=12, fontweight='bold', labelpad=15)
    
    # Adjust legend position and styling
    ax.legend(
        title="Tập dữ liệu",
        title_fontsize='11',
        loc='lower right',
        frameon=True,
        facecolor='white',
        edgecolor='#cccccc',
        fontsize=11
    )

    # Tighten layout and save image
    plt.tight_layout()
    output_path = "dataset/subset_vs_full_distribution.png"
    plt.savefig(output_path, dpi=300)
    print(f"Success: Saved visualization to {output_path}")
    return 0

if __name__ == "__main__":
    main()
