# Vicinus AI

A React + Flask web app for [TurboFieldfare](https://github.com/drumih/turbo-fieldfare) —
the Swift + Metal runtime that runs **Gemma 4 26B-A4B IT in ~2 GB of RAM** on
Apple Silicon by keeping only the shared core resident and streaming routed
MoE experts from SSD on demand.

The console gives TurboFieldfare's local server a browser UI:

- Streaming chat with Gemma-style formatting handled for you (⌘↵ or ↵ to send, Esc/■ to stop)
- Sampling controls matching the native app: temperature, Top-K, Top-P, max tokens, seed
- Status bar with decode tok/s, prompt/output tokens, and reused-prefix tokens
- A live **router & expert-cache visualizer** showing top-8-of-128 routing,
  16-slot LFU cache hits/misses, and SSD read volume per generation
- Automatic **dual mode**: proxies a real `TurboFieldfareServer` when it is
  running; otherwise falls back to a built-in simulator that reproduces the
  same event stream (tokens + telemetry) so the UI is always explorable

## Architecture

```
┌─────────────────────────────┐   /api/chat (SSE)   ┌──────────────────────────┐
│ React frontend (Vite build) │ ──────────────────► │ Flask backend            │
│ chat · settings · telemetry │                     │  ├─ turbo_client.py      │
└─────────────────────────────┘                     │  │    proxy to upstream  │
                                                    │  ├─ simulator.py         │
                                                    │  │    offline MoE model  │
                                                    │  └─ /api/health probe    │
                                                    └────────────┬─────────────┘
                                                                 │ OpenAI-compatible
                                                                 ▼
                                              http://127.0.0.1:8080/v1
                                              TurboFieldfareServer (Swift)
```

## Install (Homebrew)

```bash
brew install mathobsession/tap/vicinus-ai
```

That single command adds and trusts the tap automatically, then builds
everything — the Swift inference runtime, the React frontend, and the
Python console. Afterwards the short form works too:

```bash
brew install vicinus-ai          # reinstall / update later
vicinus-ai                       # boots inference server :8080 + web UI :5001
```

then launch everything with:

```bash
vicinus-ai                       # boots inference server :8080 + web UI :5001
```

First run downloads the Gemma 4 model (~15 GB, once) to
`~/Library/Application Support/VicinusAI/gemma4.gturbo`. Point
`VICINUS_MODEL_DIR` at an existing `.gturbo` installation to skip it.
`Ctrl+C` stops both servers cleanly.

## Prerequisites (development)

- Python 3.10+ and Node.js 18+
- Optional: the [turbo-fieldfare](https://github.com/drumih/turbo-fieldfare)
  runtime built with an installed `scratch/gemma4.gturbo` model (~14.3 GB)

## Run

1. One-command stack (recommended):

```bash
pip install -e .
vicinus-ai                       # http://localhost:5001 (UI) + :8080 (inference)
```

Useful flags: `--no-turbo` (simulated UI only), `--skip-download`,
`--model PATH`, `--flask-port`, `--turbo-port`, and `--dev`.

**Dev mode (`vicinus-ai --dev`)**: the web backend owns the inference server,
which unlocks the **Save & reload model** button in the settings panel
(toggle Dev mode in the sidebar). Saving restarts TurboFieldfareServer with
the selected runtime flags (context window, expert-cache slots) — sampling
parameters (temperature, top-k, top-p, seed) always apply per message without
a reload. In normal (non-dev) runs the button is hidden; server flags stay
fixed for the life of the process.

2. Backend only:

```bash
pip install -e .
python -m vicinusai.app          # serves http://127.0.0.1:5001
```

2. Frontend — either the dev server (hot reload):

```bash
cd frontend
npm install
npm run dev                      # serves http://localhost:5173, proxies /api
```

or a production build served directly by Flask:

```bash
cd frontend && npm run build     # then just open http://127.0.0.1:5001
```

3. (Optional) For real inference, start the upstream server first:

```bash
cd turbo-fieldfare
swift build -c release --product TurboFieldfareServer
.build/release/TurboFieldfareServer --model scratch/gemma4.gturbo --port 8080
```

The console detects it within ~10 s and flips its badge from *Simulated* to
*Live*. No code changes needed.

## Configuration (environment variables)

| Variable | Default | Purpose |
| --- | --- | --- |
| `TURBO_BASE_URL` | `http://127.0.0.1:8080` | Upstream TurboFieldfareServer |
| `TURBO_MODEL_ID` | `gemma-4-26b-a4b-it` | Model id sent to the server |
| `FLASK_PORT` | `5001` | Web backend port |
| `MAX_CONTEXT_TOKENS` | `16384` | Advertised context window |
| `FRONTEND_DIST` | `../frontend/dist` | Static build served at `/` |

## API

- `GET /api/health` → `{mode: "live"|"simulated", model: {...}, upstream: {...}}`
- `POST /api/chat` → SSE stream with frames:
  - `{type:"start", prompt_tokens, cached_tokens}`
  - `{type:"token", content}` (repeated)
  - `{type:"telemetry", tok_per_sec, cache_hit_rate, bytes_read_mb, misses_total, evictions_total, memory_gb, kv_tokens, layer_sample, expert_states[128]}` (simulator)
  - `{type:"usage", usage:{prompt_tokens, completion_tokens, cached_tokens}}`
  - `{type:"done", finish_reason}` / `{type:"error"|"notice", text}`

`cached_tokens` mirrors the upstream's single-prefix KV reuse
(`usage.prompt_tokens_details.cached_tokens`) — keep sending the full history.

## Scope notes

- The simulator is an educational stand-in: same event shapes and plausible
  numbers (5–6 tok/s, LFU warm-up curve), but not real model output.
- Tool calls are not executed here; if the model returns `finish_reason:
  tool_calls`, the console surfaces a notice instead.
- The upstream server is loopback-only (no TLS/auth) — keep it that way.

## License

Apache-2.0, matching turbo-fieldfare. Model weights are not included and stay
governed by their source terms.
