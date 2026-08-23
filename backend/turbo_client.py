import json

import requests

import config


class UpstreamError(Exception):
    pass


def probe():
    try:
        r = requests.get(
            f"{config.TURBO_BASE_URL}/health", timeout=config.PROBE_TIMEOUT_S
        )
        r.raise_for_status()
        health = r.json()
    except Exception:
        return None
    models = None
    try:
        m = requests.get(
            f"{config.TURBO_BASE_URL}/v1/models", timeout=config.PROBE_TIMEOUT_S
        )
        if m.ok:
            payload = m.json()
            data = payload.get("data") or []
            models = [x.get("id") for x in data if x.get("id")]
    except Exception:
        pass
    return {"health": health, "models": models}


def _build_payload(body):
    options = body.get("options") or {}
    payload = {
        "model": config.TURBO_MODEL_ID,
        "messages": body.get("messages", []),
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if "temperature" in options:
        payload["temperature"] = float(options["temperature"])
    if "top_p" in options and options["top_p"] is not None:
        payload["top_p"] = float(options["top_p"])
    if "top_k" in options and options["top_k"] is not None:
        payload["top_k"] = int(options["top_k"])
    if "repetition_penalty" in options and options["repetition_penalty"] is not None:
        payload["repetition_penalty"] = float(options["repetition_penalty"])
    if "max_tokens" in options and options["max_tokens"] is not None:
        payload["max_completion_tokens"] = int(options["max_tokens"])
    if "seed" in options and options["seed"] not in (None, ""):
        payload["seed"] = int(options["seed"])
    stops = options.get("stop")
    if stops:
        payload["stop"] = stops if isinstance(stops, list) else [stops]
    return payload


def stream_chat_completions(body):
    url = f"{config.TURBO_BASE_URL}/v1/chat/completions"
    payload = _build_payload(body)
    try:
        r = requests.post(
            url,
            json=payload,
            stream=True,
            headers={"Content-Type": "application/json"},
            timeout=(config.CHAT_CONNECT_TIMEOUT_S, config.CHAT_READ_TIMEOUT_S),
        )
    except requests.RequestException as e:
        raise UpstreamError(f"cannot reach TurboFieldfareServer: {e}") from e
    if not r.ok:
        detail = r.text[:400]
        raise UpstreamError(f"upstream returned HTTP {r.status_code}: {detail}")
    for raw in r.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue
        chunk = raw[len("data:") :].strip()
        if chunk == "[DONE]":
            return
        try:
            yield json.loads(chunk)
        except json.JSONDecodeError:
            continue
