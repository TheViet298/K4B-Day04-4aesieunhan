# TEAM — Day04, K4-L3B

**Làm nhóm.** Mỗi người tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

- Tên nhóm: 4aesieunhan
- Người đại diện / MSSV: Ngô Thế Việt - 2A202602594
- Tên repo:  K4B-Day04-4aesieunhan
- URL repo, nhánh nộp, commit chốt: https://github.com/TheViet298/K4B-Day04-4aesieunhan.git - main
- Deadline áp dụng và link thông báo đổi hạn nếu có: 10:00, 16/9/2026

## Thành viên

| Họ và tên | MSSV | GitHub | Vai trò và công việc | File/commit/PR |
|---|---|---|---|---|
| Ngô Thế Việt | 2A202602594 | TheViet298 | Leader & Prompt Engineering Lead: Quản lý repo, tinh chỉnh `system_prompt.md` & `tools.yaml` (v0-v3), chạy eval, ghi `version_log.csv`, tổng hợp `REPORT.md`. | Commit dff0b50 (Prompt v1 & version_log) |
| Nguyễn Quang Đạo | 2A202602394 | https://github.com/nguyenquangdao2004-glitch | Tool Registry & Safety/Adversarial Lead: Xây dựng tool schemas trong `tools/`, kiểm thử 12 case an toàn/adversarial, phân tích ranh giới an toàn & confirmation guardrails. | Commit 5e9d842 |
| Trần Vũ Gia Huy | 2A202602705 | https://github.com/jerrygiahuy | UI & Live Chat Trace Developer: Phụ trách `chat.py`/UI hiển thị tool call/input/kết quả/phiên bản, thực thi và xuất `transcripts/` minh chứng. | Commit d74a889 (tool trace và transcript); fdc0624 (INDIVIDUAL và MSSV) |
| Nguyễn Văn Giáp | 2A202602903 | https://github.com/Giappp | Eval Benchmark & Bonus Lead: Soạn 10 case nhóm (`eval_group.json`), nghiên cứu & phát triển chức năng mở rộng Bonus Feature (`network_diagnostic`), đánh giá metric. | Commit be1079b |

## Nhận xét chung

- Kết quả và bằng chứng: Toàn bộ quy trình v0-v3 đã được kiểm thử với 100% test cases cơ bản và 100% test cases an toàn (Adversarial) đạt PASS. Bộ 10 test case nhóm và Bonus feature `network_diagnostic` đã hoàn thiện kèm dữ liệu kiểm thử.
- Thay đổi hiệu quả nhất: Chuẩn hóa quy tắc `clarify` khi thiếu thông tin, cơ chế confirmation bắt buộc trước khi tạo ticket, và xây dựng tool schema chặt chẽ trong `tools.yaml`.
- Giới hạn còn lại: Khả năng phản hồi đa ngôn ngữ nâng cao và xử lý các kịch bản network phức tạp hơn cần thêm dữ liệu chuyên sâu.
- Cách phân công và tích hợp: Trưởng nhóm điều phối repo và prompt, các thành viên đảm nhận Tool Registry & Safety, UI Trace, Eval Benchmark & Bonus Tool.

## INDIVIDUAL

Sao chép mục này cho từng thành viên. Mỗi thành viên tự viết và commit phần việc kỹ thuật của mình.

### Ngô Thế Việt — 2A202602594

- Phần việc và file/commit/PR: Quản lý repo, cấu hình môi trường, tinh chỉnh system_prompt.md và tools.yaml qua các phiên bản (v0->v3), chạy eval và tổng hợp REPORT.md.
- Quyết định, khó khăn và cách xử lý: Gặp lỗi 429 Rate Limit khi chạy Gemini, đã xử lý bằng cách thêm cơ chế exponential backoff retry và chuyển qua OpenRouter GPT-4o-mini để đo đạc chuẩn
- Điều đã học: Hiểu sâu về Tool Calling loop, cách viết System Prompt có ràng buộc ranh giới an toàn
- AI/công cụ đã dùng và cách kiểm tra: Dùng Antigravity IDE hỗ trợ phân tích log run JSON và viết test
- Thời điểm đã tự nộp URL repo chung trên VLearn:  

### Nguyễn Quang Đạo — 2A202602394

- Phần việc và file/commit/PR:
  - Khai báo và chuẩn hóa toàn bộ Tool Schemas trong `starter_v0/artifacts/tools.yaml` (thiết lập ranh giới an toàn cho `create_ticket`, `clarify`, `search_device_info`).
  - Thực thi kiểm thử bộ 12 test case an toàn (`data/eval_adversarial.json`) với run evidence: `runs/v2_B_adversarial_gemini_20260915T204457659016.json`.
  - Phân tích chi tiết 3 trường hợp tấn công (A04 Argument Smuggling, A06 Internal Data Exfiltration, A10 Stale Confirmation Attack) và hoàn thiện mục B4a & B6 (Safety Review) trong `REPORT.md`.
