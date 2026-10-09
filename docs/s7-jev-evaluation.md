# S7 — Jev System One vs enricher v3 (2026-10-09)

Plan 33 đã thực thi và đóng với **FAIL**, không mở tích hợp 34B. Không đổi app code, database hay `.env`. Kết quả này đánh giá một bộ smoke synthetic nhỏ, không chứng minh model nào tốt hơn trên dữ liệu thực.

## Cách chạy và phạm vi

Script gốc dừng trước API vì thiếu `JEV_API_KEY`. Sau khi kiểm tra [tài liệu OpenRouter System One](https://openrouter.ai/docs/guides/community/typesafe-sdk), đã gọi được **Jev thật** qua `POST https://openrouter.ai/api/v1/systemone` bằng key OpenRouter hiện có. Model trả về là `typesafe/jev-1.13-20260917`, provider TypeSafe. Host `api.typesafe.ai` chưa được đo; đây là thay đổi transport được ghi trong [decisions](decisions.md), giữ nguyên primitive Noul/Choice/Score của S7.

Jev System One khác `typesafe/jev-router`: router chọn model sinh văn bản phía sau, không phải chính bộ phân loại System One. [Mô tả chính thức của router](https://openrouter.ai/typesafe/jev-router).

- 16 feedback VI/EN synthetic từ fixture S7 v1; giữ nguyên ground truth, không đọc feedback thực hoặc DB.
- Jev: bộ câu hỏi gốc `jev_questions_for`, một request mang sentiment/intent Choice, severity Score, topic/emotion Noul. Severity dùng score làm tròn về 0–3 như thiết kế gốc.
- Baseline: `qwen/qwen3-30b-a3b-instruct-2507`, cùng taxonomy, prompt và schema production enricher v3, temperature 0, giới hạn output theo cấu hình ứng dụng: 8192 token. Dùng HTTP riêng nên không gồm thời gian ghi log DB/tracing của app.
- Ngưỡng chính **0.6 chốt trước gọi API**. Sweep 0.5/0.6/0.7 chỉ chẩn đoán; không chọn ngưỡng thắng trên test set. Biến thể nghiên cứu lọc cả topic/emotion theo ngưỡng; production hiện chỉ lọc topic. Emotion không có nhãn còn lại thì `neutral`.
- Hai engine có định dạng prompt khác nhau theo API (câu hỏi S7 so với prompt v3); rubric severity S7 chỉ có tên mức, baseline có mô tả. Đây là so sánh hai cấu hình hiện hữu, chưa cô lập ảnh hưởng của model và prompt.
- Chạy tuần tự Jev rồi Qwen, 16 request/engine. Latency gồm retry và validation; p95 nearest-rank trên n=16 chính là mẫu chậm nhất. Không randomize thứ tự, không đo CI hoặc throughput batch.

## Kết quả chính tại ngưỡng 0.6

| Metric | Jev System One | Qwen baseline |
|---|---:|---:|
| Topic exact-set accuracy | 56.25% | 68.75% |
| Sentiment accuracy | 87.50% | 93.75% |
| Emotion exact-set accuracy | 6.25% | 31.25% |
| Intent accuracy | 56.25% | 75.00% |
| Severity accuracy | 81.25% | 75.00% |
| Topic micro-F1 / precision | 0.7647 / 0.7222 | 0.8571 / 0.7895 |
| Emotion micro-F1 / precision | 0.5882 / 0.4255 | 0.6087 / 0.5600 |
| p95 latency | 1.0607 s | 12.4816 s |
| Valid predictions | 16/16 | 16/16 |
| Observed 429 / unrecovered 429 | 0 / 0 | 0 / 0 |
| Billed cost, 16 records (`usage.cost`) | $0.0007392 | $0.00157465065 |
| Extrapolated cost, 100 records | $0.00462 | $0.00984157 |

Cost là ngoại suy 100 request một record theo lượt đo, **không phải** đo batch API hoặc 100 feedback trong một prompt. Tổng primary run: $0.00231385065, chưa gồm probe và pilot.

## Đối chiếu tiêu chí gốc đã chốt trước chạy

1. **FAIL** — accuracy từng split lệch ≤5 điểm % với baseline: topic −12.5, sentiment −6.25, emotion −25, intent −18.75, severity +6.25 điểm %. Theo wording gốc, chênh lệch tuyệt đối áp dụng cả khi Jev tốt hơn. n=16 khiến một mẫu tương ứng 6.25 điểm %.
2. **FAIL** — calibration gap ≤0.10: sentiment **0.068125**, intent **0.30875**, severity **0.08125**. Dùng xác suất của lựa chọn thực sự dự đoán (severity: bin score làm tròn), so với accuracy; không dùng vendor confidence hay confidence tự đánh giá toàn bộ của v3. Đây là gap trung bình theo ba choice/score split, không phải ECE/reliability curve, và chưa đo calibration cho từng topic/emotion binary.
3. **PASS quan sát** — 0 unrecovered 429. Không gặp 429 nên lượt chạy không xác minh backoff dưới tải thật.
4. **PASS** — Jev p95 1.0607 s <2 s/request.
5. **UNKNOWN** — ghi được cost thật và ngoại suy, nhưng plan không định lượng ngân sách USD. Không tự chọn ngân sách để cho PASS.

Verdict **FAIL** đã xác định từ tiêu chí 1 và 2; criterion 5 chưa xác định không thể biến verdict thành PASS. Không đổi threshold, nhãn hay model production để cải thiện kết quả sau đo.

## Pilot và giới hạn dữ liệu

Trước khi tìm thấy endpoint System One, đã chạy pilot `typesafe/jev-router` với Qwen, 16 mẫu/engine, cap 800 output token. Router có 3/16 lỗi structure sau retry, p95 9.5066 s, cost $0.023042778/16 record. Baseline pilot cost $0.0017025896; probe System One một mẫu cost $0.000046242. Tổng các lượt của phiên này theo usage.cost: khoảng **$0.02710546**. Cap pilot khác production và có thể gây truncation; pilot không lưu finish_reason nên không kết luận nguyên nhân lỗi structure. **Không dùng pilot để kết luận chất lượng Jev System One hoặc chất lượng production router.**

Fixture v1 có nhãn cần review: record 1 praise thanh toán gán `payment.failure`; record 9 vấn đề privacy gán `ai.hallucination` vì thiếu taxonomy bảo mật; record 13 gán thêm `support.response` thiếu bằng chứng rõ; intent record 8/14 mơ hồ. Nhãn được giữ nguyên để không sửa ground truth sau khi xem kết quả. Cả hai engine có emotion exact-match thấp; cần adjudication, rubric nhãn thống nhất và tập VI/EN độc lập lớn hơn trước khi đưa kết luận chất lượng vào luận văn. Không lấy sweep trên tập này làm tuning rồi báo cáo cùng tập là held-out test.

## Bằng chứng và chạy lại

[Số liệu tổng hợp, hash fixture/prompt và sweep](evidence/s7-jev-2026-10-09.json) được commit, không chứa key hay feedback thực. Raw response synthetic/checkpoint để tại `scripts/spikes/results/s7_systemone_openrouter_result.json` và pilot `s7_openrouter_result.json` (gitignored).

```powershell
# từ backend/; dùng cấu hình OpenRouter hiện có, không sửa .env
uv run python ../scripts/spikes/s7_openrouter.py --engine systemone --name s7_systemone_openrouter
# tùy chọn --budget100-usd <mức owner chốt trước lần chạy>
uv run python -m unittest discover -s ../scripts/spikes -p test_s7_openrouter.py
```

Runner companion có 6 regression tests (đã quan sát red → green): nearest-rank p95, unknown budget không PASS, exact-set/F1/precision, threshold topic+emotion, parse Score/probability và calibration từng split. Script direct-host cũ được giữ làm lịch sử; có lỗi p95, emotion threshold cố định, chọn best threshold trên test set, calibration chỉ sentiment và bỏ cost gate, nên không dùng verdict của nó làm bằng chứng cho phiên này.
