"""S7 via OpenRouter's TypeSafe-compatible System One API (default).

Run from backend/: uv run python ../scripts/spikes/s7_openrouter.py
Synthetic v1 fixture is frozen; primary threshold .6 is fixed BEFORE API calls.
No production writes, no env changes, no feedback/database reads.
--engine router is a separate chat-routing experiment, not Jev System One.
"""
import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone

import httpx

from _common import REPO_ROOT, load_env_file, save_result, utf8_stdio
from s7_jev_parity import (RECORDS, THRESHOLDS, TOPICS, EMOTIONS, SEVERITIES,
                           SENTIMENTS, INTENTS, jev_questions_for, _accuracy, _micro_f1_precision)


def systemone_prediction(answers):
    score = float(answers["severity"]["score"])
    if not math.isfinite(score) or not 0 <= score <= 3:
        raise ValueError("Invalid severity score")
    severity_index = round(score)
    raw = {"topics": [{"id": slug, "probability": answers[f"topic::{slug}"]["noul"]} for slug in TOPICS],
           "emotions": [{"label": emo, "probability": answers[f"emotion::{emo}"]["noul"]} for emo in EMOTIONS],
           "sentiment": answers["sentiment"]["choice"], "intent": answers["intent"]["choice"],
           "severity": SEVERITIES[severity_index],
           "choice_probabilities": {key: answers[key]["probabilities"][answers[key]["choice"]]
                                    for key in ("sentiment", "intent")}}
    raw["choice_probabilities"]["severity"] = answers["severity"]["probabilities"][str(severity_index)]
    probabilities = [v["probability"] for v in raw["topics"] + raw["emotions"]] + list(raw["choice_probabilities"].values())
    if raw["sentiment"] not in SENTIMENTS or raw["intent"] not in INTENTS or any(not 0 <= p <= 1 for p in probabilities):
        raise ValueError("Invalid typed answer")
    return raw


def calibration(predictions, truth):
    return {key: abs(sum(p["choice_probabilities"][key] for p in predictions) / len(truth)
                     - _accuracy([p[key] for p in predictions], [r[key] for r in truth]))
            for key in ("sentiment", "intent", "severity")}


def percentile95(values):
    return sorted(values)[math.ceil(.95 * len(values)) - 1] if values else None


def verdict(checks):
    if any(check is False for check in checks):
        return "FAIL"
    return "INCONCLUSIVE" if any(check is None for check in checks) else "PASS"


def evaluate(predictions, truth):
    metrics = {}
    for key, prefix in (("topics", "topic"), ("emotions", "emotion")):
        pred_sets = [set(p[key]) for p in predictions]
        true_sets = [set(r[key]) for r in truth]
        f1, precision = _micro_f1_precision(pred_sets, true_sets)
        metrics.update({f"{prefix}_micro_f1": f1,
                        f"{prefix}_precision": precision,
                        f"{prefix}_exact_accuracy": _accuracy(pred_sets, true_sets)})
    for key in ("sentiment", "intent", "severity"):
        metrics[f"{key}_accuracy"] = _accuracy(
            [p[key] for p in predictions], [r[key] for r in truth])
    return metrics


def labels(raw, threshold):
    return {
        "topics": [t["id"] for t in raw["topics"] if t["probability"] >= threshold],
        "emotions": [e["label"] for e in raw["emotions"]
                     if e["probability"] >= threshold and e["label"] != "neutral"] or ["neutral"],
        **{k: raw[k] for k in ("sentiment", "intent", "severity")},
    }