- Quyết định, khó khăn và cách xử lý:
  - Khó khăn: Ở bản gốc v0, Agent thường xuyên tự ý gọi `create_ticket` mà không hỏi xác nhận người dùng, và khi gặp rate limit HTTP 429 từ provider thì script bị dừng ngang làm fail 13 cases.
  - Quyết định xử lý: Bổ sung cơ chế auto-retry backoff trong adapter provider; đồng thời chuẩn hóa rõ mô tả `clarify` (3 mode: text, yes_no, choice) và siết chặt ranh giới `create_ticket` trong `tools.yaml` để giải quyết dứt điểm các lỗi missing_info và wrong_boundary.
- Điều đã học:
  - Hiểu sâu sắc cơ chế Tool Calling / Function Calling của LLM: Mô hình ra quyết định gọi tool phụ thuộc rất lớn vào mô tả ngữ nghĩa (semantic description) và kiểu dữ liệu (enum, schema).
  - Nắm vững các kỹ thuật tấn công prompt phổ biến (Argument Smuggling qua pseudo-code, Stale Confirmation, Retrieval Injection) và sự cần thiết của việc xây dựng guardrail đa tầng (tầng prompt + tầng code deterministic).
- AI/công cụ đã dùng và cách kiểm tra:
  - Sử dụng Antigravity Coding Assistant để hỗ trợ phân tích code, tối ưu YAML schema và rà soát failure trace.
  - Kiểm chứng 100% bằng việc chạy eval thực tế qua script `run_eval.py` và kiểm tra filesystem (`tickets/`).
- Thời điểm đã tự nộp URL repo chung trên VLearn:

### Gia Huy — 2A202602705

- Phần việc và file/commit/PR: Cải thiện `starter_v0/chat.py` để hiển thị tên tool, arguments bằng tiếng Việt và kết quả/lỗi; lưu transcript chạy thật trong `starter_v0/transcripts/`. Đã commit phần trace và transcript tại `d74a889`. Xây dựng khung UI Streamlit và gộp vào `chat.py`, có lịch sử chat, chi tiết tool và tải transcript demo; phần UI chưa kết nối logic AI của nhóm.

- Quyết định, khó khăn và cách xử lý: Gặp lỗi cấu hình API key, lỗi kết nối và giới hạn quota 429 của Gemini. Kiểm tra lại `.env`, lưu log lỗi và dùng chế độ Demo để tiếp tục làm UI. Khi AI trả lời bằng văn bản mô phỏng gọi tool, điều chỉnh cách ghi lịch sử tool trong `chat.py`; phiên chạy sau đã gọi tool thật. Sửa vị trí file để chạy đúng trong `starter_v0`.

- Điều đã học: Phân biệt lời gọi tool thật với văn bản mô tả gọi tool; hiểu vai trò của arguments, kết quả tool và lịch sử hội thoại. Biết xây dựng UI Streamlit, kiểm tra transcript và làm việc trên nhánh Git riêng.

- AI/công cụ đã dùng và cách kiểm tra: Dùng ChatGPT hỗ trợ phân tích lỗi, viết và gộp code; VS Code, Terminal, Git và Streamlit để triển khai. Kiểm tra cú pháp bằng `python -m py_compile`, xem git diff, chạy chat Gemini và đối chiếu log. Đã quan sát tool `clarify` chạy thật và AI nhắc đúng vấn đề đăng nhập; lượt kết thúc trong cùng phiên bị lỗi 429 nên chưa xác nhận hoàn tất toàn bộ kịch bản.

- Thời điểm đã tự nộp URL repo chung trên VLearn: [Điền ngày, giờ sau khi thực sự nộp]

### Nguyễn Văn Giáp — 2A202602903

- Phần việc và file/commit/PR: Xây dựng bộ 10 test case nhóm (eval_group.json), nghiên cứu và triển khai 01 chức năng network_diagnostic - kèm thêm bộ dữ liệu kiểm thử (eval_network_diagnostic.json), kiểm thử chỉ số metric.
- Quyết định, khó khăn và cách xử lý: Gặp khó khăn khi viết tool và tạo bộ dữ liệu để kiểm thử tool vừa tạo, xử lý bằng cách sử dụng AI generate ra template mẫu -> dựa vào đó chỉnh sửa để cover hết các edge case.
- Điều đã học: Hiểu về Prompt Engineering có tác động như thế nào tới việc model xử lý thông tin và gọi tool - chỉ cần thay đổi 1 đoạn prompt cũng có thể ngăn chặn cơ số các prompt injection.
- AI/công cụ đã dùng và cách kiểm tra: Antigravity
- Thời điểm đã tự nộp URL repo chung trên VLearn: 15/09/2026
