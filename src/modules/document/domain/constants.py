"""Domain constants for OCR quality check and file processing configurations."""

import re

SUPPORTED_TYPES = {
    "pdf", "docx", "pptx", "xlsx", "html", "md", "txt",
}

OCR_TYPES = {"png", "jpg", "jpeg", "tiff", "bmp", "gif", "webp"}

VIETNAMESE_DIACRITICS = set(
    "áàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩị"
    "óòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ"
)

VIETNAMESE_UNACCENTED_SIGNAL_WORDS = {
    "bach", "ban", "bo", "can", "cac", "chinh", "cho", "cong", "cua", "dao",
    "dai", "dan", "danh", "dieu", "dinh", "doc", "duc", "duoc", "giao", "hoc",
    "hoa", "hoat", "hoi", "khoa", "khoan", "ly", "nam", "ngay", "nghi", "nguoi",
    "phuc", "quyet", "quy", "quan", "so", "tac", "tao", "thang", "thinh",
    "to", "truong", "tu", "van", "ve", "viet", "xa",
}

MOJIBAKE_OR_PLACEHOLDER_PATTERN = re.compile(r"[□ñ]|[A-Za-z][!&*][A-Za-z]")
HTML_ENTITY_PATTERN = re.compile(r"&(?:amp|quot|lt|gt|nbsp);")

QUALITY_ISSUE_WEIGHTS = {
    "low_quality_text": 3,
    "low_vietnamese_diacritics_ratio": 2,
    "many_unaccented_vietnamese_terms": 2,
    "mojibake_or_placeholder_chars": 2,
    "html_entities_in_text": 1,
    "many_alphanumeric_artifacts": 1,
}

CLEANER_PAGE_MARKER_PATTERN = re.compile(r"<!--\s*page\s+\d+\s*-->", re.IGNORECASE)

CHUNKER_PAGE_MARKER_PATTERN = re.compile(r"<!--\s*page\s+(\d+)\s*-->")

LEGAL_HEADING_PATTERN = re.compile(
    r"(?im)^(?:#{1,6}\s*)?(?:\*\*)?\s*(Điều\s+\d+[^\n]*|Chương\s+[IVXLCDM\d]+[^\n]*|Phụ\s*lục[^\n]*)"
)

