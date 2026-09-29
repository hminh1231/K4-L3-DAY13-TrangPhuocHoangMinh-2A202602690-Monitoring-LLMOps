# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Trang Phuoc Hoang Minh
- **MSSV:** 2A202602690
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/hminh1231/K4-L3-DAY13-TrangPhuocHoangMinh-2A202602690-Monitoring-LLMOps
- **Commit SHA cuối:**
- **Challenge ID:**
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602690`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100. 84 records; 60 thiếu field bắt buộc; 60 thiếu enrichment; 0 correlation ID. FAILED: required fields, correlation ID, enrichment. PASSED: PII scrubbing. | 100/100. 20 records; 0 thiếu field; 0 thiếu enrichment; 10 correlation ID; 0 PII leak. | Log cũ đã đổi tên `data/logs.baseline.jsonl` rồi đo lại. |
| `validate_dashboard.py` | HỢP LỆ: 6/6 panel có trong dashboard contract. | HỢP LỆ: 6/6 panel có trong dashboard contract. | Contract giữ nguyên 6 panel; runtime đọc `data/logs.jsonl`. |
| `pytest` | 22 passed (5.54s) | 24 passed | |
| Số traces hợp lệ | Chưa đo ở baseline. | 10 trace API, `prompt_source=langfuse`, version 1. | Cùng correlation ID với log. |
| Số PII leak | 0 | 0 | Email, điện thoại và số thẻ trong sample query đã thành `[REDACTED_*]`. |
| Latency P95 / TTFT P95 | Chưa đo. Load test chỉ in latency từng request; correlation ID trả về `MISSING`. | P95 latency 1187ms, TTFT P95 50ms trên 40 `response_sent`. | Cả hai dưới ngưỡng SLO 3000ms. |
| Retrieval success rate | Chưa đo ở baseline. | 100% | `tool_success == true` trên mọi response trong cửa sổ 60 phút. |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Mỗi request xóa context cũ. Nếu header `x-request-id` đúng dạng `req-<8-hex>` thì dùng ID đó, không thì sinh `req-` cộng 8 ký tự hex. ID được bind vào structlog và trả lại ở body cùng header `x-request-id`; thời gian xử lý nằm ở `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** Trước `request_received`, log được gắn `user_id_hash`, `session_id`, `feature`, `model`, `env`. `correlation_id` đi theo context của request.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` chạy trước `JsonlFileProcessor` và `JSONRenderer`. Pattern che email, điện thoại Việt Nam, CCCD 12 số và thẻ 16 số.
- **Cách kiểm chứng kết quả:** Đổi tên log baseline thành `data/logs.baseline.jsonl`, chạy lại load test rồi `python scripts/validate_logs.py` được 100/100. Pytest: 24 passed. Preview log còn `[REDACTED_EMAIL]`, không còn email/số điện thoại/số thẻ thô.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Project Langfuse `day13-k4-l3a-2A202602690`. Mười request `POST /chat` vừa chạy trả correlation ID `req-360dfb39`, `req-005cb053`, `req-c61eb900`, `req-493d26a0`, `req-8cef9c0e`, `req-c22a6977`, `req-fbb608b8`, `req-8602dfce`, `req-a3bef625`, `req-8e7a85cb`. Cùng các ID này nằm trong metadata trace.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` loại `agent`. Con: `retrieve-context` loại `retriever`, `generate-response` loại `generation` (model `claude-sonnet-4-5`, usage input/output, cost), và `score-answer-quality` loại `evaluator`. Input/output đã scrub PII.
- **Cách nối trace với log:** `correlation_id` được đưa vào trace metadata qua `propagate_attributes` và ghi trong structured log. Ví dụ log `req-360dfb39` khớp trace `dd6821d0d4388bd977a75cb66dffe308`.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** version 1, labels `baseline` và `production` (sau rollback).
- **Version/label candidate:** version 2, label `candidate`. Khác version 1 ở câu yêu cầu trả lời tối đa hai câu và trích docs khi khớp câu hỏi.
- **Trace ID của mỗi version:** baseline/v1 `b9bf6924addd2b455354e03430b69be8` (`req-b1a5e001`, label `baseline`). candidate/v2 `ca5e0afa7e111faf0481baaa0782d256` (`req-c2a5e002`, label `candidate`). Sau khi promote, production/v2 `a7903cb198304cb6a90dd9537b34d4c3` (`req-p2a5e003`).
- **Cách promote và rollback `production`:** Promote gán label `production` sang version 2 (trace ở trên ghi `prompt_version=2`, `prompt_label=production`). Rollback gán lại `production` cho version 1. Mười trace API sau rollback đều là `prompt_version=1`, `prompt_source=langfuse`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Contract `config/dashboard.yaml` đủ latency (P50/P95/P99 và TTFT P95), traffic, errors (error rate và retrieval success), cost, tokens, quality. Nguồn `data/logs.jsonl`, cửa sổ 60 phút, refresh 30 giây. Runtime: `python scripts/render_dashboard.py` ghi `submission/evidence/dashboard.html`.
- **SLO và lý do chọn:** SLO `fast_successful_requests`, cửa sổ 28 ngày, target 99.5%. Good event là `response_sent` với `latency_ms <= 3000`. Ngưỡng 3000ms cao hơn P99 hiện tại 1355ms và thấp hơn scenario `rag_slow` (2.5s cộng generate), nên chỉ đuôi bất thường mới đốt budget.
- **Cách tính error budget:** Error budget = 100 - 99.5 = 0.5% số `request_received` trong 28 ngày. Với 10 000 request thì được 50 request chậm hoặc không có response. Bad 2% đốt hết budget trong 7 ngày.
- **Ba alert và runbook tương ứng:** `slow_user_responses` (P95 > 3000ms trong 5 phút, warning), `users_receiving_errors` (error rate > 2% trong 5 phút, critical), `weak_answers` (quality < 0.75 hoặc retrieval success < 90% trong 10 phút, warning). Cả ba gửi Slack `#day13-k4-l3a-alerts`, owner `oncall-llmops`, runbook trong `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
