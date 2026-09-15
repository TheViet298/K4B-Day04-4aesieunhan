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
| Ngô Thế Việt | 2A202602594 | TheViet298 | Leader & Prompt Engineering Lead: Quản lý repo, tinh chỉnh `system_prompt.md` & `tools.yaml` (v0-v3), chạy eval, ghi `version_log.csv`, tổng hợp `REPORT.md`. | |
| Nguyễn Quang Đạo | 2A202602394 | https://github.com/nguyenquangdao2004-glitch | Tool Registry & Safety/Adversarial Lead: Xây dựng tool schemas trong `tools/`, kiểm thử 12 case an toàn/adversarial, phân tích ranh giới an toàn & confirmation guardrails. | |
| Gia Huy | 2A20262075 | https://github.com/jerrygiahuy | UI & Live Chat Trace Developer: Phụ trách `chat.py`/UI hiển thị tool call/input/kết quả/phiên bản, thực thi và xuất `transcripts/` minh chứng. | |
| Nguyễn Văn Giáp | 2A202602903 | https://github.com/Giappp | Eval Benchmark & Bonus Lead: Soạn 10 case nhóm (`eval_group.json`), nghiên cứu & phát triển chức năng mở rộng Bonus Feature, đánh giá metric. | |

## Nhận xét chung

- Kết quả và bằng chứng:
- Thay đổi hiệu quả nhất:
- Giới hạn còn lại:
- Cách phân công và tích hợp:

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

### Gia Huy — 2A20262075

- Phần việc và file/commit/PR: Phát triển Chat UI (chat.py), hiển thị thông tin trace tool call, arguments, lỗi/kết quả và phiên bản agent, tạo và xuất các file transcript.
- Quyết định, khó khăn và cách xử lý:
- Điều đã học:
- AI/công cụ đã dùng và cách kiểm tra:
- Thời điểm đã tự nộp URL repo chung trên VLearn:

### Nguyễn Văn Giáp — 2A202602903

- Phần việc và file/commit/PR: Xây dựng bộ 10 test case nhóm (eval_group.json), nghiên cứu và triển khai 01 chức năng mở rộng Bonus Feature, kiểm thử chỉ số metric.
- Quyết định, khó khăn và cách xử lý:
- Điều đã học:
- AI/công cụ đã dùng và cách kiểm tra:
- Thời điểm đã tự nộp URL repo chung trên VLearn:
