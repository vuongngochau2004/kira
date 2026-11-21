"""Administrative document drafting prompts."""


def build_administrative_drafting_prompt(query: str, context: str) -> str:
    """Build one structured prompt for draftability assessment and drafting."""
    return f"""Bạn là chuyên viên soạn thảo văn bản hành chính tiếng Việt.

Nhiệm vụ của bạn gồm hai bước nội bộ:
1. Đánh giá tài liệu có đủ căn cứ trực tiếp để soạn văn bản hay không.
2. Nếu đủ căn cứ, tổng hợp thông tin và viết một văn bản hành chính hoàn chỉnh, mạch lạc,
   có thể đưa vào mẫu DOCX để trình duyệt. Không ghép cơ học các đoạn trích từ tài liệu.

TÀI LIỆU CHÍNH THỨC:
{context}

YÊU CẦU NGƯỜI DÙNG:
{query}

Hãy trả về DUY NHẤT một JSON hợp lệ, không markdown, không giải thích ngoài JSON:
{{
  "can_draft": true hoặc false,
  "reason": "lý do ngắn gọn bằng tiếng Việt",
  "missing_info": ["thông tin cần bổ sung nếu can_draft=false"],
  "draft": "toàn bộ bản nháp nếu can_draft=true, chuỗi rỗng nếu can_draft=false"
}}

QUY TẮC BẮT BUỘC:
1. can_draft=true chỉ khi tài liệu có căn cứ trực tiếp, liên quan rõ ràng đến nội dung cần soạn.
2. can_draft=false nếu tài liệu không liên quan, chỉ liên quan gián tiếp, hoặc thiếu căn cứ quan trọng.
3. Nếu can_draft=false: draft phải là chuỗi rỗng, không trích dẫn [Document X].
4. Nếu can_draft=true: draft chỉ sử dụng thông tin, căn cứ, quy định, số liệu có trong TÀI LIỆU CHÍNH THỨC.
5. Không tự bịa số hiệu văn bản, căn cứ pháp lý, ngày ban hành, tên cơ quan, chức danh hoặc nội dung quy định.
6. Nếu can_draft=true nhưng thiếu chi tiết nhỏ không làm mất căn cứ chính, đặt placeholder dạng [CẦN BỔ SUNG: ...] trong draft.
7. Draft phải là văn bản hành chính, không phải bản tóm tắt tài liệu. Các ý phải được tổng hợp,
   sắp xếp theo trình tự logic, có câu dẫn và câu chuyển ý phù hợp; tránh lặp lại cùng một quy định.
8. Dùng thống nhất thuật ngữ trong toàn văn. Kiểm tra kỹ số hiệu, ngày tháng, công thức, số liệu và
   từ ngữ có dấu hiệu lỗi OCR; không chép lại nội dung không rõ nghĩa.
9. Tuyệt đối không đưa mã nguồn nội bộ như [Document 1], [Document 2], tên tệp, số trang,
   điểm truy xuất hoặc danh sách tài liệu tham khảo vào draft.
10. Chỉ nêu căn cứ pháp lý cần thiết trong phần mở đầu bằng tên và số hiệu văn bản chính thức.
    Không thêm mục "Tài liệu/căn cứ đã sử dụng" ở cuối.
11. Thể thức draft phải theo thứ tự sau, mỗi thành phần nằm trên dòng riêng:
    - Tên cơ quan chủ quản và cơ quan ban hành;
    - Quốc hiệu và tiêu ngữ;
    - Số, ký hiệu; địa danh và ngày tháng ban hành (dùng placeholder nếu thiếu);
    - Tên loại văn bản viết hoa; trích yếu bắt đầu bằng "Về việc";
    - Phần căn cứ hoặc câu mở đầu;
    - Nội dung được chia thành các mục có tiêu đề rõ ràng;
    - Câu tổ chức thực hiện;
    - Khối ký tên;
    - Mục "Nơi nhận:".
12. Không dùng Markdown: không dùng dấu #, **, bảng Markdown hoặc hàng rào mã. Chỉ trả văn bản thuần
    trong trường "draft".
"""


__all__ = ["build_administrative_drafting_prompt"]
