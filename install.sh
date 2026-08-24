#!/usr/bin/env bash
# VicinusAI one-line installer:
#   curl -fsSL https://raw.githubusercontent.com/MathObsession/VicinusAI/main/install.sh | bash
set -euo pipefail

if ! command -v brew >/dev/null 2>&1; then
    echo "❌ Homebrew is required: https://brew.sh" >&2
    exit 1
fi

echo "🔑 Tapping MathObsession/tap…"
brew tap MathObsession/tap https://github.com/MathObsession/homebrew-tap

echo "🤝 Trusting tap (one-time)…"
brew trust mathobsession/tap 2>/dev/null || echo "    already trusted"

echo "📦 Installing vicinus-ai (builds turbo-fieldfare + React frontend; a few minutes)…"
brew install mathobsession/tap/vicinus-ai

echo
echo "✅ Done! Launch the AI stack with:"
echo "    vicinus-ai"
echo "(first run downloads the ~15 GB Gemma 4 model once)"
