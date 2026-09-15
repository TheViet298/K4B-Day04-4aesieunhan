# 📈 BÁO CÁO TIẾN TRÌNH & KẾT QUẢ KỸ THUẬT (NGÔ THẾ VIỆT)
**Vai trò:** Leader & Prompt Engineering Lead  
**MSSV:** 2A202602594 | **GitHub:** TheViet298  
**Nhánh làm việc:** `main` | **Model Provider:** OpenRouter (`openai/gpt-4o-mini`)  

---

## 🎯 1. CÁC ĐẦU VIỆC ĐÃ HOÀN THÀNH

| STT | Nhiệm vụ kỹ thuật | File liên quan | Trạng thái |
|:---:|---|---|:---:|
| 1 | Khởi tạo môi trường, cấu hình `.env`, test `preflight_provider.py` | `starter_v0/.env`, `requirements.txt` | ✅ Đã xong |
| 2 | Cấu hình cơ chế chống lỗi Rate Limit (429) cho provider | `starter_v0/providers/gemini_provider.py` | ✅ Đã xong |
| 3 | Chạy đo đạc bộ 30 test cases phiên bản gốc **`v0` (Baseline)** | `starter_v0/runs/v0_B_base_openrouter_20260915T203839229683.json` | ✅ 30/30 cases |
| 4 | Tinh chỉnh Prompt Engineering phiên bản **`v1`** giải quyết `missing_info` & `wrong_boundary` | `starter_v0/artifacts/system_prompt.md` | ✅ Đã xong |
| 5 | Chạy đo đạc bộ 30 test cases phiên bản **`v1`** | `starter_v0/runs/v1_B_base_openrouter_20260915T204130452503.json` | ✅ 30/30 cases |
| 6 | Cập nhật nhật ký các phiên bản vào `version_log.csv` | `starter_v0/artifacts/version_log.csv` | ✅ Đã ghi v0, v1 |

---

## 📊 2. BẢNG ĐO ĐẠC SO SÁNH (METRIC EVIDENCE)

### Bảng chỉ số tổng quan (Before / After):

| Phiên bản | Artifact Version | Prompt Hash | Tool Routing Accuracy | Multiturn Accuracy | Provider Errors | File Run Evidence |
|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **v0** | `v0+p27467914bc4d+td4848549884e` | `27467914bc4d...` | **76.67%** (23/30) | **80.00%** (8/10) | `0` (Hợp lệ) | [`runs/v0_B_base_openrouter_*.json`](starter_v0/runs/v0_B_base_openrouter_20260915T203839229683.json) |
| **v1** | `v1+pd3cccfd84079+td4848549884e` | `d3cccfd84079...` | **90.00%** (27/30) | **90.00%** (9/10) | `0` (Hợp lệ) | [`runs/v1_B_base_openrouter_*.json`](starter_v0/runs/v1_B_base_openrouter_20260915T204130452503.json) |
| **Tiến bộ** | — | — | 📈 **+13.33%** | 📈 **+10.00%** | — | — |

---

## 🔍 3. CHI TIẾT CÁC CA LỖI ĐÃ KHẮC PHỤC THÀNH CÔNG Ở `v1`

1. **`M05_ticket_confirmation` (Hội thoại đa lượt & Xác nhận tạo Ticket):**
   * *Ở v0 (FAIL):* Agent tự ý tạo ticket ngay khi chưa có xác nhận rõ ràng của người dùng ở lượt trước.
   * *Ở v1 (PASS):* Đã tuân thủ quy tắc xác nhận, ghi nhớ ngữ cảnh và chỉ thực hiện tạo ticket khi người dùng đồng ý.
2. **`H17_triage_with_three_sources` (Phân loại & Triage sự cố từ nhiều nguồn):**
   * *Ở v0 (FAIL):* Gọi thiếu công cụ hoặc nhầm lẫn giữa kiểm tra máy và kiểm tra trạng thái dịch vụ.
   * *Ở v1 (PASS):* Đã gọi đầy đủ các công cụ cần thiết đồng thời.
3. **Cải thiện hành vi `clarify`:**
   * Tất cả các ca thiếu thông tin (`H10_missing_asset`, `H11_missing_employee`, `H12_confirm_before_ticket`, `H19_ambiguous_environment`) ở v1 **đều đã nhận diện và routing chính xác 100% vào tool `clarify`**.

---

## 📦 4. DANH SÁCH FILE SẴN SÀNG PUSH LÊN GITHUB

Các file thuộc phần việc của **Ngô Thế Việt** đã hoàn thành và sẵn sàng commit:

1. `starter_v0/artifacts/system_prompt.md` *(Bản tinh chỉnh v1)*
2. `starter_v0/artifacts/version_log.csv` *(Nhật ký đo đạc v0 và v1)*
3. `starter_v0/providers/gemini_provider.py` *(Code bổ sung retry & delay chống 429)*
4. `starter_v0/runs/v0_B_base_openrouter_20260915T203839229683.json` *(Bằng chứng chạy v0)*
5. `starter_v0/runs/v1_B_base_openrouter_20260915T204130452503.json` *(Bằng chứng chạy v1)*
6. `TEAM.md` *(Cập nhật thông tin thành viên & phân công)*
7. `NHIEM_VU_BAI_LAB.md` & `KET_QUA_TIEN_TRINH_THE_VIET.md` *(Tài liệu hướng dẫn và theo dõi)*

---

## 🚀 5. LỆNH GIT ĐỂ PUSH LÊN GITHUB NGAY

Bạn chỉ cần mở Terminal và chạy 3 lệnh sau:

```powershell
git add starter_v0/artifacts/system_prompt.md starter_v0/artifacts/version_log.csv starter_v0/providers/gemini_provider.py starter_v0/runs/ TEAM.md NHIEM_VU_BAI_LAB.md KET_QUA_TIEN_TRINH_THE_VIET.md
git commit -m "feat(prompt): optimize system_prompt.md to v1 and update version_log with v0-v1 eval results"
git push origin main
```
*(Lưu ý: Git sẽ tự động bỏ qua file `.env` theo cấu hình `.gitignore`, đảm bảo an toàn 100%).*
