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
| Gia Huy | 2A202602705 | https://github.com/jerrygiahuy | UI & Live Chat Trace Developer: Phụ trách `chat.py`/UI hiển thị tool call/input/kết quả/phiên bản, thực thi và xuất `transcripts/` minh chứng. | |
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

- Phần việc và file/commit/PR: Khai báo tool schemas trong tools.yaml và tools/, thực hiện kiểm thử 12 case adversarial/safety, phân tích lỗi an toàn và cơ chế xác nhận.
- Quyết định, khó khăn và cách xử lý:
- Điều đã học:
- AI/công cụ đã dùng và cách kiểm tra:
- Thời điểm đã tự nộp URL repo chung trên VLearn:

### Gia Huy — 2A202602705

- Phần việc và file/commit/PR: Cải thiện `starter_v0/chat.py` để hiển thị tên tool, arguments bằng tiếng Việt và kết quả/lỗi; lưu transcript chạy thật trong `starter_v0/transcripts/`. Đã commit phần trace và transcript tại `d74a889`. Xây dựng khung UI Streamlit và gộp vào `chat.py`, có lịch sử chat, chi tiết tool và tải transcript demo; phần UI chưa kết nối logic AI của nhóm.

- Quyết định, khó khăn và cách xử lý: Gặp lỗi cấu hình API key, lỗi kết nối và giới hạn quota 429 của Gemini. Kiểm tra lại `.env`, lưu log lỗi và dùng chế độ Demo để tiếp tục làm UI. Khi AI trả lời bằng văn bản mô phỏng gọi tool, điều chỉnh cách ghi lịch sử tool trong `chat.py`; phiên chạy sau đã gọi tool thật. Sửa vị trí file để chạy đúng trong `starter_v0`.

- Điều đã học: Phân biệt lời gọi tool thật với văn bản mô tả gọi tool; hiểu vai trò của arguments, kết quả tool và lịch sử hội thoại. Biết xây dựng UI Streamlit, kiểm tra transcript và làm việc trên nhánh Git riêng.

- AI/công cụ đã dùng và cách kiểm tra: Dùng ChatGPT hỗ trợ phân tích lỗi, viết và gộp code; VS Code, Terminal, Git và Streamlit để triển khai. Kiểm tra cú pháp bằng `python -m py_compile`, xem git diff, chạy chat Gemini và đối chiếu log. Đã quan sát tool `clarify` chạy thật và AI nhắc đúng vấn đề đăng nhập; lượt kết thúc trong cùng phiên bị lỗi 429 nên chưa xác nhận hoàn tất toàn bộ kịch bản.

- Thời điểm đã tự nộp URL repo chung trên VLearn: [Điền ngày, giờ sau khi thực sự nộp]

### Nguyễn Văn Giáp — 2A202602903

- Phần việc và file/commit/PR: Xây dựng bộ 10 test case nhóm (eval_group.json), nghiên cứu và triển khai 01 chức năng mở rộng Bonus Feature, kiểm thử chỉ số metric.
- Quyết định, khó khăn và cách xử lý:
- Điều đã học:
- AI/công cụ đã dùng và cách kiểm tra:
- Thời điểm đã tự nộp URL repo chung trên VLearn:
