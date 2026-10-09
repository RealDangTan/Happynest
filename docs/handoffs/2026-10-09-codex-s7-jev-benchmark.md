# Handoff: Plan 33 executed — Jev System One FAIL on frozen smoke benchmark
- Date: 2026-10-09 Asia/Saigon
- From: codex
- To: any
- Branch / worktree: codex/activity-center / primary checkout
- Milestone: Plan 33 S7 (closed; source retained in Git history)
- Status: done

## Done
- Verified original script stops for missing TypeSafe key; discovered official OpenRouter compatible System One API and successfully used existing OpenRouter key.
- Ran 16 synthetic records through real Jev System One and 16 through Qwen baseline using v3 production prompt/schema, max output 8192, fixed primary threshold .6.
- Preserved earlier 800-token chat-router pilot separately; excluded it from primary model conclusions.
- Published docs/s7-jev-evaluation.md and docs/evidence/s7-jev-2026-10-09.json; raw synthetic results remain gitignored.
- Closed plan 33 with FAIL, removed completed plan file per owner's cleanup request, updated board/summary and legacy runner warning. Production model/env/database unchanged.

## Evidence
- Primary command from backend: uv run --no-sync python ../scripts/spikes/s7_openrouter.py --engine systemone --name s7_systemone_openrouter
- Primary exit 1 = benchmark FAIL, not runner crash; all 32 predictions valid, 0 observed 429.
- Jev returned typesafe/jev-1.13-20260917: p95 1.0607 s, cost $0.0007392/16, extrapolated $0.00462/100.
- FAIL: accuracy differences >5 points; intent calibration gap .30875. Budget gate UNKNOWN, no USD cap supplied.
- 6 regression tests passed after observed red → green; fresh final verification recorded in commit session.
- Ruff unavailable in existing environment; no dependency added. No app changes require broad FE/backend suites.

## Not done / gaps
- api.typesafe.ai host not tested (no key); equivalent System One transport via OpenRouter tested.
- No real feedback, held-out quality set, multi-label calibration, batch throughput or rate-limit load test.
- Synthetic fixture has disputed labels; do not cite these accuracies as general quality evidence.
- No deployment or push. Preserve unrelated thesis/taste/log/scratch changes.

## Next steps
1. Review labels and align rubrics, then collect an independent labeled VI/EN evaluation set before stronger quality claims.
2. If rerunning, set an agreed --budget100-usd before the run; do not tune on this test set.
