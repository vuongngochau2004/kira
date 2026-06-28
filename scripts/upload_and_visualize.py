import sys
import os
import asyncio
import time
import json
from pathlib import Path

# Automatically resolve the project root directory
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.append(PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from src.config.config import settings
from src.modules.document.domain.services.extractor import extract_pdf
from src.modules.document.domain.services.cleaner import clean_document
from src.modules.document.domain.services.chunker import chunk_document
from src.shared.adapters.ocr.paddleocr_adapter import PaddleOCRAdapter
from src.shared.adapters.embedding.api_adapter import EmbeddingAPIAdapter

async def run_pipeline_simulation():
    pdf_path = Path("./docs_to_upload/06-2022-bgddt.pdf")
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path.resolve()}")
        return

    output_dir = Path("./data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Ingestion Simulation Started for: {pdf_path.name}")
    print(f"Output directory initialized at: {output_dir.resolve()}\n")

    # Initialize adapters
    ocr_adapter = PaddleOCRAdapter()
    embedding_adapter = EmbeddingAPIAdapter()

    # Step 1: Document Extraction (Hybrid OCR/VLM)
    print("[Step 1/5] Extracting PDF content...")
    settings.pdf_extractor = "progressive"  # Force Hybrid Cascading
    start_time = time.time()
    ext_result = await extract_pdf(str(pdf_path), ocr=ocr_adapter)
    extract_duration = time.time() - start_time
    
    if not ext_result.success:
        print(f"Extraction failed: {ext_result.error}")
        return
        
    raw_text = ext_result.text
    print(f"Extraction completed in {extract_duration:.2f}s. Extracted {len(raw_text)} chars.")
    
    # Save Step 1 Output
    step1_file = output_dir / "step1_raw_text.txt"
    step1_file.write_text(raw_text, encoding="utf-8")
    print(f"-> Saved Step 1: {step1_file.resolve()}")
    
    # Step 2: Text Cleaning
    print("[Step 2/5] Cleaning document text...")
    start_time = time.time()
    cleaned_text = clean_document(raw_text)
    clean_duration = time.time() - start_time
    print(f"Cleaning completed in {clean_duration:.2f}s. Cleaned text length: {len(cleaned_text)} chars.")
    
    # Save Step 2 Output
    step2_file = output_dir / "step2_cleaned_text.txt"
    step2_file.write_text(cleaned_text, encoding="utf-8")
    print(f"-> Saved Step 2: {step2_file.resolve()}")

    # Step 3: Semantic Chunking
    print("[Step 3/5] Chunking text...")
    start_time = time.time()
    doc_id = "demo-doc-1234-5678"
    chunks = chunk_document(text=cleaned_text, document_id=doc_id)
    chunk_duration = time.time() - start_time
    print(f"Chunking completed in {chunk_duration:.2f}s. Generated {len(chunks)} chunks.")
    
    # Save Step 3 Output
    chunks_data = [
        {
            "index": c.index,
            "content": c.content,
            "token_count": c.token_count,
            "metadata": c.metadata
        }
        for c in chunks
    ]
    step3_file = output_dir / "step3_chunks.json"
    with open(step3_file, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)
    print(f"-> Saved Step 3: {step3_file.resolve()}")

    # Step 4: Embedding generation
    print("[Step 4/5] Generating embeddings via API adapter...")
    start_time = time.time()
    chunk_contents = [c.content for c in chunks]
    embeddings = await embedding_adapter.embed_batch(chunk_contents)
    embed_duration = time.time() - start_time
    print(f"Embedding completed in {embed_duration:.2f}s. Generated {len(embeddings)} vectors.")
    
    # Save Step 4 Output
    embeddings_summary = []
    for i, emb in enumerate(embeddings):
        embeddings_summary.append({
            "chunk_index": i,
            "vector_dimension": len(emb),
            "vector_preview": emb[:5]
        })
    step4_file = output_dir / "step4_embeddings.json"
    with open(step4_file, "w", encoding="utf-8") as f:
        json.dump(embeddings_summary, f, ensure_ascii=False, indent=2)
    print(f"-> Saved Step 4: {step4_file.resolve()}")

    # Step 5: Visualizing Results (Mermaid + Markdown report)
    print("[Step 5/5] Generating Visualization report...")
    
    path_taken = ext_result.metadata.get("progressive_path", "unknown")
    paddleocr_pages = ext_result.metadata.get("paddleocr_pages", [])
    vlm_pages = ext_result.metadata.get("vlm_pages", [])
    
    sample_raw = raw_text[:600] + "..." if len(raw_text) > 600 else raw_text
    sample_clean = cleaned_text[:600] + "..." if len(cleaned_text) > 600 else cleaned_text
    
    visual_report = f"""# Báo Cáo Trực Quan Hóa Từng Bước Xử Lý Tài Liệu (Pipeline Visualization)

Báo cáo này trực quan hóa toàn bộ các bước xử lý tài liệu trong ETL pipeline của KIRA cho tệp tin: **{pdf_path.name}**.

---

## Sơ Đồ Tổng Quan Luồng Xử Lý (ETL Flow)

```mermaid
graph TD
    A[Tài liệu PDF gốc: 06-2022-bgddt.pdf] -->|Bước 1: Extractor| B(Văn bản thô - Raw Text)
    B -->|Bước 2: Cleaner| C(Văn bản sạch - Cleaned Text)
    C -->|Bước 3: Chunker| D[Danh sách Chunks phân đoạn]
    D -->|Bước 4: Embedder| E[Vector Embeddings 1024-dim]
    E -->|Bước 5: Persistence| F[(Lưu trữ Vector & CSDL PostgreSQL)]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:1px
    style C fill:#bfb,stroke:#333,stroke-width:1px
    style D fill:#fbf,stroke:#333,stroke-width:1px
    style E fill:#fbb,stroke:#333,stroke-width:1px
    style F fill:#ffd,stroke:#333,stroke-width:2px
```

---

## Chi Tiết Các Bước Thực Thi

### 📄 Bước 1: Trích Xuất Văn Bản (Extraction)
*   **Chiến lược sử dụng:** `Hybrid Cascading (progressive)`
*   **Thời gian trích xuất:** `{extract_duration:.2f} giây`
*   **Tổng số trang trích xuất:** `{ext_result.pages}` trang
*   **Tổng số ký tự thô:** `{len(raw_text):,}` ký tự
*   **Đường đi thực tế:** `{path_taken.upper()}`
    *   Trang chạy qua PaddleOCR (nhanh): Trang {', '.join(map(str, paddleocr_pages)) or 'Không có'}
    *   Trang chạy qua VLM (chất lượng cao): Trang {', '.join(map(str, vlm_pages)) or 'Không có'}

> [!NOTE]
> **Văn bản thô mẫu (500 ký tự đầu):**
> ```text
> {sample_raw}
> ```

---

### 🧼 Bước 2: Làm Sạch Văn Bản (Cleaning)
*   **Thời gian thực hiện:** `{clean_duration:.4f} giây`
*   **Tổng số ký tự sau làm sạch:** `{len(cleaned_text):,}` ký tự
*   **Các quy tắc đã áp dụng:**
    *   Loại bỏ các mã HTML tags dư thừa.
    *   Chuẩn hóa bảng mã Unicode tiếng Việt về dạng NFC chuẩn.
    *   Làm sạch khoảng trắng, tab thừa bên trong các đoạn văn mà vẫn bảo toàn cấu trúc phân tách dòng (`\\n\\n`).

> [!NOTE]
> **Văn bản sau làm sạch mẫu (500 ký tự đầu):**
> ```text
> {sample_clean}
> ```

---

### ✂️ Bước 3: Phân Đoạn Văn Bản (Semantic Chunking)
*   **Thời gian thực hiện:** `{chunk_duration:.4f} giây`
*   **Tổng số Chunks được tạo ra:** `{len(chunks)}` chunks
*   **Thuật toán phân tách:** Phân tách ngữ nghĩa kết cấu văn bản (Legal-aware semantic chunking), ưu tiên giữ nguyên cấu trúc Điều/Chương/Phụ lục.

#### Thống kê 5 Chunks đầu tiên:

| Chunk Index | Độ dài (Ký tự) | Số Tokens | Metadata / Số trang |
| :---: | :---: | :---: | :---: |
"""
    for i, c in enumerate(chunks[:5]):
        page_start = c.metadata.get("page_start", c.metadata.get("page_number", "N/A"))
        page_end = c.metadata.get("page_end", "N/A")
        page_str = f"Trang {page_start}" if page_start == page_end or page_end == "N/A" else f"Trang {page_start}-{page_end}"
        visual_report += f"| `{c.index}` | `{len(c.content):,}` | `{c.token_count}` | `{c.metadata.get('section_type', 'paragraph')} ({page_str})` |\n"

    visual_report += f"""
---

#### Nội dung mẫu của Chunk đầu tiên (Index 0):
*   **Metadata:** `{json.dumps(chunks[0].metadata, ensure_ascii=False)}`
*   **Nội dung:**
```markdown
{chunks[0].content}
```

---

### 🧬 Bước 4: Nhúng Vector (Vector Embedding)
*   **Thời gian thực hiện:** `{embed_duration:.2f} giây`
*   **Kích thước chiều Vector (Dimension):** `{len(embeddings[0])}` chiều
*   **API Model Server:** `{settings.embedding_model}`

#### Bản xem trước Vector (Preview) của 3 Chunks đầu tiên (5 chiều đầu):

| Chunk Index | Vector Dimension | 5 Chiều Float Đầu Tiên |
| :---: | :---: | :--- |
"""
    for i, emb in enumerate(embeddings[:3]):
        preview = ", ".join(f"{v:.5f}" for v in emb[:5])
        visual_report += f"| `{i}` | `{len(emb)}` | `[{preview}, ...]` |\n"

    visual_report += f"""
---

### 💾 Bước 5: Lưu Trữ CSDL (Persistence)
*   **Database chính:** Lưu trữ nội dung văn bản gốc và Metadata của `{len(chunks)}` chunks vào bảng PostgreSQL `document_chunks`.
*   **Vector Database:** Lưu `{len(embeddings)}` vector `{len(embeddings[0])}` chiều vào Collection Qdrant tương ứng của người dùng.
"""
    
    # Save visual report
    report_file = output_dir / "pipeline_visualization.md"
    report_file.write_text(visual_report, encoding="utf-8")
    
    print(f"\nAll files generated successfully in {output_dir.resolve()}:")
    print(f"1. Raw Text: {step1_file.resolve()}")
    print(f"2. Cleaned Text: {step2_file.resolve()}")
    print(f"3. Chunks: {step3_file.resolve()}")
    print(f"4. Embeddings Preview: {step4_file.resolve()}")
    print(f"5. Visual Report: {report_file.resolve()}")

if __name__ == "__main__":
    asyncio.run(run_pipeline_simulation())
