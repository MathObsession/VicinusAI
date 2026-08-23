import json
import os
import time

from flask import (
    Flask,
    Response,
    jsonify,
    request,
    send_from_directory,
    stream_with_context,
)

import config
from simulator import simulate_stream
from turbo_client import UpstreamError, probe, stream_chat_completions

app = Flask(__name__, static_folder=None)

_DIST = os.path.abspath(config.FRONTEND_DIST)


def sse(obj):
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@app.get("/api/health")
def health():
    upstream = probe()
    mode = "live" if upstream else "simulated"
    return jsonify(
        {
            "mode": mode,
            "upstream_url": config.TURBO_BASE_URL,
            "upstream": upstream,
            "model": config.MODEL_CARD,
        }
    )


def _sanitize_messages(raw):
    cleaned = []
    for m in raw or []:
        role = m.get("role")
        content = m.get("content")
        if role in ("system", "user", "assistant") and isinstance(content, str):
            cleaned.append({"role": role, "content": content})
    return cleaned


@app.post("/api/chat")
def chat():
    body = request.get_json(force=True, silent=True) or {}
    messages = _sanitize_messages(body.get("messages"))
    if not messages:
        return jsonify({"error": "messages must be a non-empty array"}), 400

    live = probe() is not None

    def generate():
        yield sse({"type": "start", "mode": "live" if live else "simulated",
                   "model": config.TURBO_MODEL_ID})
        if not live:
            started = time.time()
            first = True
            for evt in simulate_stream(body):
                if first:
                    elapsed = time.time() - started
                    if elapsed < 0.15:
                        time.sleep(0.15 - elapsed)
                    first = False
                yield sse(evt)
            return
        try:
            for chunk in stream_chat_completions({"messages": messages,
                                                  "options": body.get("options")}):
                choices = chunk.get("choices") or []
                if chunk.get("usage"):
                    usage = chunk["usage"]
                    details = (usage.get("prompt_tokens_details") or {})
                    yield sse({
                        "type": "usage",
                        "usage": {
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get(
                                "completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0),
                            "cached_tokens": details.get("cached_tokens", 0),
                        },
                    })
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content")
                if piece:
                    yield sse({"type": "token", "content": piece})
                finish = choices[0].get("finish_reason")
                if finish == "tool_calls":
                    yield sse({
                        "type": "notice",
                        "text": "Model requested tool calls; this web console "
                                "does not execute tools.",
                    })
                    break
            yield sse({"type": "done", "finish_reason": "stop"})
        except UpstreamError as e:
            yield sse({"type": "error", "text": str(e)})
            yield sse({"type": "done", "finish_reason": "error"})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/")
def index():
    if os.path.isfile(os.path.join(_DIST, "index.html")):
        return send_from_directory(_DIST, "index.html")
    return (
        "Frontend build not found. Run: cd frontend && npm install && "
        "npm run build  (or use `npm run dev` for the Vite dev server)",
        200,
    )


@app.get("/<path:path>")
def assets(path):
    full = os.path.join(_DIST, path)
    if os.path.isfile(full):
        return send_from_directory(_DIST, path)
    return send_from_directory(_DIST, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=config.FLASK_PORT, threaded=True)
