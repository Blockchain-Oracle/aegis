#!/usr/bin/env bash
# Setup script for the Splunk Hosted Models real integration (ADR-003a
# Transport B-Ollama). Installs Ollama, pulls the default Hosted Model,
# and verifies the inference path end-to-end.
#
# Idempotent: safe to re-run. Re-running on a working setup is a no-op
# (skips brew install if ollama is in PATH, skips pull if model is
# present, runs the verify-prompt regardless so operators have a fresh
# health check).
#
# Usage:
#   bash scripts/setup_hosted_models.sh
#   bash scripts/setup_hosted_models.sh --model foundation-sec:8b
#
# Env overrides:
#   OLLAMA_HOST   default http://localhost:11434
#   SUIT_MODEL    default gpt-oss:20b (Apache-2.0, in the Ollama library)
#                 alt:    foundation-sec:8b (requires user-side Modelfile
#                         creation from the HF GGUF distribution)

set -euo pipefail

OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
SUIT_MODEL="${SUIT_MODEL:-gpt-oss:20b}"

while [ $# -gt 0 ]; do
  case "$1" in
    --model)
      SUIT_MODEL="$2"
      shift 2
      ;;
    --host)
      OLLAMA_HOST="$2"
      shift 2
      ;;
    -h|--help)
      sed -n '1,30p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

# ----------------------------------------------------------------------
# 1. Install Ollama if missing.
# ----------------------------------------------------------------------
if ! command -v ollama >/dev/null 2>&1; then
  echo "==> Ollama not found. Installing via Homebrew..."
  if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew not found. Install from https://brew.sh first." >&2
    echo "       Or follow https://ollama.com/download for a direct install." >&2
    exit 1
  fi
  brew install ollama
fi
echo "==> Ollama installed: $(ollama --version 2>&1 | head -1)"

# ----------------------------------------------------------------------
# 2. Ensure the Ollama server is reachable (start if not).
# ----------------------------------------------------------------------
if ! curl -fs "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
  echo "==> Ollama server not reachable at ${OLLAMA_HOST}. Starting in the background..."
  # `ollama serve` blocks; we background it and wait for /api/tags to answer.
  nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
  SERVE_PID=$!
  echo "    PID $SERVE_PID — logs at /tmp/ollama-serve.log"
  # Wait up to 30s for the server to come up.
  for i in $(seq 1 30); do
    if curl -fs "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! curl -fs "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
    echo "ERROR: Ollama server did not start in 30s." >&2
    echo "       Check /tmp/ollama-serve.log" >&2
    exit 1
  fi
fi
echo "==> Ollama server reachable at ${OLLAMA_HOST}"

# ----------------------------------------------------------------------
# 3. Pull the model if absent.
# ----------------------------------------------------------------------
if ! curl -fs "${OLLAMA_HOST}/api/tags" | grep -q "\"$SUIT_MODEL\""; then
  echo "==> Pulling ${SUIT_MODEL} (this may take a few minutes — large download)..."
  ollama pull "${SUIT_MODEL}"
fi
echo "==> Model ${SUIT_MODEL} present in Ollama"

# ----------------------------------------------------------------------
# 4. Health check via /api/generate (the same endpoint the SplunkGate
#    explainer uses). Prints the model's response so operators have a
#    visible signal the path works.
# ----------------------------------------------------------------------
echo "==> Health check: posting a verdict-style prompt to /api/generate..."
HEALTH_PROMPT=$(cat <<'EOF'
You are a security copilot. Explain this AI safety verdict in one sentence (<= 280 chars):
Verdict: BLOCK
Severity: HIGH
Rules: Prompt Injection (source=ai_defense)
Output the sentence only.
EOF
)

HEALTH_BODY=$(jq -n \
  --arg model "$SUIT_MODEL" \
  --arg prompt "$HEALTH_PROMPT" \
  '{model: $model, prompt: $prompt, stream: false, options: {temperature: 0.2, num_predict: 100}}')

RESPONSE=$(curl -fs -X POST "${OLLAMA_HOST}/api/generate" \
  -H "Content-Type: application/json" \
  -d "$HEALTH_BODY" | jq -r '.response // empty')

if [ -z "$RESPONSE" ]; then
  echo "ERROR: empty response from /api/generate" >&2
  exit 1
fi
echo ""
echo "    Model response: ${RESPONSE}"
echo ""

# ----------------------------------------------------------------------
# 5. Print env vars the operator should set to enable live inference
#    in the SplunkGate middleware.
# ----------------------------------------------------------------------
cat <<EOF

==> Setup complete. To enable the live Hosted Model in SplunkGate:

    # Add to your Config(...) call site:
    Config(
        ai_defense_api_key=SecretStr(os.environ["SPLUNKGATE_AI_DEFENSE_API_KEY"]),
        explainer_backend="ollama",      # was "template"
        explainer_model="${SUIT_MODEL}",  # default
        explainer_ollama_url=None,       # falls through to OLLAMA_HOST
    )

    # Or via env (for the integration test):
    export OLLAMA_HOST=${OLLAMA_HOST}
    export RUN_HOSTED_MODELS_LIVE_TESTS=1
    uv run pytest packages/splunkgate_judges/tests/test_hosted_models_live.py -v

EOF
