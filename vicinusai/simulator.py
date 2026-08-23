import json
import random
import time

from . import config

TOTAL_LAYERS = config.MODEL_CARD["layers"]
EXPERTS_PER_LAYER = config.MODEL_CARD["experts_per_layer"]
TOP_K_ROUTED = config.MODEL_CARD["routed_experts_per_token"]
DEFAULT_SLOTS = config.MODEL_CARD["default_cache_slots"]
EXPERT_BYTES = 14_336_000
RESIDENT_CORE_GB = 1.35
KV_BYTES_PER_TOKEN = 96_000
BASE_TOK_PER_SEC = 5.6


def approx_tokens(text):
    return max(1, round(len(text) / 4))


class ExpertCache:
    def __init__(self, slots, pinned=False):
        self.slots = slots
        self.pinned = pinned
        self.entries = {}
        self.freq = {}
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.bytes_read = 0

    def lookup(self, expert_id):
        if self.pinned:
            self.hits += 1
            return True
        if expert_id in self.entries:
            self.hits += 1
            self.freq[expert_id] += 1
            return True
        self.misses += 1
        self.bytes_read += EXPERT_BYTES
        if len(self.entries) >= self.slots:
            victim = min(self.entries, key=lambda e: (self.freq.get(e, 0), e))
            del self.entries[victim]
            del self.freq[victim]
            self.evictions += 1
        self.entries[expert_id] = True
        self.freq[expert_id] = 1
        return False


_ZIPF_WEIGHTS = [1.0 / ((i + 1) ** 0.65) for i in range(EXPERTS_PER_LAYER)]


class RouterSim:
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def pick(self):
        return set(
            zipf_sample(_ZIPF_WEIGHTS, TOP_K_ROUTED, self.rng)
        )


def zipf_sample(weights, k, rng):
    total = sum(weights)
    picked = []
    pool = list(range(len(weights)))
    for _ in range(k):
        r = rng.random() * total
        acc = 0.0
        for idx in pool:
            acc += weights[idx]
            if r <= acc:
                picked.append(idx)
                pool.remove(idx)
                total -= weights[idx]
                break
    return picked


_PROMPT_SIGNATURE_KEY = "_turbo_web_last_prompt"


class SimulatorState:
    last_prompt_tokens = None
    last_signature = None


def _signature(messages):
    return json.dumps(
        [[m.get("role"), m.get("content")] for m in messages],
        ensure_ascii=False,
    )


def _prefix_cached_tokens(messages):
    sig = _signature(messages)
    prev = SimulatorState.last_prompt_tokens
    prev_sig = SimulatorState.last_signature
    SimulatorState.last_signature = sig
    total = sum(approx_tokens(m.get("content", "")) for m in messages)
    SimulatorState.last_prompt_tokens = total
    if prev_sig and sig.startswith(prev_sig[:-1]) and prev:
        history = json.loads(prev_sig)
        reused = 0
        kept = []
        for item in history:
            probe = json.dumps(kept + [item], ensure_ascii=False)
            if not sig.startswith(probe[:-1]):
                break
            kept.append(item)
            reused += approx_tokens(item[1])
        return max(0, min(reused, total - 1))
    return 0


def compose_reply(messages):
    user_texts = [
        m.get("content", "") for m in messages if m.get("role") == "user"
    ]
    text = " ".join(user_texts).strip()
    low = text.lower()

    def has(*words):
        return any(w in low for w in words)

    if not text:
        body = (
            "It looks like your message came through empty. "
            "Type a prompt above and press Enter to generate."
        )
    elif has("hello", "hi ", "hey", "greetings") or low in ("hi", "hey"):
        body = (
            "Hello! This web console talks to TurboFieldfare, a Swift + Metal "
            "runtime that runs Gemma 4 26B-A4B in about 2 GB of RAM on Apple "
            "Silicon by keeping only the shared core resident and streaming "
            "routed experts from SSD as the router requests them. Ask me about "
            "the architecture, or start TurboFieldfareServer locally for real "
            "model output."
        )
    elif has("how", "why", "explain", "memory", "ram", "stream", "ssd", "moe",
             "expert", "router", "cache", "metal", "work"):
        body = (
            "TurboFieldfare never holds the full 14.3 GB checkpoint in memory. "
            "A ~1.35 GB shared core plus an FP16 KV cache stay resident while "
            "each transformer layer runs a tiny 8-bit router that picks the "
            "top-8 of 128 routed experts for every token. Missing experts are "
            "filled into a small LFU cache with bounded parallel pread calls, "
            "so a Mac with 8 GB of RAM can decode at several tokens per "
            "second. Prefill proceeds in 128-token chunks so one fetched "
            "expert serves many rows, and attention mixes 25 sliding-window "
            "layers with 5 full-attention layers to keep KV storage bounded."
        )
    elif has("benchmark", "speed", "fast", "tok", "performance"):
        body = (
            "Measured reference points: roughly 5-6 tok/s decode on an 8 GB M2 "
            "MacBook Air and 31-35 tok/s on a 24 GB M5 Pro, always within a "
            "~2 GB memory budget. Throughput depends on prompt length, page "
            "cache state, and how warm the expert cache is."
        )
    else:
        topic = text if len(text) < 120 else text[:117] + "..."
        body = (
            f"You asked about \"{topic}\". The real Gemma 4 checkpoint would "
            "answer this directly; right now the web console is running its "
            "built-in simulator because no TurboFieldfareServer was detected "
            "on 127.0.0.1:8080. Build the server from the turbo-fieldfare repo "
            "(swift build -c release --product TurboFieldfareServer), point it "
            "at scratch/gemma4.gturbo, restart this app, and the same chat box "
            "will stream genuine model output with prompt-prefix reuse."
        )
    note = (
        "\n\n_Simulated output - the backend did not detect a running "
        "TurboFieldfareServer._"
    )
    return body + note