def main():
    utf8_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget100-usd", type=float, default=None)
    parser.add_argument("--name", default="s7_systemone_openrouter")
    parser.add_argument("--engine", choices=("systemone", "router"), default="systemone")
    args = parser.parse_args()
    env = load_env_file()
    if not env.get("LLM_API_KEY") or "openrouter.ai" not in env.get("LLM_BASE_URL", ""):
        print("Requires existing OpenRouter LLM configuration; no key values printed.")
        return 2
    models = {"jev_router": "jev-latest" if args.engine == "systemone" else env.get("MODEL_ENRICH"), "baseline": env.get("LLM_MODEL")}
    if not models["jev_router"] or models["baseline"] == models["jev_router"]:
        print("Expected Jev Router and a distinct configured baseline.")
        return 2
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from app.schemas.enrichment import EnrichmentOut, strict_enrichment_schema
    from app.services.enricher import _SYSTEM_PROMPT, _taxonomy_block
    from app.core.config import get_settings
    max_tokens = get_settings().LLM_MAX_TOKENS

    result = {
        "experiment": "s7-openrouter-v2-production-cap", "engine": args.engine, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": "https://openrouter.ai/api/v1/systemone" if args.engine == "systemone" else env["LLM_BASE_URL"].rstrip("/") + "/chat/completions",
        "direct_typesafe_status": "BLOCKED_MISSING_JEV_API_KEY" if not env.get("JEV_API_KEY") else "NOT_RUN",
        "models_requested": models, "records": len(RECORDS), "primary_threshold": .6,
        "fixture_sha256": hashlib.sha256(json.dumps(RECORDS, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        "prompt_sha256": hashlib.sha256(_SYSTEM_PROMPT.encode()).hexdigest(),
        "max_tokens": max_tokens,
        "budget100_usd": args.budget100_usd, "runs": {},
    }
    taxonomy = [(slug, slug) for slug in TOPICS]  # Original S7 taxonomy, no label edits.
    schema = {"type": "json_schema", "json_schema": {
        "name": "enrichment", "strict": True, "schema": strict_enrichment_schema()}}
    with httpx.Client(timeout=120) as client:
        for engine, model in models.items():
            is_systemone = engine == "jev_router" and args.engine == "systemone"
            rows = []
            result["runs"][engine] = rows
            for index, record in enumerate(RECORDS):
                start = time.perf_counter()
                row = {"record_index": index, "attempts": [], "finish_reasons": [], "prediction": None, "cost_usd": 0.0,
                       "cost_known": True, "prompt_tokens": 0, "completion_tokens": 0}
                rows.append(row)
                payload = {"model": model, "temperature": 0, "max_tokens": max_tokens,
                           "messages": [{"role": "system", "content": _SYSTEM_PROMPT},
                                        {"role": "user", "content": _taxonomy_block(taxonomy)
                                         + "Feedback cần phân loại:\n" + record["text"]}],
                           "response_format": schema}
                endpoint = env["LLM_BASE_URL"].rstrip("/") + "/chat/completions"
                if is_systemone:
                    endpoint = "https://openrouter.ai/api/v1/systemone"
                    payload = {"model": model, "state": record["text"], "questions": jev_questions_for(TOPICS)}
                structure_retries = 0
                rate_retries = 0
                while True:
                    try:
                        response = client.post(endpoint,
                                               headers={"Authorization": "Bearer " + env["LLM_API_KEY"]},
                                               json=payload)
                    except httpx.HTTPError as exc:
                        row["error"] = type(exc).__name__  # No request headers/body in error logs.
                        row["cost_known"] = False
                        break
                    row["attempts"].append(response.status_code)
                    if response.status_code in (429, 529) and rate_retries < 3:
                        time.sleep(2 ** rate_retries)
                        rate_retries += 1
                        continue
                    if response.status_code == 400 and payload.get("response_format") == schema:
                        payload["response_format"] = {"type": "json_object"}
                        continue
                    if response.status_code != 200:
                        row["error"] = "HTTP_" + str(response.status_code)
                        row["cost_known"] = False
                        break
                    body = response.json()
                    usage = body.get("usage", {})
                    row["cost_known"] &= usage.get("cost") is not None
                    row["cost_usd"] += float(usage.get("cost") or 0)
                    row["prompt_tokens"] += int(usage.get("prompt_tokens", usage.get("input_tokens")) or 0)
                    row["completion_tokens"] += int(usage.get("completion_tokens", usage.get("output_tokens")) or 0)
                    row["model_returned"] = body.get("model")
                    row["provider"] = body.get("provider")
                    row["finish_reasons"].append(body.get("choices", [{}])[0].get("finish_reason"))
                    try:
                        if is_systemone:
                            row["prediction"] = systemone_prediction(body["answers"])
                            row["answers"] = body["answers"]
                            break
                        content = body["choices"][0]["message"]["content"].strip()
                        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                        validated = EnrichmentOut.model_validate_json(content)
                        if any(t.id not in TOPICS for t in validated.topics):
                            raise ValueError("Unknown taxonomy slug")
                        row["prediction"] = validated.model_dump(mode="json")
                        break
                    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                        if structure_retries or is_systemone:
                            row["error"] = "INVALID_STRUCTURE"
                            break
                        structure_retries += 1
                        payload["messages"].append({"role": "user", "content": "Trả lại JSON đúng schema và chỉ dùng taxonomy đã cung cấp."})
                row["latency_s"] = time.perf_counter() - start
                save_result(args.name, result)  # Checkpoint after every paid record.
                print(f"{engine} {index + 1}/{len(RECORDS)}: {row.get('error', 'OK')} {row['latency_s']:.2f}s", flush=True)

    summaries = {}
    empty = {"topics": [], "emotions": [], "sentiment": None, "intent": None, "severity": None}
    for engine, rows in result["runs"].items():
        sweep = {str(t): evaluate([labels(r["prediction"], t) if r["prediction"] else empty
                                  for r in rows], RECORDS) for t in THRESHOLDS}
        summaries[engine] = {
            "metrics_by_threshold": sweep,
            "latency_p95_s": percentile95([r["latency_s"] for r in rows]),
            "failures": sum(r["prediction"] is None for r in rows),
            "unrecovered_429": sum(r.get("error") == "HTTP_429" for r in rows),
            "rate_limit_responses": sum(s == 429 for r in rows for s in r["attempts"]),
            "cost_usd": sum(r["cost_usd"] for r in rows),
            "cost_estimate100_usd": sum(r["cost_usd"] for r in rows) * 100 / len(RECORDS)
                                     if all(r["cost_known"] for r in rows) else None,
        }
    jev, baseline = summaries["jev_router"], summaries["baseline"]
    rows = result["runs"]["jev_router"]
    gaps = calibration([r["prediction"] for r in rows], RECORDS) if args.engine == "systemone" and all(r["prediction"] for r in rows) else None
    result["calibration_gaps_choice_splits"] = gaps
    metric_names = ("topic_exact_accuracy", "sentiment_accuracy", "emotion_exact_accuracy", "intent_accuracy", "severity_accuracy")
    checks = {
        "1_accuracy_within_5pts": all(abs(jev["metrics_by_threshold"]["0.6"][k] - baseline["metrics_by_threshold"]["0.6"][k]) <= .05 for k in metric_names),
        "2_calibration_gap_le_0.10": all(g <= .10 for g in gaps.values()) if gaps else None,
        "3_zero_unrecovered_429": jev["unrecovered_429"] == 0,
        "4_p95_latency_lt_2s": jev["latency_p95_s"] < 2,
        "5_cost_within_budget": jev["cost_estimate100_usd"] <= args.budget100_usd
                                if args.budget100_usd is not None and jev["cost_estimate100_usd"] is not None else None,
        "all_predictions_valid": all(s["failures"] == 0 for s in summaries.values()),
    }
    result.update(summary=summaries, checks=checks, verdict=verdict(checks.values()))
    save_result(args.name, result)
    print(json.dumps({k: result[k] for k in ("summary", "checks", "verdict")}, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
