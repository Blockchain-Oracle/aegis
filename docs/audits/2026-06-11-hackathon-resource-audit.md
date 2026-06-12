# Hackathon-resource audit — 2026-06-11

Late-stage cross-reference of the codebase on `main` against the official
Splunk Agentic Ops Hackathon resources (rules + capabilities list) that
Abu surfaced in `instructions.md`. This audit is **research-driven**,
**unbiased**, and quotes sources verbatim where it matters. Where we
improvised earlier in the sprint without ground truth, this audit pulls
that ground truth.

**Submission deadline: 2026-06-15 09:00 PDT (~3.5 days from now).**

---

## 1. Track and bonus-prize alignment

The hackathon has **3 tracks** ($3,000 each + one $7,000 Grand Prize) and
**3 bonus prizes** ($1,000 each). A project can win **one Grand prize +
one bonus prize**.

### Our target

ADR-013 + the original plan target the **Security track** + the **Best
Use of Splunk Developer Tools** bonus prize = $4,000 ceiling.
After this audit we should consider whether the bonus-prize choice still
holds, or whether we can stretch for a second.

### Track fit (verbatim from official rules)

> **Security** — "Build solutions that help security teams detect threats
> faster, investigate incidents more efficiently, and automate security
> workflows using AI and Splunk data"

SplunkGate is a runtime safety net for AI agents → emits verdicts as
Splunk events → SOC consumes via 3 dashboards → ES Risk-Based Alerting
fires on HIGH. Lands cleanly in the Security track.

### Bonus prize fit — verbatim text

> **Best Use of Splunk MCP Server.** Awarded to the team that most
> effectively leverages the Splunk MCP Server to build intelligent,
> agent-driven experiences. This prize recognizes solutions that
> seamlessly connect AI agents to Splunk data, enabling powerful workflows
> such as automated investigation, contextual insights and real-time
> decision making.

> **Best Use of Splunk Hosted Models.** Awarded to the team that
> demonstrates the most impactful use of Splunk-hosted AI models to solve
> real-world problems. This includes leveraging capabilities like anomaly
> detection, forecasting, natural language understanding, etc., to generate
> actionable insights. Winning projects will highlight how hosted models
> can accelerate development, improve accuracy and unlock advanced AI-driven
> experiences without requiring heavy infrastructure.

> **Best Use of Splunk Developer Tools.** Awarded to the team that best
> utilizes Splunk's developer ecosystem to build a high-quality, scalable
> and production-ready solution. This includes effective use of SDKs, App
> Inspect, and other development tools offered through dev.splunk.com to
> ensure best practices in app development, validation and deployment.
> Judges will prioritize clean architecture, ease of use and how well the
> solution aligns with Splunk platform standards.

### Our current eligibility

| Prize | Our match | Confidence |
|---|---|---|
| **Best Use of Splunk Developer Tools** ($1,000) | Splunk Python SDK (`splunklib`, `splunklib.ai`), AppInspect-clean app, CI integration with appinspect, MITRE ATLAS mapping, ES Risk-Based Alerting, Splunkbase-ready .tgz, clean architecture, 93+ structural tests | **HIGH — this remains the strongest match.** |
| **Best Use of Splunk MCP Server** ($1,000) | We expose 4 *agent-safety* tools (score_prompt_injection, judge_tool_call, check_output_leak, audit_trace) via the official `mcp` Python SDK. We document coexistence with Splunkbase app 7931. **But we do NOT use the official Splunk MCP Server.** The prize wording — "leverages **the** Splunk MCP Server" — strongly suggests the official Splunkbase app, not just any MCP server. | **LOW-MEDIUM — wording is ambiguous; without a verifiable integration with the Splunkbase 7931 app, this is a stretch.** |
| **Best Use of Splunk Hosted Models** ($1,000) | **NOTHING is shipping that uses CDTSM, Foundation-Sec, or gpt-oss in production.** All references are in docs/, sprint-status, eval baselines (mocked), and `inspiration/`. The Foundation-Sec stories are DEFERRED per ADR-013. | **VERY LOW — we are effectively not in contention as-is.** |

