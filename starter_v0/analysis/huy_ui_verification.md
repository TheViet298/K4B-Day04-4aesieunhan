# Kiểm chứng UI & Live Chat — Trần Vũ Gia Huy, 2A202602705

Thực hiện ngày **16/09/2026**, sau merge `ef95955`, trên nhánh `huy/chat-ui-trace`.
Đây là bổ sung sau mốc 23:59 mặc định; không sửa lịch sử hoặc ngày commit.
Phạm vi: UI/CLI, tool trace, transcript, A4/B4 và INDIVIDUAL. Không chạy lại bộ eval
và không nhận công việc prompt/safety/bonus của các thành viên khác.

## Thay đổi kỹ thuật

- Một entry point `starter_v0/chat.py`: CLI giữ `main()` cùng các tham số cũ;
  Streamlit dùng `-- --ui`. `run_model_tool_loop`, `execute_tool_call`, các hàm
  định dạng/lưu transcript vẫn có mặt. UI và CLI dùng chung `submit_turn` và loop,
  gọi các adapter `providers/` và `TOOL_FUNCTIONS` đã merge, không chạy thêm một
  `HelpdeskAgent.run` song song (tránh thực thi tool hai lần).
- Demo dùng fixture ghi rõ `mode=demo`, không gọi API/registry; thư mục tự lưu
  `demo_transcripts/` bị Git ignore. Live giữ cấu trúc transcript của dự án và
  bổ sung `mode`, `request_id`; phiên nhận diện bằng UUID.
- Lịch sử theo từng cấu hình mode/provider/model/artifact. Cửa sổ 5 lượt giữ cả
  kết quả tool trước đó, kể cả lượt lỗi sau khi đã thực thi. Reset chỉ tác động phiên đang chọn.
- Checkpoint sau từng tool; lỗi model không xóa trace. Ghi file bằng atomic replace.
  Nếu đĩa lỗi, giữ phiên trong RAM và hiển thị lỗi để người dùng tải xuống.
- Request ID đã tồn tại không chạy lại; render/download/widget rerun không submit.
  Trong một lượt, mọi lần gọi `create_ticket` sau lần đầu bị chặn với
  `duplicate_write_blocked`, kể cả lần đầu báo lỗi không rõ trạng thái.
  Đây không phải hệ thống idempotency bền vững qua crash process hoặc nhiều thiết bị.
- Gemini chat đặt `max_attempts=1`; adapter mặc định vẫn 6 như code nhóm cho caller khác.
  Không tự retry quota hoặc toàn bộ lượt. Không thay prompt, tools.yaml hay bộ eval.
- `reply` trong JSON (kể cả code fence) chỉ dùng trình bày; phản hồi nguyên gốc
  nằm trong transcript. Không parse chuỗi mô tả tool thành hành động thực thi.
- CSS khai báo cả màu chữ/nền cho input, dropdown, cảnh báo, nút; không phụ thuộc
  `.streamlit/config.toml` hoặc thư mục đang chạy. Chưa xác minh bằng ảnh trình duyệt.

## Kiểm tra đã chạy

| Kiểm tra | Kết quả / bằng chứng |
|---|---|
| `python -m pip install -r starter_v0/requirements.txt` trong `.venv` | Dependency đã có; Streamlit 1.63.0, Python 3.14; không cần cài thêm gói |
| `python -m pip check` | `No broken requirements found` |
| `python -m py_compile` cho chat, Gemini adapter, smoke script | PASS |
| `python starter_v0/chat.py --help` | CLI giữ provider/model/version và các tham số cũ |
| `python -m unittest discover -s starter_v0/tests -v` | **15/15 PASS** — [log offline/mock](huy_offline_tests.txt), [mã test](../tests/test_chat.py) |
| Streamlit AppTest | Demo thành công/hỏi lại/lỗi, reset, đổi mode/model, lịch sử riêng, render lỗi và trace, payload JSON download Demo/Live, rerun không gọi lại provider |
| Test tool ghi dữ liệu | **Model mock**, công cụ `create_ticket` thật ghi vào thư mục tạm; sau xác nhận có 1 ticket, lỗi model tiếp theo vẫn giữ trace, submit lại cùng request ID không ghi lần hai |
| Server Streamlit từ gốc repo | Chạy trên cổng 8507, `/_stcore/health` trả `ok`; sandbox cần quyền mở port/network |
| Browser | Runtime trả danh sách browser rỗng; **chưa kiểm tra trực quan/screenshot hoặc thao tác tải file trên browser thật**. Đã kiểm tra payload download bằng AppTest |
| Rà credential | Các transcript mới không chứa giá trị API key/token cấu hình; không stage `.env`, cache, `.venv` hoặc ticket |
| `git diff --check` | PASS trước commit |

[Demo fixture ba kịch bản](huy_demo_fixture.json) là **mô phỏng**, không phải evidence Live.
Test offline có provider mock và một số công cụ dữ liệu giả lập thật; không chứng minh
model thực tuân thủ xác nhận/hủy. AppTest Live cũng dùng provider mock.

