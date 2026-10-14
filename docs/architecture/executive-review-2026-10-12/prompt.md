# Prompt — HappyNest executive architecture review

Mode: built-in `image_gen.imagegen` · Use case: `infographic-diagram`

```text
Use case: infographic-diagram
Asset type: high-resolution, single-page executive architecture review for this actual software project, in Vietnamese.
Primary request: Create ONE polished, informative landscape infographic titled "HappyNest" and "EXECUTIVE ARCHITECTURE REVIEW". Show how this AI feedback system converts bilingual user feedback into evidence-backed human decisions, and provide a balanced executive assessment of readiness.

Canvas: landscape 3:2, ideally 3000 x 2000 or higher equivalent. Flat front-facing infographic, crisp typesetting, no perspective, no photo mockup.
Visual language: restrained editorial information design matching the project's existing "Evidence Loom" visual identity. Field-paper background #f1f3e9, pine-ink #14251d type and framing, chalk #fcfcf8 cards, lichen #91a873 capability accents, signal-blue #3f738b evidence/data arrows, pollen #dbac3b human approval and review-priority badges. Thin rules, consistent minimal line icons, generous gutters, strong typography hierarchy. No decorative robots, neon, 3D, fake charts, fake screenshots, logos of vendors, watermarks, or invented KPIs.
Audience: product leaders, thesis reviewers and technical executives. Easy to scan in 30 seconds; readable Vietnamese with correct diacritics. Use only the exact text below. Wrap naturally; keep supporting copy large enough to read. Never replace Vietnamese with gibberish.

LAYOUT AND EXACT COPY:

1. HEADER (about 12% of height)
Small top line: "HappyNest"
Main title: "EXECUTIVE ARCHITECTURE REVIEW"
Large Vietnamese subtitle: "Từ phản hồi người dùng đến quyết định có bằng chứng"
Compact metadata at upper right: "12/10/2026 · Tổng quan mã nguồn"

2. EXPERIENCE / ORCHESTRATION STRIP (about 10% of height)
Two horizontally connected modules with a bidirectional connector:
Module A heading: "TRẢI NGHIỆM"
Module A copy: "Next.js 16 · React 19 · shadcn/ui"
Module A second line: "Người dùng · Dashboard · Activity Center"
Module B heading: "ĐIỀU PHỐI"
Module B copy: "FastAPI · Python 3.12"
Module B second line: "API · jobs trong tiến trình · LangGraph"
A clear downward arrow from this strip to the business pipeline below.

3. CENTRAL BUSINESS PIPELINE (about 34% of height)
Four well-proportioned cards flowing left-to-right with clear arrowheads. Card 2 may be slightly wider for its extra content. Distinct but subtle numbered stage markers. Human approval badges are pollen-yellow, labeled G1, G2 and G3 exactly once at their correct stages. The badges belong inside the relevant card, not at ambiguous stage boundaries.

Card 1 heading: "01  LISTEN"
Vietnamese subheading: "Thu thập & chuẩn hóa"
Body lines, in order:
"CSV / nhập tay → hồ sơ an toàn"
"G1 · Duyệt mapping"
"Ẩn PII → phân loại theo taxonomy"
"Phản hồi tiếng Việt – tiếng Anh"

Card 2 heading: "02  UNDERSTAND"
Vietnamese subheading: "Phát hiện & điều tra"
Body lines:
"Embedding 1536d → HDBSCAN"
"Trend / spike / emerging"
"LangGraph: plan → tool → evaluate"
"Insight gắn với evidence"
"G2 · Duyệt / sửa / điều tra thêm"
This is a visible agent investigation loop. Use a small looping arrow from evaluate back to plan, without adding any extra text.

Card 3 heading: "03  ACT"
Vietnamese subheading: "Ưu tiên hành động"
Body lines:
"Evidence + best practices"
"Điểm ưu tiên tính bằng công thức"
"G3 · Duyệt hành động"

Card 4 heading: "04  IMPACT"
Vietnamese subheading: "Theo dõi tác động"
Body lines:
"Đếm phản hồi trước / sau"
"Impact check qua CLI"
"Tín hiệu quan sát, chưa kết luận nhân quả"

Below these cards, a subtle DASHED feedback arrow points back from IMPACT toward LISTEN, labeled "Phản hồi mới → đánh giá lại". This is a conceptual feedback loop, not a claim of autonomous execution.

4. SHARED PLATFORM (about 15% of height)
Three side-by-side support modules in a common rail, with subtle connectors from the business pipeline:
"DỮ LIỆU"
"Supabase PostgreSQL 17 + pgvector"
"Feedback · evidence · insight · action · checkpoint"

"AI THEO TÁC VỤ"
"OpenAI-compatible API"
"Model routing · taxonomy do người duyệt"

"TRUY VẾT & QUYẾT ĐỊNH"
"Langfuse + llm_call_logs"
"decision_logs · lưu dấu quyết định"

5. GOVERNANCE AND DEPLOYMENT BAND (about 10% of height)
Shield icon and exact title: "KIỂM SOÁT XUYÊN SUỐT"
Two compact lines:
"Chỉ text đã ẩn PII vào AI / log / trace · JWT cookie httpOnly · workspace dùng chung"
"Giới hạn vòng điều tra & ngân sách LLM · checkpoint để tiếp tục duyệt"
Below, exact deployment note:
"Dev: Windows native · Đích deploy: Ubuntu VPS + systemd · Không Docker"

6. EXECUTIVE REVIEW (remaining space at bottom)
An authoritative but balanced assessment banner:
"NHẬN ĐỊNH: PHÙ HỢP MVP · CẦN GIA CỐ TRƯỚC PRODUCTION"
Three compact numbered priority blocks:
"01 · KIỂM CHỨNG"
"Chạy lại backend & kiểm thử phạm vi dữ liệu"

"02 · ĐỘ BỀN"
"Hoàn thiện job nền & triển khai VPS"

"03 · CHẤT LƯỢNG"
"Cast field TEXT · đánh giá trên dữ liệu VI–EN"

Small footer:
"Nguồn: mã nguồn + docs/architecture + decisions · Đánh giá tĩnh, chưa xác nhận production"

Accuracy constraints: this is an existing implementation overview, not a futuristic target architecture. FastAPI jobs and agent threads currently run in the application process, not a durable queue. Deployment script is still a placeholder. PostgreSQL graph checkpoints persist human-review state. Impact is descriptive before/after feedback volume, not causal proof. Do not invent accuracy, scale benchmarks, savings, completion percentages or production-readiness claims. Three human gates are mapping review, insight review and action review. Do not depict automatic execution of proposed actions. Do not introduce Kafka, Redis, Celery, Kubernetes, Docker, microservices, a fine-tuning engine, or an autonomous online-learning loop. Render this as ONE unified complete infographic, not multiple images.
```
