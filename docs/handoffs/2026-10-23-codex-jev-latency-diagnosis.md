# Handoff: Explain JEV latency using existing timing metadata
- Date: 2026-10-23 local (Asia/Saigon)
- From: codex
- To: any
- Branch / worktree: codex/activity-center (existing checkout)
- Milestone: Owner question about JEV speed and advertised 50 ms
- Status: done

## Done
- Owned read-only latency diagnosis; inspected JEV client, sequential runner, embedder, tracing, and progress polling.
- Verified runtime settings use `ENRICH_ENGINE=jev`, `JEV_MODEL=jev-latest`, endpoint `openrouter.ai/api/v1/systemone`; no keys printed.
- Read timing metadata only from Supabase; no feedback content read and no paid inference requests made.
- Checked official TypeSafe launch article: published 70–500 ms end-to-end and evaluations generally from West Coast laptops near their service; no universal 50 ms promise established.

## Evidence
- Last 200 llm_call_logs rows: 71 native JEV enrich calls, p50 924 ms, p95 1625.5 ms, max 2358 ms, 0 error rows. Sample spans multiple days and call types.
- Completed v4 run (30 items, October 23): wall 217.84 s, 30 linked enrich calls totaling 34.04 s.
- Same run window: 30 embedding calls totaling 40.84 s; embedding logs lack run attribution, so association is by timestamps, not FK.
- Residual 142.96 s includes DB/logging/client setup/orchestration and other unmeasured work; not individually profiled.
- Other recent runs: 5 items / 42.64 s (JEV 5.67 s; embeddings in window 6.42 s); 32 items / 249.65 s (JEV 29.88 s; embeddings in window 41.79 s).
- Fresh SELECT 1 over an already-open DB connection: 235, 232, 233 ms.
- Runner does refresh + pick-next + enrich + embed + commit sequentially per item. Enrich and embed each also commit their own log session.
- JEV httpx client and embedding OpenAI client are created anew per call; no cross-item connection reuse at those layers.
- Progress polling 4 s; understand/insight/taxonomy use other models, not native JEV.

## Not done / gaps
- No code/settings changes, test runs, new provider calls, direct-vs-gateway benchmark, or per-stage instrumentation.
- Existing latency logs include transport/client setup; cannot split model inference, network, gateway, queue, or internal retries from them.
- Do not attribute all residual time to DB or Langfuse; trace export need not be synchronous network I/O.

## Blocked / risks
- None for the explanation. Read-only DB inspection required approved execution outside sandbox.

## Next steps
1. If optimization requested: profile DB round trips and log writes, reuse HTTP clients, then consider bounded concurrency with per-item commits and isolation preserved.
2. Benchmark direct TypeSafe route against current OpenRouter path only with suitable credentials and authorized paid calls.
3. Official reference: https://typesafe.ai/blog/introducing-system-one-models-and-jev
