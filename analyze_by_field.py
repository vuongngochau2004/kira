import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Đường dẫn file manifest.csv
csv_path = "docs_to_upload/_dut_vanban_manifest.csv"

if not os.path.exists(csv_path):
    print(f"Lỗi: Không tìm thấy file {csv_path}")
    exit(1)

# Đọc dữ liệu
try:
    df = pd.read_csv(csv_path)
except Exception as e:
    print(f"Lỗi khi đọc file CSV: {e}")
    exit(1)

# Xử lý dữ liệu cột 'field'
column_name = 'field'
if column_name not in df.columns:
    print(f"Lỗi: File CSV không có cột '{column_name}'")
    exit(1)

# Điền các giá trị thiếu bằng 'Không xác định' và loại bỏ khoảng trắng thừa
df[column_name] = df[column_name].fillna('Không xác định').astype(str).str.strip()

# Tính toán số lượng và tỷ lệ
field_counts = df[column_name].value_counts()
total_docs = len(df)

# In bảng thống kê ra terminal
print("\n" + "="*60)
print(f"{'THỐNG KÊ SỐ LƯỢNG TÀI LIỆU THEO LĨNH VỰC (FIELD)':^60}")
print("="*60)
print(f"{'Lĩnh vực':<40} | {'Số lượng':<8} | {'Tỷ lệ':<8}")
print("-"*60)
for field, count in field_counts.items():
    percentage = (count / total_docs) * 100
    print(f"{field:<40} | {count:<8} | {percentage:.2f}%")
print("="*60)
print(f"{'Tổng cộng':<40} | {total_docs:<8} | 100.00%")
print("="*60 + "\n")

# Thiết lập giao diện cho biểu đồ
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'DejaVu Sans'  # Font mặc định hỗ trợ tiếng Việt cơ bản trên Linux/Mac

fig, ax = plt.subplots(figsize=(12, 7))

# Vẽ biểu đồ cột ngang bằng seaborn
sns.barplot(
    x=field_counts.values,
    y=field_counts.index,
    hue=field_counts.index,
    palette="viridis",
    legend=False,
    ax=ax
)

# Thêm số lượng cụ thể vào cuối mỗi cột
for i, v in enumerate(field_counts.values):
    percentage = (v / total_docs) * 100
    ax.text(v + 1, i, f" {v} ({percentage:.1f}%)", va='center', fontweight='bold', color='#333333')

# Thiết lập tiêu đề và nhãn
ax.set_title("Phân bố số lượng tài liệu theo Lĩnh vực (Field)", fontsize=16, fontweight='bold', pad=20, color='#1a1a1a')
ax.set_xlabel("Số lượng tài liệu (bản)", fontsize=12, fontweight='bold', labelpad=10)
ax.set_ylabel("Lĩnh vực", fontsize=12, fontweight='bold', labelpad=10)

# Tối ưu hóa khoảng cách
plt.tight_layout()

# Lưu biểu đồ
output_image = "field_distribution.png"
plt.savefig(output_image, dpi=300)
print(f"-> Đã vẽ và lưu biểu đồ tại: {os.path.abspath(output_image)}")
