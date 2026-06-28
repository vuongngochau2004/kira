#!/usr/bin/env bash
# Exit immediately if any command exits with a non-zero status
set -e

# Colors for terminal output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}          STARTING END-TO-END RAG EVALUATION BENCHMARK WORKFLOW        ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# Ensure we are in the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Step 1: Uploading and processing subset documents
echo -e "\n${BLUE}[Step 1/4] Uploading subset documents & waiting for ingestion to complete...${NC}"
uv run python scripts/upload_subset_documents.py

# Check if user_id.txt was created
if [ ! -f dataset/user_id.txt ]; then
    echo -e "${RED}Error: dataset/user_id.txt was not created by the uploader script!${NC}"
    exit 1
fi

USER_ID=$(cat dataset/user_id.txt)
echo -e "${GREEN}Ingestion complete. Test User ID: ${USER_ID}${NC}"

# Step 2: Generating the Golden evaluation dataset
echo -e "\n${BLUE}[Step 2/4] Generating evaluation Golden Dataset from completed chunks...${NC}"
uv run python scripts/generate_eval_dataset_from_ingested_chunks.py \
  --user-id "$USER_ID" \
  --output dataset/generated_dataset.json \
  --dataset-id eval-subset-gold \
  --max-documents 43

# Step 3: Running DeepEval benchmark evaluation on the RAG pipeline
echo -e "\n${BLUE}[Step 3/4] Running DeepEval judge model benchmark on the RAG pipeline...${NC}"
uv run python -m src.modules.evaluation.cli run \
  --dataset dataset/generated_dataset.json \
  --user-id "$USER_ID" \
  --output-dir reports/evaluation

# Step 4: Visualizing dataset distribution & rendering charts
echo -e "\n${BLUE}[Step 4/4] Generating distribution graphs & displaying samples...${NC}"
uv run --with matplotlib --with seaborn python scripts/visualize_gold_dataset.py

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}    RAG EVALUATION PIPELINE COMPLETED SUCCESSFULLY!                   ${NC}"
echo -e "${GREEN}    Check 'reports/evaluation/' for detailed markdown/json reports.    ${NC}"
echo -e "${GREEN}    Check 'dataset/gold_dataset_distribution.png' for visual chart.   ${NC}"
echo -e "${GREEN}======================================================================${NC}"
