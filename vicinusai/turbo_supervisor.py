"""Supervises a TurboFieldfareServer process owned by the web backend.

Enabled only in dev mode (VICINUS_MANAGE_TURBO=1 with a resolvable server
binary and model path). Lets the settings panel restart the model with new
runtime flags (context, expert-cache slots/policy, prompt-cache mode).
"""

from __future__ import annotations

import atexit
import os
import subprocess
import threading
import time
from pathlib import Path

ALLOWED_CONTEXTS = (4096, 8192, 16384, 32768, 65536)
ALLOWED_SLOTS = (8, 16, 24, 32)
ALLOWED_POLICY = ("lfu", "lru")
ALLOWED_PROMPT_CACHE = ("off", "single-prefix")
ALLOWED_PREFILL = ("on", "off")
ALLOWED_RDADVISE = ("off", "default", "bounded", "adaptive")

DEFAULT_SETTINGS = {
    "max_context": 16384,
    "expert_cache_slots": 16,
    "expert_cache_policy": "lfu",
    "prompt_cache_mode": "single-prefix",
    "prefill": "on",
    "rdadvise": "off",
}


def validate_settings(raw: dict, current: dict | None = None) -> tuple[dict | None, str | None]:
    """Return (clean_settings, None) or (None, error_message).

    Unknown keys (e.g. sampling parameters, which apply per request) are
    ignored. Cross-field rule: chunked prefill needs >= 16 cache slots.
    """
    cur = dict(DEFAULT_SETTINGS if current is None else current)
    clean = {}
    ctx = raw.get("max_context")
    if ctx is not None:
        if int(ctx) not in ALLOWED_CONTEXTS:
            return None, f"max_context must be one of {list(ALLOWED_CONTEXTS)}"
        clean["max_context"] = int(ctx)
    slots = raw.get("expert_cache_slots")
    if slots is not None and slots != "":
        if int(slots) not in ALLOWED_SLOTS:
            return None, f"expert_cache_slots must be one of {list(ALLOWED_SLOTS)}"
        clean["expert_cache_slots"] = int(slots)
    policy = raw.get("expert_cache_policy")
    if policy is not None:
        if policy not in ALLOWED_POLICY:
            return None, f"expert_cache_policy must be one of {ALLOWED_POLICY}"
        clean["expert_cache_policy"] = policy
    pcm = raw.get("prompt_cache_mode")
    if pcm is not None:
        if pcm not in ALLOWED_PROMPT_CACHE:
            return None, f"prompt_cache_mode must be one of {ALLOWED_PROMPT_CACHE}"
        clean["prompt_cache_mode"] = pcm
    prefill = raw.get("prefill")
    if prefill is not None:
        if prefill not in ALLOWED_PREFILL:
            return None, f"prefill must be one of {ALLOWED_PREFILL}"
        clean["prefill"] = prefill
    rdadvise = raw.get("rdadvise")
    if rdadvise is not None:
        if rdadvise not in ALLOWED_RDADVISE:
            return None, f"rdadvise must be one of {ALLOWED_RDADVISE}"
        clean["rdadvise"] = rdadvise

    merged = {**cur, **clean}
    if merged.get("prefill") == "on" and int(merged.get("expert_cache_slots", 16)) < 16:
        return None, (
            "chunked prefill requires at least 16 expert-cache slots "
            "(set Prefill to off, or pick 16+ slots)"
        )
    return clean, None


class TurboSupervisor:
    def __init__(self, binary: Path, model_path: Path, port: int):
        self.binary = binary
        self.model_path = model_path
        self.port = port
        self.settings = dict(DEFAULT_SETTINGS)
        self.proc: subprocess.Popen | None = None
        self.reloading = False
        self.last_error: str | None = None
        self._lock = threading.Lock()
        atexit.register(self.stop)

    @classmethod
    def from_env(cls) -> "TurboSupervisor | None":
        """Build a supervisor when dev-manage env vars are present."""
        if os.environ.get("VICINUS_MANAGE_TURBO") != "1":
            return None
        binary = os.environ.get("TURBO_SERVER_BIN")
        model = os.environ.get("VICINUS_MODEL_PATH")
        if not binary or not model:
            return None
        base = os.environ.get("TURBO_BASE_URL", "")
        port = None
        if base:
            try:
                port = int(base.rsplit(":", 1)[1])
            except (IndexError, ValueError):
                port = None
        if port is None:
            port = int(os.environ.get("TURBO_PORT", "8080"))
        return cls(Path(binary), Path(model), port)

    def _cmd(self) -> list[str]:
        s = self.settings
        return [
            str(self.binary),
            "--model",
            str(self.model_path),
            "--port",
            str(self.port),
            "--max-context",
            str(s["max_context"]),
            "--expert-cache-slots",
            str(s["expert_cache_slots"]),
            "--expert-cache-policy",
            s["expert_cache_policy"],
            "--prompt-cache-mode",
            s["prompt_cache_mode"],
            "--prefill",
            s["prefill"],
            "--rdadvise",
            s["rdadvise"],
        ]

    def _stop_current(self, timeout: float = 15.0) -> None:
        if self.proc is None or self.proc.poll() is not None:
            self.proc = None
            return
        self.proc.terminate()
        deadline = time.time() + timeout
        while self.proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if self.proc.poll() is None:
            self.proc.kill()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        self.proc = None

    def start(self) -> bool:
        """Start the server with current settings. Returns success."""
        with self._lock:
            self._stop_current()
            log_path = Path.home() / "Library" / "Logs" / "VicinusAI"
            try:
                log_path.mkdir(parents=True, exist_ok=True)
                log = open(log_path / "turbo-server.log", "ab")
                self.proc = subprocess.Popen(
                    self._cmd(), stdout=log, stderr=subprocess.STDOUT
                )
                self.last_error = None
                return True
            except OSError as exc:
                self.last_error = str(exc)
                self.proc = None
                return False

    def apply(self, raw_settings: dict) -> tuple[bool, str | None]:
        """Validate, persist, and restart the server with new settings."""
        clean, err = validate_settings(raw_settings, self.settings)
        if err:
            return False, err
        with self._lock:
            self.settings.update(clean)
            self.reloading = True
        try:
            ok = self.start()
            if not ok:
                return False, self.last_error or "failed to start server"
            return True, None
        finally:
            with self._lock:
                self.reloading = False

    def snapshot(self) -> dict:
        return {
            "running": self.proc is not None and self.proc.poll() is None,
            "pid": self.proc.pid if self.proc else None,
            "settings": dict(self.settings),
            "reloading": self.reloading,
            "last_error": self.last_error,
        }

    def stop(self) -> None:
        with self._lock:
            self._stop_current()
