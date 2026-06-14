# Docling-First Document Processing

Tài liệu này mô tả cách chuyển pipeline xử lý tài liệu PDF sang hướng
Docling-first, đồng thời vẫn giữ fallback PaddleOCR hiện tại để hệ thống không
bị ngắt khi Docling chưa khả dụng hoặc gặp file khó.

## Mục Tiêu

Pipeline mới ưu tiên chất lượng text đầu vào cho RAG:

```text
PDF upload
-> Docling document conversion
-> nếu Docling thành công: dùng Markdown/text từ Docling
-> nếu Docling lỗi/chưa cài: render PDF page bằng PyMuPDF
-> OCR toàn bộ trang bằng PaddleOCR service hiện tại
-> chunk/embed/index như pipeline cũ
```

Lý do cần thay đổi: nhiều PDF hành chính có native text layer bị encoding lỗi.
Nếu chỉ dùng `page.get_text()` từ PyMuPDF, text có thể thành dạng:

```text
CONG HOA xA 1191 CHU NGHTA VIT NAM
Dc 1p - Tir do - Hinh phñc
```

Trong khi OCR lại đọc được gần đúng hơn:

```text
CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
```

## Code Đã Đổi

Các điểm chính:

- `src/modules/document/domain/services/extractor.py`
  - `extract_pdf()` ưu tiên Docling.
  - Nếu Docling lỗi, fallback sang PyMuPDF + PaddleOCR.
  - Khi fallback từ Docling, hệ thống force OCR toàn bộ trang thay vì tin native
    text layer.

- `src/config/config.py`
  - Thêm cấu hình:

```env
PDF_EXTRACTOR=docling
```

- `pyproject.toml`
  - Thêm optional extra:

```toml
[project.optional-dependencies]
docling = [
    "docling>=2.55.0",
]
```

## Cài Đặt Docling

Trên môi trường Linux/Docker/GPU nên cài:

```bash
uv sync --extra dev --extra docling
```

Trên macOS x86_64, Docling full có thể kéo các backend/model không có wheel phù
hợp, đặc biệt là Torch/backend native. Nếu cài không được, pipeline vẫn chạy vì
fallback PaddleOCR đã được giữ lại.

Kiểm tra Docling có import được không:

```bash
.venv/bin/python - <<'PY'
from docling.document_converter import DocumentConverter
print("Docling OK", DocumentConverter)
PY
```

## Cấu Hình Runtime

Mặc định:

```env
PDF_EXTRACTOR=docling
OCR_ENABLED=true
OCR_BASE_URL=http://100.84.187.107:8889
OCR_LANG=vi
OCR_TIMEOUT=30
OCR_MAX_RETRIES=3
```

Ý nghĩa:

- `PDF_EXTRACTOR=docling`: ưu tiên Docling cho PDF.
- `PDF_EXTRACTOR=pymupdf`: bỏ qua Docling, dùng pipeline PyMuPDF/PaddleOCR cũ.
- `OCR_BASE_URL`: PaddleOCR HTTP service đang dùng làm fallback.

## Fallback Behavior

Khi upload PDF:

1. Hệ thống gọi Docling.
2. Nếu Docling trả text hợp lệ:

```json
{
  "extractor": "docling",
  "engine": "docling",
  "ocr_used": true,
  "extraction_method": "docling"
}
```

3. Nếu Docling lỗi hoặc chưa cài:

```json
{
  "extractor": "pymupdf-ocr-hybrid",
  "engine": "fitz",
  "ocr_used": true,
  "ocr_pages": 26,
  "extraction_method": "ocr",
  "force_ocr_all": true,
  "fallback_from": "docling",
  "docling_error": "..."
}
```

Điểm quan trọng là `force_ocr_all=true`: khi Docling fail, hệ thống không còn
dùng native text layer có thể bị lỗi encoding nữa.

## Test Trước Khi Re-ingest

Chạy debug OCR/ảnh trên vài file mẫu:

```bash
.venv/bin/python scripts/debug_ocr_sample.py \
  "docs_eval_sample/04_Daotao_1562 QD BH Quy dinh moi thinh giang va quan ly cong tac thinh giang tai Truong DHBK-DHDN.PDF" \
  --pages 1-2 \
  --output-dir reports/ocr_debug
```