---

## 2. Ground truth on each capability

### 2.1 Splunk MCP Server (Splunkbase app 7931) — verified

Per <https://help.splunk.com/en/splunk-cloud-platform/mcp-server-for-splunk-platform/1.1/configure-the-splunk-mcp-server>:

- Default capabilities: `mcp_tool_execute` (run tools), `mcp_tool_admin`
  (manage tools + create tokens).
- AI tools become available **only when Splunk AI Assistant is installed**:
  `generate_spl`, `explain_spl`, `optimize_spl`, `ask_splunk_question`.
- Installed as a Splunkbase app on the Search Head / SHC.
- Uses **token-based authentication** today (OAuth is in Controlled
  Availability — not yet GA).

**Implication for SplunkGate**: our `splunkgate_mcp` exposes *agent-safety*
tools — structurally different from the Splunk MCP Server's *data-query*
tools. We are complementary, not competing. The judge looking for "Best
Use of Splunk MCP Server" most likely wants to see the official server
in a client config + a creative workflow on top of it.

### 2.2 Splunk Hosted Models — verified

#### Cisco Deep Time Series Model (CDTSM)

Per <https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/5.7.2/ai-toolkit-models/feature-preview-cisco-deep-time-series-model>:

> "You must be a Splunk Cloud platform customer running AI Toolkit
> version 5.7.x in a supported region to try the preview of the Cisco
> Deep Time Series Model (CDTSM)."

- **Splunk Cloud Platform only**. NOT available on Splunk Enterprise.
- Invocation is **SPL only**: `apply CDTSM <fields> [forecast_k=...] ...`
- Visualization via `forecastviz(...)` macro.
- No SDK / programmatic path documented.

**Implication for SplunkGate**: the hackathon resources tell participants
to download Splunk Enterprise (60-day trial → 6-month developer license).
If a judge installs SplunkGate on Splunk Enterprise, `apply CDTSM` will
produce a "command not found" error. We can **ship the SPL** and document
the requirement, but the demo experience on Splunk Enterprise will be
broken. This is a real constraint, not a SplunkGate bug — but it caps
how aggressively we should push CDTSM.

#### Foundation-Sec-1.1-8B-Instruct

Per <https://huggingface.co/fdtn-ai/Foundation-Sec-1.1-8B-Instruct>:

- Handle: `fdtn-ai/Foundation-Sec-1.1-8B-Instruct`
- 8B parameters, **64k context window**, Llama-3.1 backbone.
- **License: "other" — defers to NOTICE.md.** Not confirmed Apache-2.0.
  Llama-3.1 backbone strongly suggests **Llama 3.1 Community License**
  (Meta) with attribution requirements. Must review NOTICE.md before
  shipping production integration.
