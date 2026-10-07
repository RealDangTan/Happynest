"""SPIKE S7 — Jev (TypeSafe System One) vs LLM baseline trên feedback VI/EN.

⚠️ SPIKE-ONLY: script này KHÔNG đụng app code. Kết quả PASS/FAIL là GATE cho
việc bật `ENRICH_ENGINE=jev` (plans 32/34B — docs/plans/33-spike-s7-jev.md).

VENDOR FACTS (pinned firsthand từ https://docs.typesafe.ai/api, fetch
2026-10-07 — KHÔNG suy đoán):
- Endpoint:  POST https://api.typesafe.ai/v1/systemone
- Auth:      Authorization: Bearer <API_KEY>
- Body:      {"state": <str|obj>, "model": "jev-latest",
              "questions": {<id>: {"type": "noul"|"choice"|"score",
                                   "instructions": ..., "criteria": ...}}}
- Answer:    noul   -> {"type":"noul","noul": p}
             choice -> {"type":"choice","choice": key,"probabilities": {...},
                        "confidence": c}
             score  -> {"type":"score","score": w,"legend": {...},
                        "probabilities": {...},"confidence": c}
- 429/529    -> exponential backoff (vendor khuyến nghị); lỗi khác không retry.
- `questions` là MAP → MỘT request mang NHIỀU câu hỏi song song (per-emotion
  Noul chạy trong cùng 1 call, đúng thiết kế multi-label đã chốt).

PASS CRITERIA (chốt trước 2026-10-07, KHÔNG đổi khi chạy — docs/plans/33):
1. Per-split accuracy (topic/sentiment/intent/severity/emotion) lệch ≤ 5 điểm %
   so với LLM baseline trên CÙNG bộ ground truth.
2. Calibration gap ≤ 0.10 (|avg confidence − accuracy| mỗi split).
3. 0 unrecovered 429/529 (backoff max 3 lần).
4. p95 latency < 2s / request.
5. Cost ước tính ở quy mô batch (100 feedback) ghi rõ — giá đầu vào $0.042/1M
   token là UNVERIFIED (nguồn thứ ba jevmodel.org); spike chỉ đo token, owner
   nhân với giá hiện hành khi quyết.

Dataset: fixture VI/EN trộn teencode NHÂN TẠO, KHÔNG PII, gắn tay 1–2 emotion
label/record CỐ Ý có mixed-emotion case (nguyên tắc multi-label đã chốt ở review
S7). Topic từ tập đóng 6 nhãn giống shape Active Taxonomy.

Cách chạy (từ backend/, hoặc repo root với uv run --project backend):
    uv run python ../scripts/spikes/s7_jev_parity.py
Cần JEV_API_BASE + JEV_API_KEY (+ LLM_* cho baseline) trong backend/.env.
Không có key → thoát code 2 với thông báo rõ (spike READY, chưa chạy).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import getenv, load_env_file, save_result, utf8_stdio  # noqa: E402

# --- Cấu hình spike --------------------------------------------------------

JEV_MODEL = "jev-latest"
THRESHOLDS = (0.5, 0.6, 0.7)
BACKOFF_MAX = 3
P95_BUDGET_S = 2.0
INPUT_PRICE_PER_1M = 0.042  # UNVERIFIED — xem PASS criteria #5

TOPICS = [
    "payment.failure",
    "account.login",
    "search.result",
    "performance.speed",
    "ai.hallucination",
    "support.response",
]
EMOTIONS = [
    "frustration", "anger", "disappointment", "confusion",
    "anxiety", "satisfaction", "delight", "neutral",
]
INTENTS = ["bug_report", "feature_request", "question", "complaint", "praise", "other"]
SENTIMENTS = ["positive", "negative", "neutral", "mixed"]
SEVERITIES = ["low", "medium", "high", "critical"]

# (text VI/EN teencode nhân tạo, topics[1-2], sentiment, emotions[1-2 incl mixed],
#  intent, severity) — KHÔNG PII, nội dung được bịa cho spike.
RECORDS: list[dict] = [
    {"text": "Update xong app lam an toan qua, thanh toan nhanh rat vui", "topics": ["payment.failure"], "sentiment": "positive", "emotions": ["satisfaction"], "intent": "praise", "severity": "low"},
    {"text": "Tuần rồi chuyển khoản cứ quay mãi rồi báo lỗi, mất cả buổi", "topics": ["payment.failure"], "sentiment": "negative", "emotions": ["frustration"], "intent": "bug_report", "severity": "high"},
    {"text": "dang lm tu nhien bi log out, dang nhap lai ko dc nua", "topics": ["account.login"], "sentiment": "negative", "emotions": ["frustration", "anxiety"], "intent": "bug_report", "severity": "high"},
    {"text": "OTP gửi về sim cũ, đổi số ở đâu vậy mọi người", "topics": ["account.login"], "sentiment": "neutral", "emotions": ["confusion"], "intent": "question", "severity": "medium"},
    {"text": "Search ra kết quả toàn thứ ko liên quan, filter cũng lag", "topics": ["search.result", "performance.speed"], "sentiment": "negative", "emotions": ["frustration", "disappointment"], "intent": "complaint", "severity": "medium"},
    {"text": "Bot vừa bịa nguồn báo cáo, số liệu khác hẳn dashboard thật", "topics": ["ai.hallucination"], "sentiment": "negative", "emotions": ["anger", "disappointment"], "intent": "bug_report", "severity": "critical"},
    {"text": "App nặng máy ghê, mở lên quạt quay như máy bay", "topics": ["performance.speed"], "sentiment": "negative", "emotions": ["frustration"], "intent": "complaint", "severity": "medium"},
    {"text": "Gặp lỗi font chữ ở trang dashboard, nhỏ thôi", "topics": [], "sentiment": "neutral", "emotions": ["neutral"], "intent": "other", "severity": "low"},
    {"text": "Bảo mật vậy mà data khách bị lộ, luật sư cần biết", "topics": ["ai.hallucination"], "sentiment": "negative", "emotions": ["anger", "anxiety"], "intent": "complaint", "severity": "critical"},
    {"text": "Nên thêm xuất báo cáo Excel nữa thì hoàn hảo", "topics": [], "sentiment": "positive", "emotions": ["satisfaction"], "intent": "feature_request", "severity": "low"},
    {"text": "Support trả lời chậm quá, 3 ngày chưa thấy phản hồi", "topics": ["support.response"], "sentiment": "negative", "emotions": ["frustration", "disappointment"], "intent": "complaint", "severity": "medium"},
    {"text": "Mới update xong thấy search nhanh hẳn, detailed luôn", "topics": ["search.result"], "sentiment": "positive", "emotions": ["delight"], "intent": "praise", "severity": "low"},
    {"text": " Thanh toán fail mà ko biết lỗi do bank hay do app, bức xúc", "topics": ["payment.failure", "support.response"], "sentiment": "negative", "emotions": ["anger"], "intent": "bug_report", "severity": "high"},
    {"text": "Đổi mật khẩu xong bị kick khỏi mọi thiết bị, hơi bất tiện", "topics": ["account.login"], "sentiment": "neutral", "emotions": ["confusion"], "intent": "question", "severity": "low"},
    {"text": "The AI summary is making things up completely, dangerous", "topics": ["ai.hallucination"], "sentiment": "negative", "emotions": ["anger"], "intent": "bug_report", "severity": "critical"},
    {"text": "Loading dashboard mất 40 giây, ko dùng nổi", "topics": ["performance.speed"], "sentiment": "negative", "emotions": ["frustration"], "intent": "bug_report", "severity": "high"},
]

# --- Jev client ------------------------------------------------------------


def jev_call(client: httpx.Client, base: str, key: str, state: str, questions: dict) -> dict:
    """Một request /v1/systemone; backoff 429/529 tối đa BACKOFF_MAX lần.
    Trả JSON body; raise RuntimeError khi hết lượt retry."""
    delay = 1.0
    last_err = None
    for _ in range(BACKOFF_MAX + 1):
        resp = client.post(
            f"{base.rstrip('/')}/v1/systemone",
            headers={"Authorization": f"Bearer {key}"},
            json={"state": state, "model": JEV_MODEL, "questions": questions},
            timeout=30,
        )
        if resp.status_code in (429, 529):
            last_err = f"HTTP {resp.status_code}"
            time.sleep(delay)
            delay *= 2
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"unrecovered provider throttle sau {BACKOFF_MAX} retry: {last_err}")


def jev_questions_for(taxonomy_slugs: list[str]) -> dict:
    """Bộ câu hỏi cho 1 record — 1 request, N câu song song (spec §3)."""
    questions: dict = {
        "sentiment": {
            "type": "choice",
            "instructions": "Sentiment của feedback người dùng về sản phẩm (có thể trộn VI/EN, teencode).",
            "criteria": {s: None for s in SENTIMENTS},
        },
        "intent": {
            "type": "choice",
            "instructions": "Ý định chính của feedback.",
            "criteria": {
                "bug_report": "Báo lỗi/hỏng hóc",
                "feature_request": "Đề xuất tính năng mới",
                "question": "Hỏi cách dùng/thông tin",
                "complaint": "Khiếu nại trải nghiệm",
                "praise": "Khen",
                "other": "Khác",
            },
        },
        "severity": {
            "type": "score",
            "instructions": "Mức nghiêm trọng của vấn đề được mô tả.",
            "criteria": SEVERITIES,
        },
    }
    for slug in taxonomy_slugs:
        questions[f"topic::{slug}"] = {
            "type": "noul",
            "instructions": f"Feedback này có thuộc chủ đề '{slug}' không?",
            "criteria": {"true": "Nội dung nói đúng vấn đề này", "false": "Không liên quan"},
        }
    for emo in EMOTIONS:
        questions[f"emotion::{emo}"] = {
            "type": "noul",
            "instructions": f"Feedback có thể hiện cảm xúc '{emo}' không?",
            "criteria": {"true": "Có", "false": "Không"},
        }
    return questions


def jev_parse(answers: dict, taxonomy_slugs: list[str], threshold: float) -> dict:
    topics = [
        slug
        for slug in taxonomy_slugs
        if answers.get(f"topic::{slug}", {}).get("noul", 0.0) >= threshold
    ]
    emotions = [
        emo
        for emo in EMOTIONS
        if answers.get(f"emotion::{emo}", {}).get("noul", 0.0) >= 0.5
    ] or ["neutral"]
    sev_answer = answers.get("severity", {})
    sev_idx = int(round(float(sev_answer.get("score", 0))))
    sev_idx = max(0, min(len(SEVERITIES) - 1, sev_idx))
    return {
        "topics": topics,
        "sentiment": answers.get("sentiment", {}).get("choice"),
        "emotions": emotions,
        "intent": answers.get("intent", {}).get("choice"),
        "severity": SEVERITIES[sev_idx],
        "confidences": {
            "sentiment": answers.get("sentiment", {}).get("confidence"),
            "intent": answers.get("intent", {}).get("confidence"),
            "severity": sev_answer.get("confidence"),
        },
    }


# --- LLM baseline ----------------------------------------------------------


def llm_baseline(cfg: dict, records: list[dict]) -> list[dict]:
    from openai import OpenAI

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"], timeout=120, max_retries=1)
    system = (
        "Bạn là bộ phân loại feedback sản phẩm AI (VI/EN trộn). Trả CHỈ JSON: "
        '{"topics": [slug...], "sentiment": "positive|negative|neutral|mixed", '
        '"emotions": [frustration|anger|disappointment|confusion|anxiety|satisfaction|delight|neutral...], '
        '"intent": "bug_report|feature_request|question|complaint|praise|other", '
        '"severity": "low|medium|high|critical"}. '
        "topics chỉ chọn từ danh sách; không khớp thì mảng rỗng; emotions tối đa 3."
    )
    out = []
    for rec in records:
        resp = client.chat.completions.create(
            model=cfg["model"],
            temperature=0,
            max_tokens=300,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Topics khả dụng: {', '.join(TOPICS)}\nFeedback: {rec['text']}"},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        out.append(json.loads(content))
    return out


# --- Metrics ---------------------------------------------------------------


def _accuracy(pred: list, truth: list) -> float:
    assert len(pred) == len(truth)
    return sum(1 for p, t in zip(pred, truth) if p == t) / len(truth) if truth else 0.0


def _micro_f1_precision(pred_sets: list[set], truth_sets: list[set]) -> tuple[float, float]:
    tp = sum(len(p & t) for p, t in zip(pred_sets, truth_sets))
    fp = sum(len(p - t) for p, t in zip(pred_sets, truth_sets))
    fn = sum(len(t - p) for p, t in zip(pred_sets, truth_sets))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return f1, precision


def main() -> int:
    utf8_stdio()
    env = load_env_file()
    base = getenv(env, "JEV_API_BASE", default="https://api.typesafe.ai")
    key = getenv(env, "JEV_API_KEY")
    if not key:
        print("JEV_API_KEY chưa có trong backend/.env — spike READY nhưng CHƯA chạy.")
        print("Owner điền key rồi chạy lại: uv run python scripts/spikes/s7_jev_parity.py")
        return 2
    llm_cfg = {
        "base_url": getenv(env, "LLM_BASE_URL"),
        "api_key": getenv(env, "LLM_API_KEY"),
        "model": getenv(env, "LLM_MODEL"),
    }

    truth_topics = [set(r["topics"]) for r in RECORDS]
    truth_sent = [r["sentiment"] for r in RECORDS]
    truth_emo = [set(r["emotions"]) for r in RECORDS]
    truth_intent = [r["intent"] for r in RECORDS]
    truth_sev = [r["severity"] for r in RECORDS]

    # --- Jev pass ---
    latencies: list[float] = []
    jev_preds_by_threshold: dict[float, list[dict]] = {t: [] for t in THRESHOLDS}
    unrecovered = 0
    input_tokens_total = 0
    with httpx.Client() as client:
        for rec in RECORDS:
            questions = jev_questions_for(TOPICS)
            t0 = time.perf_counter()
            try:
                body = jev_call(client, base, key, rec["text"], questions)
            except RuntimeError:
                unrecovered += 1
                for t in THRESHOLDS:
                    jev_preds_by_threshold[t].append({"topics": [], "sentiment": None, "emotions": [], "intent": None, "severity": None, "confidences": {}})
                continue
            latencies.append(time.perf_counter() - t0)
            input_tokens_total += int(body.get("usage", {}).get("input_tokens", 0))
            for t in THRESHOLDS:
                jev_preds_by_threshold[t].append(jev_parse(body.get("answers", {}), TOPICS, t))

    # --- LLM baseline pass ---
    llm_preds = llm_baseline(llm_cfg, RECORDS)

    def evaluate(preds: list[dict]) -> dict:
        topic_sets = [set(p["topics"]) for p in preds]
        f1, prec = _micro_f1_precision(topic_sets, truth_topics)
        exact = _accuracy([sorted(p["topics"]) for p in preds], [sorted(t) for t in truth_topics])
        return {
            "topic_micro_f1": round(f1, 3),
            "topic_precision": round(prec, 3),
            "topic_exact_accuracy": round(exact, 3),
            "sentiment_accuracy": round(_accuracy([p["sentiment"] for p in preds], truth_sent), 3),
            "emotion_micro_f1": round(_micro_f1_precision([set(p["emotions"]) for p in preds], truth_emo)[0], 3),
            "intent_accuracy": round(_accuracy([p["intent"] for p in preds], truth_intent), 3),
            "severity_accuracy": round(_accuracy([p["severity"] for p in preds], truth_sev), 3),
        }

    llm_metrics = evaluate(llm_preds)
    jev_metrics_by_threshold = {t: evaluate(jev_preds_by_threshold[t]) for t in THRESHOLDS}

    # Calibration gap trên choice-answers (sentiment/intent) — trung bình 2 split
    cal_gaps = []
    for t in THRESHOLDS:
        preds = jev_preds_by_threshold[t]
        gap_sent = abs(
            _accuracy([p["sentiment"] for p in preds], truth_sent)
            - (sum(p["confidences"].get("sentiment") or 0 for p in preds) / len(preds))
        )
        cal_gaps.append(gap_sent)
    calibration_gap = round(sum(cal_gaps) / len(cal_gaps), 3)

    lat_sorted = sorted(latencies)
    p95 = lat_sorted[int(len(lat_sorted) * 0.95) - 1] if lat_sorted else None

    # --- Verdict theo PASS criteria ---
    best_t = max(THRESHOLDS, key=lambda t: jev_metrics_by_threshold[t]["topic_micro_f1"])
    best = jev_metrics_by_threshold[best_t]
    checks = {
        "1_accuracy_within_5pts": all(
            abs(best[k] - llm_metrics[k]) <= 0.05
            for k in llm_metrics
            if not k.startswith("topic_")
        )
        and abs(best["topic_micro_f1"] - llm_metrics["topic_micro_f1"]) <= 0.05,
        "2_calibration_gap_le_0.10": calibration_gap <= 0.10,
        "3_zero_unrecovered_429": unrecovered == 0,
        "4_p95_latency_lt_2s": p95 is not None and p95 < P95_BUDGET_S,
    }
    verdict = "PASS" if all(checks.values()) else "FAIL"

    result = {
        "verdict": verdict,
        "thresholds": list(THRESHOLDS),
        "best_threshold": best_t,
        "jev_metrics": jev_metrics_by_threshold,
        "llm_metrics": llm_metrics,
        "calibration_gap_avg": calibration_gap,
        "latency_p95_s": round(p95, 3) if p95 else None,
        "unrecovered_429": unrecovered,
        "input_tokens_total": input_tokens_total,
        "cost_estimate_batch100_usd": round(
            (input_tokens_total / len(RECORDS) * 100) / 1_000_000 * INPUT_PRICE_PER_1M, 6
        ),
        "input_price_unverified": INPUT_PRICE_PER_1M,
        "checks": checks,
        "records": len(RECORDS),
    }
    save_result("s7_jev_parity", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nS7 VERDICT: {verdict} (threshold tốt nhất: {best_t})")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
