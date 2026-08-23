import os
import sys

TURBO_BASE_URL = os.environ.get("TURBO_BASE_URL", "http://127.0.0.1:8080")
TURBO_MODEL_ID = os.environ.get("TURBO_MODEL_ID", "gemma-4-26b-a4b-it")
PROBE_TIMEOUT_S = float(os.environ.get("PROBE_TIMEOUT_S", "1.5"))
CHAT_CONNECT_TIMEOUT_S = float(os.environ.get("CHAT_CONNECT_TIMEOUT_S", "5"))
CHAT_READ_TIMEOUT_S = float(os.environ.get("CHAT_READ_TIMEOUT_S", "600"))
MAX_CONTEXT_TOKENS = int(os.environ.get("MAX_CONTEXT_TOKENS", "16384"))
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5001"))


def _default_frontend_dist() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = []
    # Homebrew layout: venv lives at <prefix>/opt/<name>/libexec, static
    # assets are installed at <prefix>/share/vicinus-ai/dist.
    prefix = os.path.abspath(os.path.join(sys.prefix, "..", "..", ".."))
    candidates.append(os.path.join(prefix, "share", "vicinus-ai", "dist"))
    # Development checkout layout.
    candidates.append(os.path.normpath(os.path.join(here, "..", "frontend", "dist")))
    for cand in candidates:
        if os.path.isfile(os.path.join(cand, "index.html")):
            return cand
    return candidates[-1]


FRONTEND_DIST = os.environ.get("FRONTEND_DIST") or _default_frontend_dist()

MODEL_CARD = {
    "id": TURBO_MODEL_ID,
    "name": "Gemma 4 26B-A4B IT",
    "total_params": "26B",
    "active_params_per_token": "~3.88B",
    "quantization": "MLX affine 4-bit (group 64), 8-bit router",
    "resident_memory_gb": 2.05,
    "installed_size_gb": 14.3,
    "layers": 30,
    "full_attention_layers": 5,
    "sliding_window_layers": 25,
    "experts_per_layer": 128,
    "routed_experts_per_token": 8,
    "default_cache_slots": 16,
    "default_cache_policy": "LFU",
    "prefill_chunk_tokens": 128,
    "max_context": MAX_CONTEXT_TOKENS,
}
