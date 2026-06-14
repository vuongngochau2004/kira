# High-Accuracy Document Processing Pipeline

Tài liệu này mô tả hướng chuyển pipeline ingest tài liệu sang chế độ ưu tiên độ
chính xác cao. Mục tiêu là không embed trực tiếp text OCR nhiễu, mà tạo một bản
`canonical_text` đã được đọc, hiệu chỉnh và kiểm chứng trước khi chunk/embed.

## Mục Tiêu

Pipeline mới:

```text
PDF
-> render từng trang ảnh 300-400 DPI
-> Docling lấy layout/thứ tự vùng nếu hữu ích
-> VLM transcription từng trang từ ảnh gốc
-> LLM correction + verification theo ảnh gốc
-> tạo canonical_text theo Điều/Khoản/Điểm
-> quality gate cuối
-> chunk theo cấu trúc pháp lý
-> embed canonical_text
-> lưu page image + VLM transcript + canonical text + confidence để audit
```

Nguyên tắc chính:

- `canonical_text` là nguồn duy nhất dùng cho chunking/embedding.
- VLM đọc ảnh gốc là nguồn chính; không chạy OCR phụ trong nhánh VLM để tránh
  chậm pipeline và đưa thêm tín hiệu nhiễu.
- `vlm_transcript`, `docling_text` nếu có, page image và quality report chỉ dùng
  để audit, debug, verification hoặc reprocess.
- OCR thành công không đồng nghĩa với ingest thành công.
- PaddleOCR/PyMuPDF chỉ là fallback legacy khi Ollama/VLM lỗi provider, ví dụ
  sai key, model không tồn tại, mất network hoặc API trả lỗi.
- Nếu chất lượng cuối chưa đạt, document/page phải vào trạng thái
  `needs_review` hoặc `needs_reprocess`, không đưa vào vector index chính.

## Provider LLM Hiện Tại

Hệ thống đã chuyển LLM provider mặc định sang Ollama Cloud:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_API_KEYS=<your-ollama-api-key>
OLLAMA_MODEL=gemma4:31b-cloud
PDF_EXTRACTOR=vlm
PDF_RENDER_DPI=300
VLM_PAGE_CONCURRENCY=2
VLM_PAGE_VERIFICATION_ENABLED=true
VLM_VERIFY_ONLY_FAILED_PAGES=true
VLM_MIN_PAGE_COVERAGE_RATIO=0.7
LEGAL_CANONICALIZATION_ENABLED=false
LEGAL_CHUNKING_ENABLED=true
```

Kiểm tra provider:

```bash
env DEBUG=false .venv/bin/python - <<'PY'
import asyncio
from src.shared.infrastructure.llm.client import chat_async

async def main():
    result = await chat_async(
        [{"role": "user", "content": "Reply with exactly: OK"}],
        max_tokens=20,
        temperature=0,
        timeout=60,
    )
    print(result)

asyncio.run(main())
PY
```

Kỳ vọng:

```text
provider: ollama
model: gemma4:31b-cloud
content: OK
```

## Vai Trò Từng Thành Phần

### Docling

Docling vẫn hữu ích để:

- phân tích layout;
- nhận diện thứ tự vùng nội dung;
- nhận diện bảng, tiêu đề, list;
- tạo baseline text để so sánh.

Nhưng Docling không nên là nguồn text cuối cùng cho PDF scan hoặc PDF có text
layer lỗi encoding tiếng Việt.

### PaddleOCR/VietOCR

PaddleOCR service hiện dùng:

```text
PaddleOCR detect -> VietOCR recognize
```

Nên dùng để:

- fallback legacy khi VLM provider không hoạt động;
- debug thủ công ở `scripts/debug_ocr_sample.py --mode page-ocr`;
- xử lý ảnh đơn nếu workflow không đi qua VLM.

Không dùng PaddleOCR làm prepass cho pipeline VLM mặc định. Không embed trực
tiếp output OCR nếu quality score còn thấp.

### VLM Transcription

VLM đọc trực tiếp ảnh từng trang. Đây nên là nguồn chính cho tài liệu scan.

Input:

- ảnh trang gốc render từ PDF;
- nếu có, ảnh preprocess;
- optional: vùng layout từ Docling;

Output mong muốn:

```json
{
  "page": 1,
  "blocks": [
    {
      "type": "header",
      "text": "ĐẠI HỌC ĐÀ NẴNG\nTRƯỜNG ĐẠI HỌC BÁCH KHOA",
      "confidence": 0.94,
      "uncertain_spans": []
    },
    {
      "type": "article",
      "label": "Điều 1",
      "text": "Điều 1. ...",
      "confidence": 0.91,
      "uncertain_spans": []
    }
  ],
  "warnings": []
}
```

Prompt yêu cầu:

```text
Bạn là hệ thống transcription tài liệu hành chính tiếng Việt.

