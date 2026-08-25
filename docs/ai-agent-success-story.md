Giả sử công ty tôi đã có một **VoC Agent** hỗ trợ xuyên suốt quy trình **Listen → Understand → Act**, thì công việc của tôi sẽ thay đổi khá rõ. Tôi vẫn là người chịu trách nhiệm cuối cùng, nhưng thay vì dành phần lớn thời gian để gom, đọc và tổng hợp feedback, tôi chuyển sang **review insight, ra quyết định và phối hợp action**.

Tôi sẽ hình dung Agent có 7 chức năng chính:

1. **Collect & Normalize Agent** — tự gom feedback từ survey, ticket, email, app review, social, CSV… rồi chuẩn hóa về một schema chung.
2. **Classification Agent** — tự gán topic, sub-topic, sentiment, severity, product area, customer segment.
3. **Dedup & Cluster Agent** — phát hiện feedback trùng hoặc gần giống nhau và gom thành issue cluster.
4. **Trend/Anomaly Agent** — phát hiện vấn đề nào đang tăng bất thường so với baseline.
5. **Insight Agent** — tổng hợp cluster thành một insight có evidence, pattern, affected users và representative feedback.
6. **Prioritization Agent** — đề xuất mức ưu tiên dựa trên volume, severity, trend, customer impact, business impact.
7. **Action Agent** — đề xuất owner, next action, tạo draft Jira/Slack/report; các action quan trọng cần tôi approve trước khi gửi.

Giờ tôi nhập vai để bạn thấy impact rõ hơn.

---

## 8:30 sáng — trước đây tôi mở 5 nơi để gom feedback

Tôi vào Zendesk, Google Sheet, survey dashboard, app review và Slack của customer support.

Mỗi nơi có một kiểu dữ liệu khác nhau.

Tôi copy-paste khoảng 200 feedback vào spreadsheet, mất gần một tiếng.

Nhưng khi có Agent, tôi mở dashboard và thấy:

> **1,284 new feedback collected since yesterday.**
> 1,151 successfully normalized.
> 93 duplicates detected.
> 40 require manual review.

Tôi không cần biết feedback đến từ Zendesk hay survey để bắt đầu phân tích nữa.

Agent đã map chúng về cùng dạng:

`source → timestamp → customer → product area → raw feedback → metadata`

### Impact

Trước đây:

**~60 phút/ngày chỉ để gom và làm sạch dữ liệu.**

Bây giờ:

**5–10 phút để kiểm tra lỗi ingestion.**

Tôi đã lấy lại gần một giờ làm việc ngay từ đầu ngày.

---

## 9:00 — Agent nói với tôi: “Có một cluster cần chú ý”

Dashboard xuất hiện:

> **Emerging issue detected**
>
> Web Search hallucination
> 46 feedback / 31 users
> +238% vs 7-day baseline
> Severity prediction: High
> Confidence: 0.91

Tôi click vào.

Agent không chỉ nói “46 feedback negative”.

Nó cho tôi thấy:

**Pattern**

* 38/46 feedback xuất hiện sau release `v2.17`.
* 34 feedback có liên quan tới Web Search.
* 26 user trước đó có CSAT ≥ 4 nhưng lần này cho CSAT ≤ 2.

**Representative feedback**

> “The source doesn't exist but the AI presents it like a fact.”

> “Search results look convincing but are completely fabricated.”

Agent đề xuất:

> Possible hypothesis: retrieval/source-validation regression after v2.17.

Điểm quan trọng là Agent gọi đây là **hypothesis**, không khẳng định đó là root cause.

Tôi click:

**Review evidence.**

Sau khi đọc khoảng 8 feedback mẫu, tôi thấy pattern hợp lý.

Tôi chọn:

**Approve insight.**

---

## Impact ở bước Understand

Trước đây tôi có thể phải đọc 100–200 feedback mới nhận ra:

> “Ơ hình như mấy người này đều đang nói về Web Search.”

Và thậm chí có thể đến cuối tuần tôi mới nhận ra trend.

Agent phát hiện nó ngay sau khi signal vượt baseline.

Thay vì:

**Human đọc feedback → nhớ → tự nhận pattern → lọc lại → đếm → viết summary**

workflow thành:

**Agent detect → Agent cluster → Agent summarize → Human verify.**

Tôi không bỏ qua con người.

Tôi chỉ chuyển con người từ:

> **information processor**

sang:

> **decision maker.**

---

## 9:20 — Agent đề xuất priority

Agent đưa ra:

> Suggested Priority: **P1**
>
> Reason:
>
> High severity
> Rapid growth
> Trust-related issue
> Affects core AI experience
> Seen across 31 unique users

Nhưng nó cũng nói:

> Similar cluster last month was rated P2 by Product team.

Đây là thứ rất hữu ích.

Agent không chỉ dùng một công thức cứng.

Nó biết cách tổ chức từng xử lý issue tương tự trước đây.

Tôi nghĩ issue lần này nghiêm trọng hơn vì trend tăng rất nhanh.

Tôi override:

**P1 confirmed.**

Agent ghi lại:

> Human decision: P1
> Reviewer: VoC Analyst
> Reason: rapid post-release escalation.

Lần sau model có thêm một precedent để tham khảo.

---

## 9:30 — Agent chuẩn bị action

Thay vì tôi mở Jira và viết ticket từ đầu, Agent tạo draft:

**Title**

`[P1] Web Search hallucination spike after v2.17`

**Summary**

Hallucination-related feedback increased 238% relative to the 7-day baseline following v2.17.

**Evidence**

46 feedback
31 unique users
34 related to Web Search
26 significant CSAT drops

