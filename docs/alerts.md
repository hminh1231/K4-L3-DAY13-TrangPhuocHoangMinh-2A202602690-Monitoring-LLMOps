# Alert và runbook

Mỗi alert bám triệu chứng người dùng hoặc SLO. Điều kiện lấy từ `config/slo.yaml` và `config/dashboard.yaml`. Kênh Slack: `#day13-k4-l3a-alerts`. Owner: `oncall-llmops`.

<a id="alert-1"></a>

## Alert 1 — slow_user_responses

- Tên: `slow_user_responses`
- Severity: warning
- Duration: 5m
- Kênh thông báo: Slack `#day13-k4-l3a-alerts`
- SLI/SLO liên quan: primary SLO `fast_successful_requests`. Good event là `response_sent` với `latency_ms <= 3000`. Target 99.5% trong 28 ngày, error budget 0.5%.
- Điều kiện và thời gian duy trì: P95 `latency_ms` của `response_sent` lớn hơn 3000ms liên tục 5 phút.
- Ảnh hưởng tới người dùng: câu trả lời tới muộn. Người dùng chờ quá lâu hoặc bỏ cuộc trước khi nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Latency (P50/P95/P99 và TTFT P95), khoanh khoảng 5 phút vừa cảnh báo.
  2. Lọc `data/logs.jsonl` event `response_sent` có `latency_ms > 3000`, lấy một `correlation_id`.
  3. Mở trace cùng `correlation_id` và so sánh thời lượng span `retrieve-context` với `generate-response`.
- Mitigation tạm thời: nếu span retrieval chiếm gần hết latency, tắt scenario `rag_slow` hoặc giảm tải retrieval. Nếu generation phình token, kiểm tra panel cost/tokens và cân nhắc rollback prompt `production` về label `baseline`.
- Owner: `oncall-llmops`

<a id="alert-2"></a>

## Alert 2 — users_receiving_errors

- Tên: `users_receiving_errors`
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack `#day13-k4-l3a-alerts`
- SLI/SLO liên quan: guardrail `error_rate_pct_max` = 2. Request lỗi không tạo `response_sent` nên cũng đốt error budget của SLO 99.5%.
- Điều kiện và thời gian duy trì: `count(request_failed) / count(request_received) * 100` lớn hơn 2% liên tục 5 phút.
- Ảnh hưởng tới người dùng: một phần request trả lỗi 500, người dùng không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Errors: error rate, breakdown `error_type`, và retrieval success.
  2. Lọc event `request_failed`, nhóm theo `error_type` và `tool_name`, lấy `correlation_id` của một dòng lỗi.
  3. Mở trace cùng ID. Nếu span `retrieve-context` lỗi (ví dụ vector store timeout), retrieval là span gây ảnh hưởng.
- Mitigation tạm thời: tắt incident `tool_fail` nếu đang bật để người dùng nhận câu trả lời trở lại. Giữ cảnh báo cho đến khi error rate về dưới 2% đủ 5 phút.
- Owner: `oncall-llmops`

<a id="alert-3"></a>

## Alert 3 — weak_answers

- Tên: `weak_answers`
- Severity: warning
- Duration: 10m
- Kênh thông báo: Slack `#day13-k4-l3a-alerts`
- SLI/SLO liên quan: guardrail `quality_score_avg_min` = 0.75 và `retrieval_success_rate_pct_min` = 90.
- Điều kiện và thời gian duy trì: trung bình `quality_score` dưới 0.75, hoặc tỉ lệ `tool_success == true` dưới 90%, liên tục 10 phút.
- Ảnh hưởng tới người dùng: câu trả lời vẫn trả về nhưng thiếu ngữ cảnh hoặc chất lượng thấp, người dùng không dùng được nội dung.
- Ba bước kiểm tra đầu tiên:
  1. So panel Quality với panel Errors (retrieval success) trong cùng cửa sổ 60 phút.
  2. Lọc `response_sent` có `quality_score < 0.75` hoặc `tool_success == false`, lấy `correlation_id`.
  3. Trên trace, xem `prompt_name`, `prompt_version`, `prompt_label` và output của `retrieve-context` (doc_count).
- Mitigation tạm thời: nếu chất lượng tụt ngay sau khi promote prompt, rollback label `production` về version `baseline`. Nếu retrieval success tụt, xử lý nguồn tài liệu trước khi đổi prompt.
- Owner: `oncall-llmops`