Nhiệm vụ:
- Chép lại nguyên văn nội dung chính nhìn thấy trên trang.
- Không tóm tắt.
- Không tự thêm thông tin.
- Giữ nguyên số quyết định, ngày tháng, tên cơ quan, Điều/Khoản/Điểm.
- Bỏ qua dấu mộc, watermark, chữ trang trí nếu không thuộc nội dung chính.
- Không bọc output trong code fence.
- Không dùng HTML entity như `&nbsp;`.
- Trả Markdown sạch.
```

## LLM Correction + Verification

Sau VLM transcription, pipeline chỉ chạy verification cho page fail quality gate
hoặc khi cấu hình `VLM_VERIFY_ONLY_FAILED_PAGES=false`.

Verification dùng:

- `vlm_text`;
- page image hoặc crop ảnh;
- dictionary/cụm từ hành chính phổ biến.

Nhiệm vụ correction:

- sửa lỗi transcription rõ ràng theo ảnh gốc;
- ghép dòng bị vỡ;
- chuẩn hóa dấu tiếng Việt;
- giữ nguyên nội dung pháp lý;
- không diễn giải;
- không tự bịa phần không đọc được;
- giữ `uncertain_spans` khi không chắc.

Prompt correction:

```text
Bạn là hệ thống hiệu chỉnh transcription tài liệu pháp quy tiếng Việt.

Chỉ được sửa lỗi/chính tả nhìn thấy rõ từ ảnh gốc hoặc nguồn đối chiếu đáng tin.
Không tóm tắt, không diễn giải, không thêm nội dung mới.
Ưu tiên giữ nguyên số quyết định, ngày tháng, điều khoản, tên cơ quan.
Nếu không chắc, giữ nguyên và đánh dấu uncertain.
Không dùng HTML entity như `&nbsp;`.
Không bọc output trong code fence.
Trả Markdown sạch.
```

## Canonical Text

`canonical_text` là bản cuối để chunk/embed.

Yêu cầu:

- Unicode NFC;
- giữ cấu trúc văn bản hành chính;
- giữ heading và nhãn điều khoản;
- loại bỏ watermark/dấu mộc nhiễu;
- không chứa dòng rác OCR;
- không chứa HTML entity như `&amp;`;
- có metadata page/block/confidence.

Ví dụ cấu trúc Markdown:

```markdown
# Quyết định số 1274/QĐ-ĐHBK

## Căn cứ

- Căn cứ Nghị định số ...
- Căn cứ Thông tư số ...

## Điều 1

Sửa đổi, bổ sung một số điều của "Quy định về liêm chính học thuật..."

### Điểm a Khoản 3 Điều 4

Các hành vi vi phạm tại phòng thi bị xử lý như sau:

- Khiển trách: ...
- Cảnh cáo: ...
```

## Quality Gate Cuối

Page/document sẽ có `quality_status=needs_review` nếu:

- `canonical_text` quá ngắn so với số trang;
- nhiều `uncertain_spans`;
- nhiều token rác hoặc mojibake;
- tỷ lệ dấu tiếng Việt thấp bất thường;
- thiếu các section quan trọng như số quyết định, ngày ban hành, Điều/Khoản;
- VLM/Docling mâu thuẫn ở thông tin quan trọng;
- confidence trung bình dưới ngưỡng.
- page-level verification làm giảm coverage dưới `VLM_MIN_PAGE_COVERAGE_RATIO`.

Metadata đề xuất:

```json
{
  "quality_status": "pass|needs_review|needs_reprocess",
  "page_warnings": [
    {"page": 4, "warnings": ["page_quality_failed", "page_coverage_too_low"]}
  ],
  "final_quality": {
    "score": 1,
    "issues": []
  }
}
```

## Chunking Theo Cấu Trúc Pháp Lý

Không chunk theo token thô nếu có thể nhận diện cấu trúc.

Ưu tiên chunk theo:

- document header;
- phần căn cứ;
- từng `Điều`;
- từng `Khoản`;
- từng `Điểm`;
- từng bảng/phụ lục.

Mỗi chunk nên có metadata:

```json
{
  "document_id": "...",
  "chunk_index": 3,
  "section_type": "article",
  "article": "Điều 1",
  "clause": "Khoản 3",
  "point": "Điểm a",
  "page_start": 1,
  "page_end": 2,
  "source": "canonical_text",
  "confidence": 0.91,
  "needs_review": false
}
```

## Dữ Liệu Cần Lưu Để Audit

Với mỗi document:

```text
data/document_processing/<document_id>/
├── pages/
│   ├── page_001.png
│   ├── page_001_preprocessed.png
│   └── ...
├── raw/
│   ├── docling.md
│   ├── paddleocr_page_001.txt
│   └── vlm_page_001.json
├── canonical/
│   ├── canonical_text.md
│   ├── canonical_blocks.json
│   └── quality_report.json
└── chunks/
    └── chunks.jsonl
```

Trong DB/vector store, chunk chỉ dùng `canonical_text`, nhưng metadata phải trỏ
ngược về page image và raw artifacts để kiểm tra khi cần.

## Trạng Thái Xử Lý Đề Xuất

```text
uploaded
-> extracting
-> transcribing
-> correcting
-> verifying
-> chunking
-> embedding
-> indexed
```

Trạng thái lỗi/chờ:

```text
needs_review
needs_reprocess
failed
```

## Migration Plan

1. Thêm module render page:

```text
src/modules/document/domain/services/page_renderer.py
```

2. Thêm VLM transcriber:

```text
src/modules/document/domain/services/vlm_transcriber.py
```

3. Thêm OCR correction:

```text
src/modules/document/domain/services/ocr_correction.py
```

4. Thêm canonical builder:

```text
src/modules/document/domain/services/canonical_builder.py
```

5. Thêm legal structure chunker:

```text
src/modules/document/domain/services/legal_chunker.py
```

6. Sửa pipeline:

```text
pipeline.py
-> extract raw signals
-> build canonical_text
-> final quality gate
-> legal chunk
-> embed canonical chunks
```

7. Cập nhật debug script để xuất đầy đủ:

```bash
env DEBUG=false .venv/bin/python scripts/debug_ocr_sample.py \
  "docs_eval_sample/file.pdf" \
  --output-dir reports/pipeline_debug
```

## Giai Đoạn Triển Khai Khuyến Nghị

### Phase 1: Shadow Mode

Chạy pipeline mới song song với pipeline cũ.

Không ghi vector DB, chỉ xuất report:

- rendered page image;
- VLM transcription;
- corrected canonical text;
- quality report;
- suggested chunks.

### Phase 2: Human Review

Chọn 20-50 trang đại diện:

- PDF scan trắng đen;
- PDF có dấu mộc;
- PDF có watermark;
- PDF có bảng;
- PDF có text layer lỗi encoding;
- PDF dài hơn 100 trang.

So sánh thủ công:

```text
Docling output
VLM transcription
Corrected canonical_text
```

### Phase 3: Controlled Ingest

Chỉ ingest document có:

- quality status `pass`;
- confidence đủ cao;
- số `uncertain_spans` thấp;
- chunk preview ổn.

### Phase 4: Full Re-ingest

Sau khi RAG evaluation tốt hơn, re-ingest toàn bộ tài liệu.

## Tiêu Chí Thành Công

Pipeline mới được coi là tốt hơn khi:

- câu trả lời RAG có citation đúng trang/điều khoản;
- `contextual_recall` tăng;
- `contextual_precision` không giảm;
- số chunk rác giảm rõ;
- người dùng đọc context thấy giống văn bản pháp quy thật;
- các truy vấn về số quyết định, ngày tháng, Điều/Khoản trả lời đúng.