def tokenize(text):
    parts = text.split(" ")
    out = []
    for i, part in enumerate(parts):
        if part == "":
            continue
        out.append(part if i == len(parts) - 1 else part + " ")
    return out


def simulate_stream(body):
    options = body.get("options") or {}
    messages = body.get("messages", [])
    seed = options.get("seed")
    rng_seed = int(seed) if seed not in (None, "") else random.randrange(2**32)
    slots = int(options.get("cache_slots") or DEFAULT_SLOTS)
    max_tokens = int(options.get("max_tokens") or 1024)
    context = int(options.get("context") or config.MAX_CONTEXT_TOKENS)
    prefill = str(options.get("prefill") or "on").lower()
    rdadvise = str(options.get("rdadvise") or "bounded").lower()
    resident_n = max(0, min(TOTAL_LAYERS, int(options.get("resident_layers") or 0)))
    miss_penalty = 0.00008 if rdadvise == "bounded" else 0.00018
    stop_strings = options.get("stop") or []
    if isinstance(stop_strings, str):
        stop_strings = [stop_strings]

    cached_prompt = _prefix_cached_tokens(messages)
    prompt_tokens = sum(
        approx_tokens(m.get("content", "")) for m in messages
    )

    reply = compose_reply(messages)
    words = tokenize(reply)[:max_tokens]

    caches = [
        ExpertCache(slots, pinned=i < resident_n) for i in range(TOTAL_LAYERS)
    ]
    router = RouterSim(rng_seed)

    yield {
        "type": "start",
        "mode": "simulated",
        "model": config.TURBO_MODEL_ID,
        "prompt_tokens": prompt_tokens,
        "cached_tokens": cached_prompt,
    }

    if prefill == "on":
        time.sleep(min(0.35, prompt_tokens * 0.0035))
    else:
        time.sleep(min(2.2, prompt_tokens * 0.02))

    generated = ""
    started = time.time()
    emitted = 0
    active_layer = TOTAL_LAYERS // 2
    stop_reason = "stop" if len(words) < max_tokens else "length"

    for step, word in enumerate(words):
        if prompt_tokens + emitted >= context:
            stop_reason = "length"
            break
        cut = None
        for s in stop_strings:
            idx = (generated + word).find(s)
            if idx != -1:
                cut = idx
                break
        if cut is not None:
            break
        generated += word

        states = ["idle"] * EXPERTS_PER_LAYER
        misses_this_step = 0
        for cache in caches:
            picked = router.pick()
            for eid in picked:
                hit = cache.lookup(eid)
                if not hit:
                    misses_this_step += 1
        rep_cache = caches[active_layer]
        for eid in router.pick():
            states[eid] = "active"
        for eid in rep_cache.entries:
            if states[eid] == "idle":
                states[eid] = "cached"

        elapsed = time.time() - started
        emitted += 1
        yield {"type": "token", "content": word}
        if (step + 1) % 8 == 0 or step == len(words) - 1:
            kv_gb = (prompt_tokens + emitted) * KV_BYTES_PER_TOKEN / 1e9
            total_hits = sum(c.hits for c in caches)
            total_lookups = sum(c.hits + c.misses for c in caches)
            yield {
                "type": "telemetry",
                "tokens": emitted,
                "tok_per_sec": round(emitted / elapsed, 2) if elapsed > 0 else 0,
                "cache_hit_rate": round(
                    total_hits / total_lookups, 4
                ) if total_lookups else 0,
                "misses_total": sum(c.misses for c in caches),
                "evictions_total": sum(c.evictions for c in caches),
                "bytes_read_mb": round(
                    sum(c.bytes_read for c in caches) / 1e6, 1
                ),
                "memory_gb": round(RESIDENT_CORE_GB + kv_gb + 0.7, 2),
                "kv_tokens": prompt_tokens + emitted,
                "layer_sample": active_layer,
                "expert_states": states,
            }
        time.sleep(
            max(0.004, random.gauss(1.0 / BASE_TOK_PER_SEC, 0.03))
            + misses_this_step * miss_penalty
        )

    elapsed = time.time() - started
    yield {
        "type": "usage",
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": emitted,
            "total_tokens": prompt_tokens + emitted,
            "cached_tokens": cached_prompt,
        },
    }
    yield {
        "type": "done",
        "finish_reason": stop_reason,
        "elapsed_s": round(elapsed, 2),
    }