- **Local sidecar deployment only** (vLLM, SGLang, Transformers, Ollama,
  llama.cpp). No Splunk hosted endpoint documented. (Despite "Splunk
  Hosted Models" branding in the hackathon resources.)
- HarmBench 94.74% (vs Llama-3.1-8b-Instruct 72.43%).

**Implication for SplunkGate**: shipping Foundation-Sec requires running
inference somewhere — most likely a sidecar container or a local
`ollama` host. Adding it now (3.5 days to deadline) is feasible only as
a NL-explanation layer (e.g. generate the human-readable WHY string from
a verdict), not as a classifier. ADR-003's "Foundation-Sec NEVER
classifies" decision still holds.

#### gpt-oss-120b / gpt-oss-20b

- Apache-2.0 license. Configurable reasoning effort (low/med/high).
- gpt-oss-20b runs in 16GB memory; gpt-oss-120b runs on a single 80GB GPU.

**Implication for SplunkGate**: similar to Foundation-Sec — would need
a sidecar inference host. Mostly relevant for the eval harness (story-eval-04
ships a mock; live integration is not in scope).

### 2.3 Splunk AI capabilities per splunk.com — verified

Per <https://www.splunk.com/en_us/solutions/splunk-artificial-intelligence.html>:

Listed capabilities (verbatim positioning):
1. **Splunk AI Assistant (SAIA)** — "helps teams investigate issues, uncover answers, and take the next best action with confidence"
2. **Splunk AI Toolkit** — "Build, test, and deploy custom AI"
3. **Splunk MCP Server** — "Connect AI to Splunk data securely"
4. **AI Canvas** — collaborative investigation hub (NEW — not mentioned in the hackathon resources Abu shared!)

**Notable absences** on the official AI page that the hackathon page DOES
mention:
- "AI for Splunk Apps / Python SDK AI" — the hackathon resources position
  this as a capability; splunk.com doesn't list it as a top-level AI
  capability. It's the **Splunk Python SDK + AI for Splunk Apps** which
  sits one layer down (developer tools).

**Implication for SplunkGate**: our primary integration with Splunk is
via the **Splunk Python SDK** (`splunklib`, `splunklib.ai`). This is
real, valid, and well-aligned with "Best Use of Splunk Developer Tools."

---

## 3. Codebase reality check

### What we actually ship (verified by Grep on `main`)

| Surface | What it uses | Splunk capability it maps to |
|---|---|---|
| `splunkgate_core` | `splunklib`-typed verdict primitives | Splunk Python SDK |
| `splunkgate_mw` | `splunklib.ai` middleware (4 layers: tool / subagent / model / agent) | **AI for Splunk Apps / Python SDK AI** ✅ |
| `splunkgate_judges` | Cisco AI Defense client (tenacity retry, circuit breaker, mock) | External Cisco AI service (not a Splunk capability per se) |
| `splunkgate_mcp` | Official `mcp` Python SDK; exposes 4 agent-safety tools via stdio + HTTP | **MCP protocol** (NOT the official Splunk MCP Server) |
| `splunkgate_app` | AppInspect-clean Splunkbase-ready `.tgz`; HEC events; ES Risk-Based Alerting; 3 SUIT dashboards on Dossier system | **Splunk Developer Tools** + **App Inspect** ✅ |
| DefenseClaw integration | Config-delta docs + docker-compose example | External Apache-2.0 OSS gateway |

### What is NOT in production code today

- ❌ No `apply CDTSM` SPL in any view XML.
- ❌ No Foundation-Sec inference call (deferred per ADR-003).
- ❌ No gpt-oss runtime call.
- ❌ No integration with the official Splunkbase 7931 Splunk MCP Server
  (we coexist via separate client config, we don't query through it).
- ❌ No SAIA integration (story-demo-02 plans a screen-only SAIA moment;
  no code integration today).

### What IS being worked on (per Abu's message)

- 🔧 `architecture_diagram.(md|pdf|png)` at repo root — in progress.
- 🔧 Demo video — in progress (story-demo-01 + story-demo-02).

These two are submission-mandatory per the official rules; flagging
only so the audit is complete, not as new findings.

---

## 4. Gap analysis ranked by submission impact

### Stage One (pass/fail) gates

> "The first stage will determine via pass/fail whether the ideas meet a
> baseline level of viability, in that the Project reasonably fits the
> theme and reasonably applies the required APIs/SDKs featured in the
> Hackathon."

We pass Stage One on the strength of:
- Splunk Python SDK (`splunklib`, `splunklib.ai`)
- AppInspect-clean Splunk app
- HEC event emission
- Security track theme fit

**Stage One verdict: PASS (assuming the architecture diagram + demo video
land before the deadline, which Abu confirmed are in progress).**

### Stage Two (4 equally-weighted criteria)

1. **Technological Implementation** — strong. ~120 PRs through full review
   fleet, 93+ structural tests, AppInspect-clean, deterministic builds.
2. **Design** — strong (Dossier SUIT rebuild on 3 dashboards, brand-kit
   coherent, Playwright-verified).
3. **Potential Impact** — defensible (real regulatory framing: NIST AI
   RMF, SR 26-2, EU AI Act Article 6).
4. **Quality of the Idea** — defensible (4-surface approach, runtime
   safety net + audit trail — narrower than "yet another AI dashboard").

### Bonus-prize gap: Hosted Models ($1,000)

**The biggest unforced miss in our positioning.** We have ZERO production
code using a Splunk Hosted Model. Even the eval baseline for gpt-oss is
mocked. Foundation-Sec is explicitly DEFERRED per ADR-003.

**Realistic recovery options (ranked by effort vs payoff)**:

| Option | Effort | Risk | Payoff |
|---|---|---|---|
| **A. Add CDTSM forecast dashboard** to the Splunk app (forecast block-rate trend or HIGH-severity rule incidence) | 4–8 hours | Demo broken on Splunk Enterprise (judges may not have Splunk Cloud) | Direct match to "forecasting" in the prize criteria |
| **B. Add a local Foundation-Sec sidecar** as the verdict explainer (NL-only, not a classifier — ADR-003 still holds) | 12–18 hours | Llama 3.1 license review needed; needs a working inference host | Direct match to "natural language understanding" in the prize criteria |
| **C. Add SAIA NL→SPL demo moment** showing a SOC analyst asking SAIA to write a SplunkGate query | 6–10 hours | Requires SAIA installed in demo tenant (already in our README) | Demonstrates SAIA, not Hosted Models directly — partial credit at best |
| **D. Accept the gap.** Stay focused on the Developer Tools bonus prize, ship the architecture diagram + demo polish | 0 hours | Forfeit Hosted Models bonus | Predictable; preserves Developer Tools chance |

### Bonus-prize gap: Splunk MCP Server ($1,000)

Wording-ambiguous. Two readings:
- **Strict reading**: "the Splunk MCP Server" = the Splunkbase 7931 app
  specifically. Without integrating, we don't qualify.
- **Loose reading**: any MCP server in the Splunk ecosystem. We qualify
  by virtue of running an MCP server with Splunk-emitted events.

**Cheap recovery option**: install Splunkbase 7931 in our demo tenant
and document a Claude Desktop config that lists BOTH servers
(`splunkgate-mcp` for safety + `splunk-mcp-server` for data). Tell the
story of "official Splunk MCP for data, SplunkGate MCP for safety, both
in one agent's tool surface." 4–6 hours.

---

## 5. License sanity check for shipping Hosted Models

If we go Option B (Foundation-Sec sidecar):

- Our repo is **Apache-2.0**.
- Foundation-Sec is **"other" license — NOTICE.md gated**. Almost
  certainly **Llama 3.1 Community License** (Meta) requiring:
  - Attribution to Meta + Llama 3.1
  - "Built with Llama" branding compliance
  - Acceptable Use Policy compliance
  - Distribution of the NOTICE file with derivative works
- We would NOT inline the model weights in our repo (too large + license
  redistribution risk). We would document `huggingface-cli download
  fdtn-ai/Foundation-Sec-1.1-8B-Instruct` as a setup step + ship a
  `LICENSE-MODELS.md` with attribution.

**Action item if Option B is greenlit**: read NOTICE.md before writing
any inference code, not after.

---

## 6. Recommendation

Given **3.5 days** to deadline, my honest read:

### Tier 1 (must-have for Stage One pass)
- ✅ `architecture_diagram.(md|pdf|png)` at repo root — Abu confirmed in progress.
- ✅ Demo video — Abu confirmed in progress.

### Tier 2 (ROI for Stage Two judging)
- **Polish the README hackathon framing** — make the Splunk capabilities
  we leverage immediately visible (Python SDK + MCP + AppInspect + ES
  Risk-Based Alerting + HEC). Currently it's there but buried in the
  4-surface narrative. **Effort: ~1 hour.**
- **Document the "two MCP servers in one client config" story** —
  cheap, defensible, makes the MCP bonus prize less of a stretch.
  **Effort: ~3 hours.** Worth doing.

### Tier 3 (Hosted Models bonus — decide explicitly)

This is the call that needs **Abu's decision**:

- **Option A (CDTSM forecast view)**: low effort, medium risk (cloud-only),
  direct match to "forecasting." If a judge demos on Splunk Cloud, this
  is gold. If they demo on Splunk Enterprise free trial, this is broken.
- **Option B (Foundation-Sec NL explainer)**: medium-high effort, license
  review needed, direct match to "natural language understanding."
  Strongest narrative match to the Foundation-Sec bonus prize.
- **Option C (SAIA NL→SPL moment in demo video)**: medium effort, partial
  credit. SAIA is not technically "Hosted Models" but is one of the
  capabilities the hackathon resources highlight.
- **Option D (accept the gap)**: zero effort, predictable. We're already
  strong on Developer Tools.

**My honest recommendation**: Tier 1 + Tier 2 are non-negotiable. For
Tier 3, **Option C (SAIA NL→SPL demo moment)** has the best
effort-vs-payoff ratio and the lowest tenant-fragility — SAIA is on the
splunk.com AI page as a top-tier capability, the demo recording is
already planned (story-demo-02), and the bonus prize criteria reads
"natural language understanding" which SAIA literally delivers. This
does not technically nail the Hosted Models bonus, but it strengthens
the overall Stage Two score AND keeps the SAIA card visible.

If we want a real shot at Hosted Models bonus, **Option B** is the only
move that maps directly — but the 12–18 hour effort + license review +
inference-host setup is a real cost on a 3.5-day timeline.

### What I'm NOT recommending

- Don't pivot tracks. Security is right.
- Don't replace `splunkgate_mcp` with the official Splunk MCP Server.
  Two MCP servers is the right story.
- Don't add CDTSM if we can't guarantee judges run Splunk Cloud —
  showing a broken `apply CDTSM` command in the demo would be worse
  than not having it.

---

## 7. Sources used (all verified within last 30 minutes)

- <https://help.splunk.com/en/splunk-cloud-platform/mcp-server-for-splunk-platform/1.1/configure-the-splunk-mcp-server> — Splunk MCP Server config + tools list
- <https://www.splunk.com/en_us/solutions/splunk-artificial-intelligence.html> — official Splunk AI capability list
- <https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/5.7.2/ai-toolkit-models/feature-preview-cisco-deep-time-series-model> — CDTSM SPL syntax + cloud-only requirement
- <https://huggingface.co/fdtn-ai/Foundation-Sec-1.1-8B-Instruct> — Foundation-Sec license + deployment options
- `/Users/abu/dev/hackathon/splunk/workspace/aegis/instructions.md` — official rules quotes (judging criteria, prizes, mandatory submission items)
- Codebase `main` @ 9afdf1f — grep + Read of `packages/`, `splunk_apps/`, `docs/sprint-status.yaml`

---

## 8. Open questions for Abu

1. **Hosted Models bonus prize — do we want to chase it?** Pick from A / B / C / D in §6 Tier 3. My recommendation is C (SAIA NL→SPL in demo), but B (Foundation-Sec sidecar) is the only direct match.
2. **MCP bonus prize — Tier 2 "two MCP servers in one client config" story — green-light to write it?** 3 hours of polish, no codebase changes.
3. **Anything you want me to drop from this audit because it's already covered elsewhere?** I want to make sure I'm not re-flagging work you have under way.

This audit's bias was deliberately set to "skeptical of what we
improvised earlier, generous to what the docs actually say." Verbatim
quotes used wherever the wording mattered.
