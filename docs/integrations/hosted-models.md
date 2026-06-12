# Splunk Hosted Models integration

SplunkGate uses a **Splunk Hosted Model** to generate human-readable
WHY-strings for verdict explanations. This is the **explainer**
path — per ADR-003 the model NEVER classifies; that's still Cisco
AI Defense's job.

This integration satisfies the hackathon's **"Best Use of Splunk
Hosted Models"** bonus-prize criterion, which awards
"the most impactful use of Splunk-hosted AI models to solve real-world
problems ... leveraging capabilities like ... natural language
understanding."

## What's a "Hosted Model" in this context

The hackathon resources list **four** Splunk Hosted Models:

1. **Foundation-Sec-1.1-8B-Instruct** — Cisco's security copilot
   (`fdtn-ai/Foundation-Sec-1.1-8B-Instruct` on Hugging Face).
   Llama-3.1 backbone, 64k context, 94.74% HarmBench.
2. **gpt-oss-120b** — OpenAI open-weight, 117B params, single H100.
3. **gpt-oss-20b** — OpenAI open-weight, 21B params, 16GB RAM. Apache-2.0.
4. **Cisco Deep Time Series Model (CDTSM)** — Splunk Cloud-only
   forecasting; doesn't apply to our NL explanation use case.

SplunkGate's explainer can use any of (1)-(3) interchangeably. The
default is **gpt-oss-20b** because it ships in the official Ollama
library out-of-the-box — zero-friction setup for hackathon judges who
don't already have Foundation-Sec running locally.

## Transport options (per ADR-003a)

There are three valid transports. The explainer reads
`Config.explainer_backend` to pick:

### `"template"` (the v1 default — no model required)

Deterministic pure-Python string composition. Zero dependencies. Used
by CI and any caller who doesn't want to run an LLM. Output looks like:

```
BLOCK (severity HIGH): Prompt Injection [ai_defense].
```

### `"ollama"` (the SHIPPING Hosted Models path — real, no mocks)

Calls a local or remote Ollama server's `/api/generate` endpoint with
the Hosted Model tag. Implementation:
`packages/splunkgate_judges/src/splunkgate_judges/hosted_models.py`.

Contract:
- 30s timeout per call.
- Tenacity retry on transient HTTPX failures (3 attempts, exponential
  backoff).
- **Template fallback** on ANY exception — the verdict always carries
  a non-empty explanation.

Example output (real model, real call):

```
The agent's request was blocked at HIGH severity because Cisco AI
Defense detected a prompt-injection attempt aimed at exfiltrating
customer PII — the email tool would have surfaced the data to an
external recipient.
```

### `"ai_spl"` (Splunk-native, mock-default)

Implementation: `packages/splunkgate_judges/src/splunkgate_judges/foundsec_spl.py`.
Pattern:

```spl
| makeresults
| eval prompt="..."
| ai prompt=prompt provider=Splunk model=foundation-sec-1.1-8b-instruct
| fields explanation
```

This is the canonical "Best Use of Splunk Hosted Models" call shape
when AITK 5.7+ is installed with `provider=Splunk` configured.
**Mock-default** because Trial-tier Splunk Cloud tenants don't reliably
have this entitlement (see ADR-003a). Operators with confirmed access
flip `SPLUNKGATE_USE_MOCK=false`.

## Setup

```bash
# One-time: install Ollama + pull the default model + verify the path.
bash scripts/setup_hosted_models.sh
```

The script is idempotent. To use a different model:

```bash
bash scripts/setup_hosted_models.sh --model foundation-sec:8b
```

Note: `foundation-sec:8b` is **not in the official Ollama library**;
operators must build a Modelfile from the Hugging Face GGUF
distribution. The default `gpt-oss:20b` works out-of-the-box.

## Configuration

In Python:

```python
from pydantic import SecretStr
from splunkgate_mw import Config

cfg = Config(
    ai_defense_api_key=SecretStr("..."),
    foundation_sec_enabled=True,           # enable the explainer
    explainer_backend="ollama",            # was "template" by default
    explainer_model="gpt-oss:20b",         # the Hosted Model tag
    explainer_ollama_url=None,             # → OLLAMA_HOST or localhost
)
```

Via environment:

```bash
export OLLAMA_HOST=http://localhost:11434
# (model + backend are read from Config — env-only fallback is the URL only)
```

## Testing

```bash
# Unit tests (respx-mocked HTTP, no Ollama required):
uv run pytest packages/splunkgate_judges/tests/test_hosted_models.py -v

# LIVE integration test (no mocks, real Ollama):
export RUN_HOSTED_MODELS_LIVE_TESTS=1
uv run pytest packages/splunkgate_judges/tests/test_hosted_models_live.py -v
```

The live test is **gated on `RUN_HOSTED_MODELS_LIVE_TESTS=1`** so CI
skips by default. CI doesn't have a GPU + 13GB model loaded; developers
running locally with Ollama flip the env var to exercise the no-mock
path.

## License compliance

- **gpt-oss-20b** ships under Apache-2.0. Compatible with this repo's
  Apache-2.0 license; no attribution file needed in the binary
  distribution, though crediting OpenAI in `README.md` is good
  citizenship.
- **Foundation-Sec-1.1-8B-Instruct** ships under a Llama-3.1 derivative
  license ("other" on Hugging Face, governed by `NOTICE.md` in the
  model repo). If you swap to Foundation-Sec for production, ship a
  `LICENSE-MODELS.md` containing the upstream NOTICE.md verbatim and
  the "Built with Llama" branding attribution Meta requires.
- **gpt-oss-120b** ships under Apache-2.0 (same terms as gpt-oss-20b).

The Ollama daemon itself is MIT-licensed. SplunkGate calls it over HTTP
only — no Ollama code is linked into our binary distribution.
