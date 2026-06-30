import pytest
from src.modules.retrieval.domain.services.bm25_index import BM25Index, _tokenize


def test_vietnamese_tokenization_with_pyvi():
    """Kiểm tra xem tokenization tiếng Việt sử dụng pyvi có tạo ra từ ghép chính xác."""
    text = "Trí tuệ nhân tạo phát triển rất nhanh."
    tokens = _tokenize(text)
    
    # KIRA sử dụng pyvi để tách từ, nên "trí tuệ" và "nhân tạo" phải là từ ghép có dấu gạch dưới.
    assert "trí_tuệ" in tokens
    assert "nhân_tạo" in tokens
    # Các từ đơn vẫn hoạt động bình thường
    assert "đang" not in tokens  # từ này không có trong text
    assert "phát_triển" in tokens


def test_bm25_index_and_search_vietnamese():
    """Kiểm tra lập chỉ mục và tìm kiếm BM25 với tài liệu tiếng Việt."""
    documents = [
        {
            "content": "Quy định về việc xét tuyển sinh đại học chính quy năm nay.",
            "metadata": {"document_id": "doc-1", "chunk_index": 0}
        },
        {
            "content": "Hướng dẫn đăng ký nhập học và chuẩn bị hồ sơ sinh viên mới.",
            "metadata": {"document_id": "doc-2", "chunk_index": 0}
        },
        {
            "content": "Nghiên cứu về trí tuệ nhân tạo và các ứng dụng thực tiễn của học máy.",
            "metadata": {"document_id": "doc-3", "chunk_index": 0}
        }
    ]
    
    index = BM25Index()
    index.index_documents(documents)
    
    # 1. Tìm kiếm với từ khóa "trí tuệ nhân tạo"
    results_ai = index.search("trí tuệ nhân tạo", k=2)
    assert len(results_ai) > 0
    # Kết quả phù hợp nhất phải là doc-3
    assert results_ai[0]["metadata"]["document_id"] == "doc-3"
    
    # 2. Tìm kiếm với từ khóa "xét tuyển sinh"
    results_admission = index.search("xét tuyển sinh", k=2)
    assert len(results_admission) > 0
    # Kết quả phù hợp nhất phải là doc-1
    assert results_admission[0]["metadata"]["document_id"] == "doc-1"