## Live: kết quả quan sát thực tế

Provider: `gemini`; model thực dùng: `gemini-3.5-flash-lite`.
Chỉ Gemini có API key cấu hình. Không đổi tài khoản/model để vượt quota, không bật billing.

Artifact thực dùng:

- `current+p5acbae7cbcb2+t17ea562ed15f`
- Prompt SHA-256: `5acbae7cbcb2e252f8c9f51bbb2251cb14657098290ba43665b93aa7a8e4ff07`
- Tools SHA-256: `17ea562ed15f462f0aae9abc8972e0029388dbd75d7a5f3c4b8b2d71ceb49daf`

Cả hai hash không khớp cặp hash v3 trong version log, nên không gắn nhãn v3.
Có 9 lượt nhận phản hồi API thật (1 probe + 8 lượt smoke); không chạy eval toàn nhóm.

| Tình huống | Transcript | Kết quả đúng theo trace |
|---|---|---|
| Probe VPN production | [probe](../transcripts/live_current_gemini_0404647f2cfe4133bcd2116579e0f6d2.transcript.json) | Có JSON văn bản; **0 tool calls**, chưa kiểm tra VPN thật |
| Tra cứu hợp lệ với VPN production | [lookup](../transcripts/live_current_gemini_589f8f7023e243b88451b40f6cd63a50.transcript.json) | Chỉ nói đang kiểm tra, **0 tool calls**, chưa đạt |
| Thiếu asset → bổ sung LT-204 → nhớ ngữ cảnh | [clarify/context](../transcripts/live_current_gemini_e38026e1fcd4474daa0bdc561c13d4b4.transcript.json) | Hỏi mã bằng văn bản; nhớ đúng LT-204 ở lượt 3; **không thực thi clarify/inspect_device** |
| Tạo ticket sau xác nhận rõ ràng | [confirmation](../transcripts/live_current_gemini_751f589592314767bb852c2138dbb44c.transcript.json) | Hỏi xác nhận bằng văn bản; sau đồng ý nói đã tạo nhưng **0 create_ticket**, không có bằng chứng ticket thành công. Đây là lỗi hành vi model |
| Hủy ticket và chuyển sang email production | [cancellation](../transcripts/live_current_gemini_91f9c704df864ecfb7adee388049904a.transcript.json) | Phản hồi đổi ý, không gọi create_ticket; nhưng cũng không kiểm tra email. Không đủ để tuyên bố toàn bộ luồng tool/hủy đạt |
| Lỗi kết nối sandbox trước khi cấp quyền mạng | [CLI connection error](../transcripts/live_current_gemini_80e86d6ed02743ccb4b5e9ff75a3f928.transcript.json), [smoke connection error](../transcripts/live_current_gemini_f646a9b36e204093b5fd1180f66e0937.transcript.json) | `provider_error`, lỗi DNS thật; lưu nguyên, không tính là quota hoặc API thành công |

[Index smoke](huy_live_smoke_index.json) và [script opt-in](../scripts/huy_live_smoke.py).
`status=answered` chỉ có nghĩa model trả văn bản, **không có nghĩa tác vụ/tool thành công**.
UI cảnh báo rõ lượt không thực thi tool; transcript giữ nguyên cả lời khẳng định sai của model.
Không sửa prompt nhóm hoặc tự parse `action`/`TOOL_CALLS_JSON` để tạo evidence thành công.

## Giới hạn và bàn giao

- UI/CLI đã nối backend thật; **Live tool calling và tạo ticket thành công chưa được kiểm chứng**
  với model/artifact hiện tại. Cần nhóm phụ trách prompt/provider kiểm tra lý do model
  chỉ mô tả hành động bằng JSON. Các transcript trên là failure evidence để đối chiếu.
- Chưa có browser khả dụng để kiểm chứng hình ảnh, contrast thực tế và download file trên trình duyệt.
- Không sửa transcript cũ, eval, số liệu nhóm, nội dung B4a/B5/B6 hay dữ liệu giả lập.
- Rà tài liệu source chính không thấy MSSV sai `2A20262075`; tên đầy đủ và mã đúng
  `2A202602705` được ghi trong TEAM và phân công. Không rà/sửa bản repo lồng ngoài phạm vi.
- Stash README chỉ chứa phần hướng dẫn; nội dung phù hợp đã ghép vào README hiện tại,
  sửa lại cú pháp `--ui`, bỏ hướng dẫn `--cli` và đường dẫn source gốc gây nhầm lẫn.
- Giữ nguyên `chat.py` ở gốc, repo lồng `K4B-Day04-4aesieunhan/` và 8 transcript cũ chưa tracked.
  Không xóa hoặc stage các file này. Không có ticket phát sinh từ các lượt Live mới.
- Chỉ commit local; không push, tạo PR, merge main, gửi tin nhắn hoặc nộp VLearn.
  Chưa có bằng chứng Huy đã nộp VLearn nên không điền thời gian nộp.
