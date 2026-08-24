"""Spike S2 — Provider tại LLM_BASE_URL có honor `json_schema` response_format?

10 call độc lập, temperature=0, schema nhỏ (sentiment + severity) trên 10 câu
feedback VI tổng hợp (không PII). Pass: >= 9/10 valid -> mode production =
json_schema. Nếu < 9/10 hoặc provider từ chối: đo mode prompt-JSON +
strip fence + Pydantic validate + retry 1 lần (chính là fallback chain Phase 07).
Output: JSON ra stdout + results/s2_llm_schema_result.json (gitignored).
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import llm_client_cfg, load_env_file, save_result, utf8_stdio  # noqa: E402

utf8_stdio()

from openai import OpenAI  # noqa: E402
from pydantic import BaseModel, ValidationError  # noqa: E402

SENTENCES = [
    "App mở rất nhanh nhưng thanh tìm kiếm hay bị lag.",
    "Tôi thích giao diện mới, sạch và dễ dùng.",
    "Ứng dụng tự thoát bất ngờ khi tôi đang xem video.",
    "Bản cập nhật vừa rồi làm pin tụt nhanh kinh khủng.",
    "Chức năng xuất PDF hoạt động ổn định, đáng tiền.",
    "Đăng nhập bằng vân tay đôi lúc nhận lúc không, khó chịu.",
    "Hỗ trợ khách hàng trả lời chậm mà cũng không giải quyết được gì.",
    "Tính năng đồng bộ giữa các thiết bị chạy mượt, quá ổn.",
    "Quảng cáo dày đặc khiến trải nghiệm tệ đi nhiều.",
    "Nhìn chung app bình thường, không có gì nổi bật.",
]


class Label(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"]
    severity: Literal["low", "medium", "high", "critical"]


JSON_SCHEMA_FMT = {
    "type": "json_schema",
    "json_schema": {
        "name": "feedback_label",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "neutral", "negative"],
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
            },
            "required": ["sentiment", "severity"],
            "additionalProperties": False,
        },
    },
}

SYS_SCHEMA = (
    "You label user feedback about an app. Respond with the JSON object only."
)
SYS_PROMPT_JSON = (
    'Return ONLY a JSON object matching {"sentiment": "...", "severity": "..."} '
    "where sentiment is one of positive|neutral|negative and severity is one of "
    "low|medium|high|critical. No markdown fences, no extra text."
)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")
_BRACE_RE = re.compile(r"\{.*\}", re.S)


def extract_json(text):
    cleaned = _FENCE_RE.sub("", text.strip()).strip()
    m = _BRACE_RE.search(cleaned)
    return m.group(0) if m else cleaned


def try_validate(content):
    """Return (label_or_None, error_or_None)."""
    try:
        return Label.model_validate_json(content), None
    except (ValidationError, ValueError) as exc:
        return None, str(exc).replace("\n", " ")[:200]


def run_mode(client, model, mode, sentences):
    valid = 0
    retries_used = 0
    errors = []
    t0 = time.perf_counter()
    for idx, sentence in enumerate(sentences):
        messages = [
            {"role": "system", "content": SYS_PROMPT_JSON if mode == "prompt_json" else SYS_SCHEMA},
            {"role": "user", "content": sentence},
        ]
        kwargs = {"temperature": 0}
        if mode == "json_schema":
            kwargs["response_format"] = JSON_SCHEMA_FMT
        try:
            resp = client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )
            content = resp.choices[0].message.content or ""
            label, err = try_validate(content)
            if label is not None:
                valid += 1
                continue
            # retry MỘT lần kèm text lỗi (fallback chain của Phase 07)
            retries_used += 1
            messages.append({"role": "assistant", "content": content[:500]})
            messages.append({
                "role": "user",
                "content": f"JSON invalid: {err}. Return the corrected JSON object only.",
            })
            resp2 = client.chat.completions.create(model=model, messages=messages)
            label2, err2 = try_validate(resp2.choices[0].message.content or "")
            if label2 is not None:
                valid += 1
            else:
                errors.append(f"call#{idx}: {err2 or 'empty content'}")
        except Exception as exc:  # noqa: BLE001 — spike: ghi lại mọi loại lỗi
            msg = f"{type(exc).__name__}: {str(exc)[:250]}"
            errors.append(f"call#{idx}: {msg}")
            if mode == "json_schema" and "response_format" in msg:
                # provider từ chối hẳn tham số -> dừng sớm, chuyển fallback
                errors.append("PROVIDER_REJECTS_RESPONSE_FORMAT_PARAM")
                break
    return {
        "valid": valid,
        "total": len(sentences),
        "retries_used": retries_used,
        "elapsed_seconds": round(time.perf_counter() - t0, 1),
        "errors": errors[:6],
    }


def main():
    env = load_env_file()
    cfg = llm_client_cfg(env)
    client = OpenAI(
        base_url=cfg["base_url"], api_key=cfg["api_key"], timeout=120, max_retries=1
    )
    report = {
        "spike": "S2",
        "provider_model": cfg["model"],
        "base_url_host": cfg["base_url"].split("//")[-1].rstrip("/"),
        "temperature": 0,
    }

    report["json_schema_mode"] = run_mode(client, cfg["model"], "json_schema", SENTENCES)
    schema_ok = report["json_schema_mode"]["valid"] >= 9
    if not schema_ok:
        report["prompt_json_mode"] = run_mode(
            client, cfg["model"], "prompt_json", SENTENCES
        )
        prompt_ok = report["prompt_json_mode"]["valid"] >= 9
        report["production_mode"] = (
            "prompt_json_validate_retry" if prompt_ok else "none_reliable_review_needed"
        )
    else:
        report["production_mode"] = "json_schema"

    report["pass_criterion_ge_9_of_10"] = schema_ok
    save_result("s2_llm_schema", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
