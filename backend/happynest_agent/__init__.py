"""happynest_agent — toàn bộ code module agent của khóa luận.

Owner directive 2026-08-26: gom code agent vào MỘT package để dễ soát
(decisions.md 2026-08-26). Cấu trúc:
- tools/     : 5 tool deterministic + registry (phase 18)
- state.py   : AgentState TypedDict (phase 19)
- nodes.py   : assess/route/dispatch/synthesize/critic/persist/risk_gate (19)
- graph.py   : build_agent_graph (19)
- jobs/      : agent_runner background job (19)
- routes/    : /api/agent/* router (19)
"""
