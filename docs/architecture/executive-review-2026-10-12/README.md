# HappyNest — Executive architecture review

Ngày rà soát: 12/10/2026, Asia/Saigon. Đối tượng: người quản lý sản phẩm và hội đồng khóa luận.

- [Sơ đồ kiến trúc hiện hành](../README.md)
- [Prompt tham chiếu](prompt.md)
- Tham chiếu triển khai: các sơ đồ Mermaid hiện hành trong thư mục kiến trúc.

## Nhận định executive

Kiến trúc phù hợp cho MVP VoC có người kiểm soát: thu thập và chuẩn hóa phản hồi VI–EN, phát hiện vấn đề, tổng hợp insight có evidence, đề xuất hành động rồi theo dõi phản hồi trước/sau. Ba cổng duyệt kiểm soát mapping, insight và hành động. Checkpoint PostgreSQL hỗ trợ tiếp tục graph tại bước duyệt; decision logs và truy vết kép giúp xem lại các quyết định.

Trước production, ưu tiên xác minh lại backend và phạm vi dữ liệu theo sản phẩm, tăng độ bền công việc nền và hoàn thiện deploy. Các field sản phẩm lưu TEXT cần được cast khi phân tích. Chất lượng NLP cần đánh giá trên dữ liệu VI–EN đại diện hơn. Đây là nhận định từ rà soát tĩnh, không phải chứng nhận production hay kết quả chạy lại test suite.

## Đối chiếu với mã nguồn

| Nội dung | Nguồn và giới hạn |
|---|---|
| Frontend Next.js 16, React 19, shadcn; proxy API | `frontend/package.json`, `frontend/next.config.ts`, các trang trong `frontend/app/(app)/` |
| FastAPI, Python 3.12, các API nghiệp vụ | `backend/app/main.py`, `backend/.python-version`, `backend/app/api/routes/` |
| CSV, hồ sơ an toàn, mapping G1, sanitize | `backend/app/services/import_service.py`, `llm_mapper.py`, `ingest_service.py`, `presidio_service.py`; file CSV thô còn trên disk, không gửi vào imagegen |
| Phân loại closed-set, taxonomy người duyệt | `backend/app/services/enricher.py`, `taxonomy_service.py`, `backend/app/jobs/analysis_runner.py` |
| Embedding 1536d, HDBSCAN, trend/spike/emerging | `backend/app/services/embedder.py`, `clustering.py`, `backend/app/core/config.py` |
| Agent điều tra và G2 | `backend/understand_agent/graph.py`, `nodes.py`; planner → dispatch → evaluator → planner; synthesizer → persist_insight → interrupt → apply_decision |
| Toolbox | `backend/app/analytics/tools.py`: schema/profile, aggregate, compare, segment, semantic search, representative feedback, cluster, similar cases |
| Giới hạn và checkpoint | `backend/app/core/config.py` có cấu hình 8 vòng / ngân sách 18 call cho UNDERSTAND; `graph_runtime.py` và `understand_agent/runner.py` dùng PostgreSQL checkpoint. Infographic không khẳng định đã đo tính nghiêm ngặt của cap |
| ACT và G3 | `backend/app/services/act_agent.py`, `act_grounding.py`, `act_practices.py`, `backend/app/api/routes/actions.py`; backend tính điểm ưu tiên, người duyệt hành động; không tự thực thi hành động ngoài hệ thống |
| IMPACT | `backend/app/services/impact_service.py`, `backend/scripts/run_impact_checks.py`: đếm feedback theo cửa sổ trước/sau mốc tạo action, chạy qua CLI; không chứng minh quan hệ nhân quả hoặc ghi nhận ngày thực thi thực tế |
| Xác thực và workspace dùng chung | `backend/app/api/deps.py`, `backend/app/schemas/auth.py`; cookie/Bearer xác thực danh tính, mọi tài khoản dùng chung products và thao tác |
| Truy vết | `backend/app/services/tracing.py`, `llm_client.py`, `decision_log.py`: Langfuse, metadata `llm_call_logs`, lịch sử `decision_logs` |
| Jobs và deploy | `backend/app/api/routes/analysis.py` dùng BackgroundTasks; `understand_agent/runner.py` dùng daemon thread; `infra/setup_vps.sh` còn placeholder; `infra/systemd/` chỉ có `.gitkeep` |

## Trạng thái bằng chứng

- Snapshot: branch `codex/activity-center`, HEAD `40f51b4`; có nhiều thay đổi chưa commit. Infographic phản ánh working tree tại thời điểm đọc, không chỉ HEAD.
- `docs/plans/00-index.md`: không còn plan đang mở; điều này không đồng nghĩa production đã sẵn sàng.
- `docs/decisions.md` ngày 11/10 ghi nhận phiên xác minh backend trước bị MemoryError / native crash; phiên này không chạy lại suite và không xác nhận các test count lịch sử.
- `docs/decisions.md` ngày 12/10 chốt field sản phẩm All-TEXT; cột core `occurred_at` vẫn là DateTime.
- `docs/s7-jev-evaluation.md`: S7 System One FAIL trên 16 mẫu synthetic; không dùng để suy rộng chất lượng model production. Jev Router và Jev System One là hai đường khác nhau; infographic chủ ý thể hiện routing theo tác vụ thay vì gắn kết quả S7 vào production.
- Một số tài liệu kiến trúc/README mô tả deploy ở mức mục tiêu. Script và unit hiện có xác nhận deploy chưa hoàn tất, nên infographic ghi rõ là đích deploy.

Không đọc `.env`, không gọi model phân tích feedback, không dùng feedback thực hoặc PII làm dữ liệu đầu vào tạo ảnh. Chỉ gửi mô tả kiến trúc tổng hợp và các nhãn kỹ thuật công khai trong repo vào imagegen.
