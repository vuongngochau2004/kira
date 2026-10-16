from src.modules.chat.api.endpoints import citation_contexts


def test_contexts_come_from_content_or_text() -> None:
    citations = [
        {"filename": "a.pdf", "content": "nội dung A", "text": "trích A"},
        {"filename": "Khoản 1 — Luật Thử (1/2099/QH99)", "text": "1. Nội dung khoản 1."},
        {"filename": "rỗng", "text": ""},
    ]
    assert citation_contexts(citations) == ["nội dung A", "1. Nội dung khoản 1."]


def test_no_citations_gives_no_contexts() -> None:
    assert citation_contexts([]) == []
