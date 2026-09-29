# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Trang Phuoc Hoang Minh
- **MSSV:** 2A202602690
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/hminh1231/K4-L3-DAY13-TrangPhuocHoangMinh-2A202602690-Monitoring-LLMOps
- **Commit SHA cuối:** PENDING_SHA
- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
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
| `validate_logs.py` | 30/100. 84 records; 60 thiếu field bắt buộc; 60 thiếu enrichment; 0 correlation ID. FAILED: required fields, correlation ID, enrichment. PASSED: PII scrubbing. | 100/100. 105 records; 0 thiếu field; 0 thiếu enrichment; 49 correlation ID; 0 PII leak. | Log cũ nằm ở `data/logs.baseline.jsonl`. File cuối gồm load test, challenge và một request kiểm tra CCCD. |
| `validate_dashboard.py` | HỢP LỆ: 6/6 panel có trong dashboard contract. | HỢP LỆ: 6/6 panel có trong dashboard contract. | Contract giữ nguyên 6 panel. Ảnh runtime là `evidence/11-dashboard-overview.png`. |
| `pytest` | 22 passed (5.54s) | 24 passed in 10.37s | |
| Số traces hợp lệ | Chưa đo ở baseline. | 23 root `lab-agent-run` có `prompt_source=langfuse`. Ảnh liệt kê 10 trace load test lúc 08:23Z, version 1, label `production`. | Cùng correlation ID với log. |
| Số PII leak | 0 | 0 | Email, điện thoại, số thẻ và CCCD trong input test đã thành `[REDACTED_*]`. |
| Latency P95 / TTFT P95 | Chưa đo. Load test chỉ in latency từng request; correlation ID trả về `MISSING`. | Cửa sổ steady-state: P95 latency 1187ms, TTFT P95 50ms, 40 `response_sent`. | Cả hai dưới ngưỡng SLO 3000ms. Năm request `rag_slow` nằm ngoài cửa sổ của ảnh overview và được tách ở mục incident. |
| Retrieval success rate | Chưa đo ở baseline. | 100% | `tool_success == true` trên response trong cửa sổ 60 phút của ảnh overview. |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Mỗi request xóa context cũ. Nếu header `x-request-id` đúng dạng `req-<8-hex>` thì dùng ID đó, không thì sinh `req-` cộng 8 ký tự hex. ID được bind vào structlog và trả lại ở body cùng header `x-request-id`; thời gian xử lý nằm ở `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** Trước `request_received`, log được gắn `user_id_hash`, `session_id`, `feature`, `model`, `env`. `correlation_id` đi theo context của request.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` chạy trước `JsonlFileProcessor` và `JSONRenderer`. Pattern che email, điện thoại Việt Nam, CCCD 12 số và thẻ 16 số.
- **Cách kiểm chứng kết quả:** Đổi tên log baseline thành `data/logs.baseline.jsonl`, chạy lại load test rồi `python scripts/validate_logs.py` được 100/100 trên 105 records. Pytest: 24 passed. Log `req-360dfb39`, `req-8cef9c0e`, `req-a3bef625` và `req-cccd0001` chỉ còn `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]`, `[REDACTED_CCCD]`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Project Langfuse `day13-k4-l3a-2A202602690`. Có 23 root `lab-agent-run` với `prompt_source=langfuse`. Mười request `POST /chat` lúc 08:23Z trả correlation ID `req-360dfb39`, `req-005cb053`, `req-c61eb900`, `req-493d26a0`, `req-8cef9c0e`, `req-c22a6977`, `req-fbb608b8`, `req-8602dfce`, `req-a3bef625`, `req-8e7a85cb`. Cùng các ID này nằm trong metadata trace, ảnh `evidence/06-trace-list.png`.
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

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (cohort K4, incident `rag_slow`, feature `monitoring`, seed 1311, ngưỡng `latency_threshold_ms` = 2000).
- **Khoảng thời gian điều tra:** 2026-09-29 10:08:20Z–10:08:35Z (17:08:20–17:08:35 ICT). Dashboard 60 phút tính tới log cuối `2026-09-29T10:08:35.715919Z` chỉ còn đúng 5 request của challenge.
- **Triệu chứng từ metrics:** Panel latency breach. Trên 5 `response_sent`: P50 2653ms, P95 3852ms, P99 3852ms, TTFT P95 50ms. P95 vượt ngưỡng dashboard 3000ms và cả 5 request vượt ngưỡng challenge 2000ms. Error rate 0%, retrieval success 100%, quality mean 0.84, cost tổng 0.0093 USD. Không phải lỗi tool và không phải cost spike. Ảnh: `evidence/12-incident-metric.png`.
- **Log line và correlation ID liên quan:** Request kéo P95 là `req-3de57ec1`, event `response_sent` lúc `2026-09-29T10:08:25.080534Z`, `feature=monitoring`, `latency_ms=3852`, `ttft_ms=50`, `tool_success=true`, `quality_score=0.8`. Bốn request còn lại cùng feature cũng chậm: `req-c8b7c33e` 2653ms, `req-17a5ab1a` 2653ms, `req-299a7a7d` 2652ms, `req-77fbc891` 2654ms. Ảnh: `evidence/13-incident-log.png`.
- **Trace ID và span gây ảnh hưởng:** Trace `9c9522669cb444ec6ea1b561978cd4b7` có metadata `correlation_id=req-3de57ec1`. Span `retrieve-context` (retriever) 2.502s, `generate-response` (generation) 0.151s với TTFT 50ms, root `lab-agent-run` 3.853s. Khoảng ~1.2s nằm giữa lúc retrieval kết thúc (10:08:23.729Z) và generation bắt đầu (10:08:24.928Z), đúng chỗ `resolve_prompt` gọi Langfuse. Bốn trace kia cùng kiểu: retrieval ≈ 2.50s, generation ≈ 0.15s, agent ≈ 2.65s (`7c113b97d5ebaf008cb5d7ccaae10bcf`, `ea19baab4489c873371ea215e4173ada`, `a57bf86039d598b6d5b3473934b124db`, `31e3e662d4ba890aa1a7c0aa578693cf`). Ảnh: `evidence/14-incident-trace.png`.
- **Root cause:** Incident `rag_slow` chèn `time.sleep(2.5)` trong `retrieve()` trước khi trả tài liệu corpus `monitoring`. Span `retrieve-context` một mình đã vượt ngưỡng 2000ms trên mọi request, trong khi generation và TTFT vẫn bình thường, `tool_success` vẫn true. Request đầu `req-3de57ec1` còn chờ thêm khoảng 1.2s để lấy prompt `day13-chat` label `production` (cache 60 giây, timeout fetch 2 giây), nên latency thành 3852ms và đẩy P95 qua SLO dashboard 3000ms. Năm request chạy đồng thời, nhưng `chat` gọi `agent.run()` chặn event loop nên chúng xếp hàng. `latency_ms` trong log là thời gian xử lý của agent, không phải thời gian chờ phía client.
- **Fix action:** Đã tắt incident bằng `POST /incidents/rag_slow/disable`. Request kiểm tra `req-098212a6` (cùng feature `monitoring`) trả `latency_ms=155`, `ttft_ms=50`, dưới ngưỡng 2000ms. Với hệ thống thật: bỏ delay giả trong retriever, đặt timeout cho retrieval, và không chặn event loop bằng sleep đồng bộ.
- **Preventive measure:** Giữ alert `slow_user_responses` (P95 &gt; 3000ms trong 5 phút). Thêm cảnh báo theo span khi `retrieve-context` P95 &gt; 500ms, vì ngưỡng challenge 2000ms chặt hơn SLO dashboard 3000ms và cửa sổ sự cố này chỉ dài 15 giây nên alert 5 phút chưa kịp cháy. Bọc `resolve_prompt` bằng một span riêng để khoảng chờ fetch prompt hiện trên waterfall. Giữ `correlation_id` trong log và trace metadata để nối ba tín hiệu.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** PII được scrub hai lần: `summarize_text` trước khi tạo preview, rồi processor `scrub_event` chạy trước `JsonlFileProcessor`. Nếu scrub sau khi ghi file thì dòng log đã lọt. `correlation_id` được đưa vào trace metadata bằng `propagate_attributes`, không chỉ ghi ở log, để nối được `req-360dfb39` với trace `dd6821d0d4388bd977a75cb66dffe308`. Prompt fetch dùng cache 60 giây, timeout 2 giây, `max_retries=0` và fallback local: Langfuse chậm không làm hỏng request, đổi lại request đầu sau khi hết cache chờ thêm khoảng fetch. Khoảng đó hiện trên `req-3de57ec1` (~1.2s) và trên waterfall `req-360dfb39` (retrieval kết thúc 08:23:14.908Z, generation bắt đầu 08:23:15.942Z).
- **Một lỗi/blocker đã gặp:** Sau khi sửa logging, `validate_logs.py` vẫn 30/100 vì validator đọc cả `data/logs.jsonl` cũ (84 records, 0 correlation ID). Trace đầu còn `correlation_id=MISSING` và `prompt_source=local-fallback` khi prompt `day13-chat` chưa có trên project. SDK Langfuse timeout mặc định 5 giây bị lỗi read timeout 0 khi connect chậm.
- **Cách tìm nguyên nhân và xử lý:** Đối chiếu scorecard với file log: field thiếu và enrichment thiếu nằm ở các dòng ghi trước khi bind context. Đổi file đó thành `data/logs.baseline.jsonl`, chạy lại load test, validator lên 100/100. Tạo prompt v1/v2 rồi chạy lại workload; metadata chuyển sang `prompt_source=langfuse`. Trong `app/tracing.py` đặt `LANGFUSE_TIMEOUT=20` trước khi import client.
- **Cách hiểu luồng Metrics → Logs → Traces:** Panel latency cho biết đuôi chậm và khoảng thời gian. Lọc `response_sent` trong khoảng đó lấy `correlation_id`. Mở trace cùng ID rồi so sánh span. Với challenge, P95 3852ms dẫn tới `req-3de57ec1`; span `retrieve-context` 2.502s trong khi `generate-response` 0.151s và TTFT 50ms, nên nguyên nhân là retrieval `rag_slow`, không phải model hay cost.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Label `production` chọn prompt đang phục vụ. V1 là baseline. V2 thêm ràng buộc trả lời tối đa hai câu và trích docs. Promote gán `production` sang v2, trace `a7903cb198304cb6a90dd9537b34d4c3` ghi `prompt_version=2`. Rollback trả `production` về v1; label hiện tại là v1 = `baseline` + `production`, v2 = `candidate` + `latest`, và các trace sau 08:14:39Z đều là v1. Token và cost trên generation cho biết prompt dài hơn có đốt tiền không. SLO 99.5% / 3000ms thành error budget 0.5%. Alert `slow_user_responses` bắn khi P95 vượt 3000ms trong 5 phút; `weak_answers` là chỗ rollback nếu chất lượng tụt ngay sau promote.
- **Điều quan trọng nhất đã học:** Metric, log và trace chỉ thành một kết luận khi cùng một `correlation_id`. Validator 6/6 chỉ chứng minh contract dashboard, không chứng minh panel có dữ liệu.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Cửa sổ sự cố chỉ khoảng 15 giây nên alert 5 phút chưa kịp cháy. Khoảng chờ `resolve_prompt` chưa có span riêng. `data/logs.jsonl` nằm trong `.gitignore` nên người chấm đối chiếu bằng evidence, không bằng file log trên Git. Ảnh trace/prompt lấy từ dữ liệu của project Langfuse cá nhân `day13-k4-l3a-2A202602690`; trang web Langfuse yêu cầu đăng nhập nên ảnh không phải giao diện web và không mở trang API Keys.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
