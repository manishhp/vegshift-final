from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List


LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
}


def _format_list(items: List[str]) -> str:
    return ", ".join(items) if items else "None"


def build_rule_steps(
    irrigation_method: str,
    sowing_window: str,
    avoid_crops: List[str],
    recommended_crops: List[str],
    profile: Dict[str, Any] | None = None,
) -> List[str]:
    method_label = irrigation_method.replace("_", " ") if irrigation_method else "recommended irrigation"
    steps: List[str] = [f"Confirm water source and set up {method_label} for this season."]

    if "drip" in irrigation_method:
        steps.append("For drip: install filters, add a pressure regulator, and check emitters.")
    if "sprinkler" in irrigation_method:
        steps.append("For sprinkler: verify nozzle spacing and account for wind direction.")
    if "rwh" in irrigation_method or "rain" in irrigation_method:
        steps.append("Add rainwater harvesting: rooftop collection plus contour trenches.")

    if sowing_window:
        steps.append(f"Prepare land and seeds so sowing starts {sowing_window}.")

    if avoid_crops:
        steps.append(f"Avoid high-water crops now: {_format_list(avoid_crops)}.")

    if recommended_crops:
        steps.append(f"Prioritize these crops: {_format_list(recommended_crops[:5])}.")

    if profile:
        budget = (profile.get("budgetINR") or "").strip()
        land = (profile.get("landSizeHa") or "").strip()
        if budget:
            steps.append(f"Match input costs to your budget of INR {budget}.")
        if land:
            steps.append(f"Plan inputs for about {land} hectares to avoid overbuying seed.")

    return steps


def _strip_code_block(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def _call_openai(messages: List[Dict[str, str]], model: str, api_key: str, base_url: str) -> List[str] | None:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 320,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return None

    content = (
        body.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if not content:
        return None

    raw = _strip_code_block(content)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
        return parsed
    return None


def generate_coach_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    irrigation_method = payload.get("irrigation_method", "")
    sowing_window = payload.get("sowing_window", "")
    avoid_crops = payload.get("avoid_crops") or []
    recommended_crops = payload.get("recommended_crops") or []
    profile = payload.get("profile")
    language = (payload.get("language") or "en").lower()

    rule_steps = build_rule_steps(
        irrigation_method=irrigation_method,
        sowing_window=sowing_window,
        avoid_crops=avoid_crops,
        recommended_crops=recommended_crops,
        profile=profile,
    )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"mode": "rule-based", "steps": rule_steps}

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    lang_name = LANGUAGE_NAMES.get(language, "English")

    system_msg = (
        "You are an agronomy assistant. Produce a concise action plan for the farmer. "
        "Return ONLY a JSON array of 5 to 7 short steps as strings, no extra text. "
        f"Respond in {lang_name}."
    )

    user_msg = (
        f"City: {payload.get('city', '')}\n"
        f"Irrigation method: {irrigation_method}\n"
        f"Sowing window: {sowing_window}\n"
        f"Avoid crops: {_format_list(avoid_crops)}\n"
        f"Recommended crops: {_format_list(recommended_crops)}\n"
        f"Farmer profile: {json.dumps(profile or {}, ensure_ascii=False)}\n"
        "Focus on concrete, practical steps a farmer can take this season."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    llm_steps = _call_openai(messages, model=model, api_key=api_key, base_url=base_url)
    if llm_steps:
        return {"mode": "llm", "steps": llm_steps}

    return {"mode": "rule-based", "steps": rule_steps}