Output gồm:

- `page_001.png`: ảnh render từ PDF.
- `page_001_ocr_overlay.png`: ảnh có box OCR nếu service trả tọa độ.
- `page_001_native.txt`: text layer gốc từ PDF.
- `page_001_ocr.txt`: text OCR.
- `summary.md`: thống kê phương thức xử lý.

Sau đó test extractor thực tế:

```bash
.venv/bin/python - <<'PY'
import asyncio
from src.modules.document.domain.services.extractor import extract_content

async def main():
    result = await extract_content(
        "docs_eval_sample/04_Daotao_1562 QD BH Quy dinh moi thinh giang va quan ly cong tac thinh giang tai Truong DHBK-DHDN.PDF",
        "pdf",
    )
    print(result.success)
    print(result.metadata)
    print(result.text[:1000])

asyncio.run(main())
PY
```

Nếu Docling chưa cài, kết quả vẫn nên có:

```text
ocr_used: True
force_ocr_all: True
fallback_from: docling
```

## Re-ingest Tài Liệu

Các chunk cũ trong DB đã được tạo từ extractor cũ, nên muốn RAG tốt lên cần
upload/xử lý lại tài liệu.

Khuyến nghị:

1. Chạy thử 5 file trong `docs_eval_sample/`.
2. Kiểm tra chunk mới có text tốt hơn.
3. Sinh lại dataset đánh giá.
4. Chạy lại RAG evaluation.
5. Sau khi ổn mới re-ingest toàn bộ `docs_to_upload/`.

Upload smoke test:

```bash
.venv/bin/python scripts/bulk_upload_documents.py \
  --input-dir docs_eval_sample \
  --base-url http://localhost:8006 \
  --token "$ACCESS_TOKEN"
```

Sinh lại dataset:

```bash
.venv/bin/python scripts/generate_eval_dataset_from_ingested_chunks.py \
  --user-id "$USER_UUID" \
  --output data/evaluation/eval_smoke_docling.json \
  --max-documents 5 \
  --chunks-per-document 2 \
  --questions-per-chunk 2 \
  --no-answer-count 3
```

Validate dataset:

```bash
.venv/bin/python scripts/validate_eval_dataset.py \
  data/evaluation/eval_smoke_docling.json
```

Run evaluation:

```bash
python -m src.modules.evaluation.cli run \
  --dataset data/evaluation/eval_smoke_docling.json \
  --user-id "$USER_UUID" \
  --output-dir reports/evaluation \
  --run-name eval-smoke-docling
```

## Khi Nào Cần GPU

GPU hữu ích khi xử lý nhiều PDF scan hoặc tài liệu nhiều bảng/layout phức tạp.
GPU giúp tăng tốc các phần OCR/layout/table model. Tuy vậy chất lượng còn phụ
thuộc vào:

- độ phân giải scan;
- trang có nghiêng/mờ không;
- OCR model có hỗ trợ tiếng Việt tốt không;
- render DPI/zoom;
- chunking có giữ được điều/khoản/mẫu biểu không.

Với batch hơn 400 PDF, nên chạy Docling đầy đủ trên Linux/Docker có GPU nếu có
điều kiện. Nếu chưa có GPU, fallback PaddleOCR vẫn dùng được nhưng thời gian
upload sẽ lâu hơn khi force OCR toàn bộ trang.

## Checklist Triển Khai

1. Cài Docling ở môi trường phù hợp:

```bash
uv sync --extra dev --extra docling
```

2. Đảm bảo `.env`:

```env
PDF_EXTRACTOR=docling
OCR_ENABLED=true
OCR_BASE_URL=<paddleocr-service-url>
OCR_LANG=vi
```

3. Chạy debug vài PDF:

```bash
.venv/bin/python scripts/debug_ocr_sample.py "path/to/file.pdf" --pages 1-2
```

4. Upload lại 5 file mẫu.

5. Kiểm tra chunk trong DB/API.

6. Sinh lại dataset đánh giá.

7. Chạy RAG evaluation.

8. Nếu điểm `contextual_precision/contextual_recall` cải thiện, re-ingest toàn
bộ tài liệu.
