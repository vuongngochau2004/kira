#!/usr/bin/env bash
# Tự động hóa đồng bộ dữ liệu và đánh giá RAG trong 1 lệnh duy nhất
set -e

# Mã màu cho terminal
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}       HỆ THỐNG TỰ ĐỘNG ĐỒNG BỘ DỮ LIỆU & ĐÁNH GIÁ RAG (K.I.R.A)       ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# Step 0: Dọn dẹp sạch sẽ dữ liệu cũ bị lệch pha trên DB & Qdrant
echo -e "\n${YELLOW}[BƯỚC 0/3] Đang dọn dẹp sạch sẽ tài liệu cũ bị lệch pha trên PostgreSQL & Qdrant...${NC}"
uv run python scripts/delete_all_documents.py

# Step 1: Upload và đồng bộ tài liệu mới tinh
echo -e "\n${YELLOW}[BƯỚC 1/3] Đang tải lên tài liệu mới để đồng bộ hóa 100% ID...${NC}"
uv run python scripts/upload_subset_documents.py

# Đọc USER_ID mới được sinh ra
if [ ! -f dataset/user_id.txt ]; then
    echo -e "${RED}Lỗi: Không tìm thấy file dataset/user_id.txt!${NC}"
    exit 1
fi
USER_ID=$(cat dataset/user_id.txt)
echo -e "${GREEN}-> Đồng bộ thành công! USER_ID hoạt động: ${USER_ID}${NC}"

# Step 2: Chạy đánh giá RAG bằng dataset có sẵn
echo -e "\n${YELLOW}[BƯỚC 2/3] Đang chạy đánh giá chất lượng RAG (DeepEval Benchmark)...${NC}"
uv run python -m src.modules.evaluation.cli run \
  --dataset dataset/generated_dataset.json \
  --user-id "$USER_ID" \
  --output-dir reports/evaluation

# Step 3: Cập nhật lại biểu đồ trực quan tiếng Việt
echo -e "\n${YELLOW}[BƯỚC 3/3] Đang vẽ lại biểu đồ phân phối câu hỏi (Tiếng Việt)...${NC}"
uv run python scripts/visualize_gold_dataset.py

# Sao chép biểu đồ vào thư mục artifacts để hiển thị trong báo cáo
cp dataset/gold_dataset_distribution.png /home/nguyenhuynh/.gemini/antigravity-ide/brain/bc204eeb-46af-4de2-9cc1-9f567ce83670/gold_dataset_distribution.png || true

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN} 🎉 HOÀN THÀNH ĐỒNG BỘ VÀ ĐÁNH GIÁ RAG THÀNH CÔNG!${NC}"
echo -e "${GREEN} -> Xem báo cáo markdown mới nhất trong thư mục: reports/evaluation/${NC}"
echo -e "${GREEN} -> Biểu đồ phân phối tiếng Việt đã được cập nhật tự động!${NC}"
echo -e "${GREEN}======================================================================${NC}"