**Possible hypothesis**

Regression in retrieval/source validation.

**Suggested owner**

AI Search Team

**Recommended next step**

Investigate retrieval logs around v2.17 and compare cited-source validation before/after release.

Nó hỏi tôi:

> Create Jira issue?

Tôi đọc lại.

Tôi sửa một câu.

**Approve.**

Ticket được tạo.

Agent đồng thời chuẩn bị Slack message:

> P1 VoC signal detected after v2.17...

Tôi approve tiếp.

---

## Đây mới là impact lớn

Trước đây từ lúc feedback xuất hiện đến khi engineering nhận được một issue đủ rõ có thể là:

**2–5 ngày.**

Vì phải qua:

feedback → support → report → product meeting → PM → engineering.

Với Agent:

feedback → detection → human review → engineering

có thể rút xuống còn:

**vài chục phút đến vài giờ.**

Đó là impact lớn hơn rất nhiều so với kiểu:

> “AI giúp tôi summarize nhanh hơn.”

Giá trị thật nằm ở việc **giảm time-to-insight và time-to-action**.

---

## Nhưng Agent cũng có lúc sai

Khoảng 11 giờ, tôi thấy:

> 🔴 Emerging issue
> “Login broken”
> 73 feedback
> Suggested severity: Critical.

Nghe rất nghiêm trọng.

Tôi mở cluster.

Hóa ra phần lớn feedback là:

> “I can't login with Google.”

Nhưng tất cả đến từ cùng một enterprise customer vừa tắt Google OAuth trong tenant của họ.

Đây không phải product-wide outage.

Tôi chọn:

**Reject escalation.**

Reason:

> Customer-specific configuration issue.

Agent chuyển cluster thành:

**Account-specific issue**

và gửi sang Customer Success thay vì Engineering.

Đây chính là lý do tôi không muốn Agent hoàn toàn autonomous.

Nếu Agent tự tạo P0 ticket và ping engineering mỗi lần thấy spike thì vài tuần sau không ai còn tin nó.

---

# Human-in-the-Loop lúc này có ý nghĩa thật sự

Không phải kiểu:

> “AI làm xong rồi người kiểm tra cho có.”

Mà tôi đặt Human Gate ở đúng các điểm có hậu quả lớn:

**Agent được tự động**

Collect
Normalize
Classify
Cluster
Summarize
Detect trend

**Agent phải xin approval**

Escalate P0/P1
Assign owner
Create external ticket
Recommend product decision
Close issue

Tức là:

**Low risk → automation.**

**High consequence → human judgment.**

---

## 4 giờ chiều — Agent quay lại action cũ

Ba ngày trước team engineering đã fix một issue khác.

Agent nói:

> **Impact check**
>
> Issue: slow response after document upload
>
> Before fix: 18.3 complaints/day
> After fix: 5.1 complaints/day
> ↓72%
>
> CSAT affected segment:
> 2.8 → 3.9
>
> Suggested status:
> **Likely improved — continue monitoring.**

Đây là một điểm VoC truyền thống rất hay thiếu.

Rất nhiều team làm:

**Listen → Understand → Act**

nhưng quên mất:

**Did the action actually work?**

Agent đóng loop đó lại:

**Listen → Understand → Act → Measure → Learn → Listen.**

---

# Một ngày làm việc của tôi thay đổi như thế nào?

Trước Agent, ngày của tôi có thể là:

| Công việc         | Thời gian |
| ----------------- | --------: |
| Gom dữ liệu       |        1h |
| Clean/duplicate   |        1h |
| Tag feedback      |        2h |
| Đọc & tìm pattern |        2h |
| Viết report       |        1h |
| Trao đổi/action   |        1h |

Tức là khoảng **70–80% công việc là xử lý thông tin**.

Với Agent giả định:

| Công việc          |    Thời gian |
| ------------------ | -----------: |
| Review ingestion   |          10m |
| Review clusters    |          30m |
| Validate insights  |          45m |
| Prioritization     |          30m |
| Coordinate actions |         1–2h |
| Deep investigation | phần còn lại |

Tôi chuyển phần lớn thời gian sang:

**Why is this happening?**

**Is this evidence trustworthy?**

**Should we act?**

**Who should act?**

**Did the action work?**

Đây mới là phần có giá trị cao.

---

## Nếu phải diễn đạt impact của hệ thống này trong khóa luận

Đừng nói đơn giản:

> “AI Agent giúp tự động phân loại feedback.”

Nó hơi yếu.

Tôi sẽ frame nó thành:

> **VoC Agent giảm khoảng cách từ Customer Voice đến Product Action.**

Tức là hệ thống tác động vào ba latency:

**Time-to-Listen**

Feedback xuất hiện → feedback được đưa vào hệ thống.

**Time-to-Insight**

Feedback → team hiểu được vấn đề đang xảy ra.

**Time-to-Action**

Insight → người có trách nhiệm bắt đầu xử lý.

Và đồng thời vẫn giữ:

**Traceability**

Insight nào cũng truy được về feedback gốc.

**Human control**

Action quan trọng đều có người duyệt.

**Closed-loop learning**

Sau khi action xảy ra, hệ thống quay lại đo xem customer voice đã thay đổi chưa.

Nếu làm thesis, tôi thậm chí sẽ lấy **3 chỉ số này làm KPI chính** thay vì cố chứng minh Agent “thông minh hơn con người”: **giảm thời gian xử lý feedback, giảm time-to-insight, tăng tỷ lệ insight được chuyển thành action**. Đây là impact dễ demo, dễ đo và khá sát với bài toán VoC thực tế.
