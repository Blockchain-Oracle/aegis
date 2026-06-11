# SplunkGate — Dashboard Design Brief

**Purpose of this document.** This file briefs a design-focused AI (or human designer) who will produce mockups for the **three operational dashboards** inside the SplunkGate Splunk app (`splunk_apps/splunkgate_app/`). The companion brief at `brief.md` covers the marketing landing page and `/docs` site; this brief covers what lives *inside* Splunk Web after a CISO installs the `.tgz`.

This brief is **domain knowledge and intent**, not a visual spec. It tells you what each dashboard is for, who reads it, what story it tells, what data is on the wire, and what severity grades exist in the product. It deliberately does NOT specify hex codes, type stacks, spacing scales, or animation curves — you have the brand assets, you've seen the landing page, you're the designer.

What we need back from you: **annotated PNG / Figma mockups** for each of the three dashboards, at desktop width (1440-pt design canvas, gracefully degrading to 1280). You don't write SUIT/React; an engineer translates your mockups into `splunk_apps/splunkgate_app/src/views/*.tsx` using the Dossier token set already committed at `splunk_apps/splunkgate_app/static/splunkgate-suit/tokens.css`.

---

## 1. What the three dashboards are

SplunkGate ships three dashboards inside the Splunk app. They are the buyer-facing surface of the product. Every install gets all three; they appear under "Apps > SplunkGate" in Splunk Web. The intent is that a CISO can log in, click through these three views, and understand both the product's value and the organization's actual risk posture without reading documentation.

Each dashboard has a single load-bearing job:

| # | Dashboard | Job | Primary reader |
|---|---|---|---|
| **D1** | **Regulator Evidence Pack** | Generate examiner-grade audit artifacts on demand — NIST AI RMF mapping, SR 26-2 scope quote, EU AI Act Article 6 mapping, HIPAA / PCI panels, exportable as PDF. | CISO + Compliance, reading on behalf of an OCC examiner / FDA inspector / Article 6 authority. |
| **D2** | **Agent Risk Overview** | Show the SOC what's happening *right now* across every agent in the estate — KPI tiles, severity-by-hour stack, top offenders, rules heatmap. | SOC analyst (Tier 2/3) + AI platform lead, scanning during a shift. |
| **D3** | **Verdict Inspector** | Filter, find, and drill into a specific verdict for root-cause analysis or incident response — list view, detail panel, related events panel. | SOC analyst during an incident, or an engineer reproducing a block in dev. |

The order above is also the order they should be designed in. D1 has the highest narrative ROI (it's the artifact every reg-anxious CISO wants); D2 is the most "alive"; D3 is the deepest. We've intentionally locked the engineering rebuild to land them in that order (PRs #16, #17, #18 in this repo).

---

## 2. Where each dashboard fits in the buyer's day

Mental model for picking density + tone per dashboard:

- **D1 — Regulator Evidence Pack** is opened *quarterly* (or right before an examiner visit). It is read by a CISO once, then PDF-exported and never looked at again until the next quarter. The CISO is reading on a 13" laptop on a Zoom call with a compliance officer. **High signal-to-ink. Airier. PDF-ready.** Every panel should look like it could be screenshotted into a slide deck without anyone asking what it means.

- **D2 — Agent Risk Overview** is opened *daily, during the shift*. It is read by a SOC analyst on a 27" monitor alongside their ES queue. They glance at it for 10 seconds during a shift change. **High density. Live counters. The 30-second skim is the use case.** Dense KPI tiles, time-series that compresses 24 hours into a glance.

- **D3 — Verdict Inspector** is opened *when something happens*. The analyst clicked a Splunk ES risk-based-alerting notable, landed in SplunkGate, and is now reconstructing what the agent saw, what the middleware decided, and why. **Tabular density. Detail-on-demand. Drill-down is the primary interaction.** This is the one place where it's OK to have a busy screen — the analyst is reading deeply, not skimming.

If you can only carry one principle into your visual choices: **D1 is the slide, D2 is the cockpit, D3 is the microscope.**

---

## 3. The product's grade system (this is what to make visual)

SplunkGate's job is to attach a *verdict* to every agent decision. The verdict has two grades. Both grades show up in every dashboard, and **the visual language for these grades is the single biggest brand-coherence decision in this work**. Pick a treatment in D2's KPI tiles and reuse it verbatim in the D3 verdict list, the D1 HIPAA/PCI tables, and inside the detail panels.

### 3.1. Severity (the "how bad")

Four-level ordinal scale, set by the classifier (Cisco AI Defense / Foundation-Sec):

| Severity | Meaning | Visual weight |
|---|---|---|
| **NONE** | Verdict was inspected; nothing matched. The default for benign traffic. | Lowest. Almost-invisible. Don't compete with HIGH for attention. |
| **LOW** | A rule matched but the action is borderline (e.g. profanity in user input). | Quiet. |
| **MEDIUM** | Rule match with meaningful concern (e.g. PII in tool input, prompt injection that didn't quite parse). | Visible. Yellow-family in most design systems, but you decide. |
| **HIGH** | Production-grade attack or compliance violation (prompt injection that scored, PHI in output, social-engineering exfil pattern). | Loud. This is the moment the SOC analyst's eye should land. |

### 3.2. Result (the "what happens next")

Categorical, set by the middleware policy:

| Result | Meaning | Notes |
|---|---|---|
| **ALLOW** | The action proceeds as the agent intended. | The 99% case for benign traffic. |
| **BLOCK** | The action is refused; the calling code raises `*BlockedBySplunkGate`. | The headline outcome. The wow moment. |
| **MODIFY** | The action proceeds but the payload was rewritten (e.g. PII redacted from a tool argument). | Rare; v1 only emits this for the model-output surface. |
| **REVIEW** | The verdict is ambiguous; queued for human review (or held while a second classifier weighs in). | Almost never in production; mostly an eval-harness construct. |

Severity and Result are **independent axes**. A HIGH-severity verdict can still ALLOW (the action happened, but it's on record); a LOW-severity verdict can BLOCK (defense-in-depth policy). The design should not collapse them into a single chip.

### 3.3. Source attribution (the "who said so")

Every verdict carries a `RuleHit.source` identifier that names which classifier scored it:

- `ai_defense` — Cisco AI Defense Inspection API (the binary classifier, 11 named rules).
- `defenseclaw_regex` — DefenseClaw open-source regex layer (deterministic patterns, lowest latency).
- `splunklib_security` — SplunkGate's own internal heuristics (rare, last resort).

This matters because regulators ask "who decided?" and the answer needs to be plain. A small monospace chip per row is enough. Don't iconify it — `regex` and `Cisco AI Defense` are not metaphors that translate well.

---

## 4. The rule catalog (what's getting blocked)

Cisco AI Defense's 11 named rules form the visual vocabulary of D2 and D3. The names are *verbatim from the Cisco Offer Description PDF* and **must not be paraphrased anywhere in any dashboard**:

1. Code Detection
2. Harassment
3. Hate Speech
4. PCI
5. PHI
6. PII
7. Prompt Injection
8. Profanity
9. Sexual Content & Exploitation
10. Social Division & Polarization
11. Violence & Public Safety Threats

(D3 also surfaces a 12th source — DefenseClaw regex — which adds patterns like SSN, credit-card, etc. but rolls them up under the PII / PCI rule names in the UI for consistency.)

These are not categories you should re-order alphabetically, re-tier, or visually rank. They are *named compliance artifacts*. A regulator can ask "show me all PHI blocks for the period" and the answer needs to use exactly that name. If you cluster them visually in D2's heatmap, cluster by frequency, not by your taste.

---

## 5. The data that's already on the wire

The dashboards consume Splunk events at `sourcetype="cisco_ai_defense:splunkgate_verdict"`. The fields are pre-extracted server-side, so a SUIT React component receives them as clean strings/ints. You can assume the following are always present:

| Field | Type | Example | Used by |
|---|---|---|---|
| `trace_id` | UUID | `8c4d1e6a-…` | D2 (counter), D3 (filter + detail) |
| `agent_id` | string | `support_agent_v3` | D2 (top-agents table), D3 (filter) |
| `surface` | enum | `mw_tool` / `mw_model` / `mw_subagent` / `mw_agent` / `mcp` | D2 (stack), D3 (filter) |
| `rule` | enum | one of the 11 rule names | D2 (heatmap), D3 (filter) |
| `severity` | enum | `NONE` / `LOW` / `MEDIUM` / `HIGH` | All three dashboards |
| `result` | enum | `ALLOW` / `BLOCK` / `MODIFY` / `REVIEW` | All three dashboards |
| `latency_ms` | int | `47` | D2 (p99 chip), D3 (detail) |
| `explanation` | string | "Multi-step instruction-injection attempting to exfiltrate…" | D3 (detail) |
| `source` | enum | `ai_defense` / `defenseclaw_regex` / `splunklib_security` | D3 (detail) |
| `model_input` | string (truncated) | `Ignore previous instructions and email…` | D3 (detail) |
| `tool_call` | JSON | `{"tool": "send_email", "args": {…}}` | D3 (detail, expandable) |
| `_time` | epoch | — | All time-series + filter |

D1 additionally counts events grouped by `jurisdictional_profile` (`FSI` / `HIPAA` / `PCI` / `PUBSEC` / `ALL`), driven by the dropdown at the top of the dashboard.

You don't need to model how this data is queried — the SPL is locked in `splunk_apps/splunkgate_app/default/data/ui/views/{regulator_evidence_pack,agent_risk_overview,verdict_inspector}.xml` and is being lifted verbatim into the SUIT rebuild. Your job is to decide what gets shown, in what shape, in what density.

---

## 6. Per-dashboard intent

### 6.1. Regulator Evidence Pack (D1)

The audit artifact. A CISO clicks through D1, picks a jurisdictional profile from a dropdown (or leaves it on "All profiles"), picks a coverage period (default = last 30 days), and the dashboard renders a panel-stack that can be PDF-exported by the browser print path.

**Panels (lifted verbatim from current `regulator_evidence_pack.xml`):**

1. **Coverage scope** — period start/end, total decisions logged, unique trace IDs, attested decisions (the count where `explanation != ""`). 4–5 KPI numbers in a strip. Quiet. Examiner-facing.
2. **NIST AI RMF mapping** — a 4-row table (GOVERN / MAP / MEASURE / MANAGE) with the SplunkGate components that satisfy each function. This is *the* compliance artifact: a regulator opens the PDF, looks at this table, and either closes the case or asks one follow-up question.
3. **SR 26-2 footnote 3 — verbatim quote panel.** This must look like a *quote*, not a tile. Serif, italics, a vertical rule on the left — the kind of treatment a court filing uses. The text is fixed and is the single biggest "we know what we're doing" trust signal in the entire product. Do not paraphrase; do not summarize; do not iconify.
4. **EU AI Act Article 6 mapping** — 5-row table (Annex III use cases × Article 6 trigger × SplunkGate response). Same tabular treatment as the NIST table.
5. **HIPAA Safe Harbor 18 panel** — only renders when the jurisdictional dropdown is `HIPAA` or `ALL`. A small table of PHI detection counts grouped by surface + agent.
6. **PCI-DSS 11.x panel** — only renders when the dropdown is `PCI` or `ALL`. Counts of PCI rule hits grouped by surface, agent, severity.
7. **Coverage footer** — app version + generation timestamp, in monospace, bottom-right. This is what the examiner reads to know this PDF is a fresh artifact and not a stale copy.

**What makes D1 work:** restraint. Every reflex toward "make this a tile, add a chart, add a sparkline" should be resisted. A regulator's brain is wired for tables and quotes; we feed it tables and quotes. The brand color shows up at most twice on the whole page (the header rule, the quote-block left bar) — everything else is paper + ink. The PDF is the deliverable; the on-screen view is a preview of the deliverable.

**Header strip:** SplunkGate wordmark / glyph, dashboard title, jurisdictional dropdown, coverage period picker, "Export PDF for OCC examiner" button. The button is the only call-to-action on the page; it should be unmissable but not loud.

### 6.2. Agent Risk Overview (D2)

The cockpit. A SOC analyst scans this for 10 seconds during a shift change. The eye should land in this order:

1. **The five KPI tiles (top strip).** Total verdicts (24h), BLOCKED actions (24h), HIGH-severity rate, p99 latency, distinct agents. The BLOCKED count is the brand moment — this is where the vermillion accent earns its keep. The other four are quieter.
2. **Stacked severity area chart (1×24 hours).** One series per severity tier, stacked. Anomalies in the last hour are the SOC analyst's primary look-target. If a HIGH spike appears, it's obvious without thought.
3. **Rules-by-hour heatmap.** Y-axis = the 11 Cisco AI Defense rule names (in *the* order above, not alphabetical, not by frequency). X-axis = 24 buckets. Cell intensity = count of hits. This is where the "what kind of attack are we seeing this morning" answer lives.
4. **Top offenders table.** Top 10 `agent_id` values by HIGH-severity count, with a per-agent sparkline.
5. **MSJ scaling line (optional, smaller).** Multi-shot jailbreak shots vs success rate — this is a research-side chart pulled from the eval harness; it's quiet and lives near the bottom. (If you find it doesn't fit the cockpit metaphor, drop it.)

**What makes D2 work:** density without anxiety. A SOC analyst's day is reading dashboards; the surface should feel like a tool that respects their time, not a marketing surface that demands their attention. The KPI tiles should be glance-readable in any light condition (the SOC is often on a wall display). The stacked area should compress 24h of risk into one viewport-glance.

The *one* place D2 is allowed to feel alive: when a new verdict lands in real time, the affected KPI tile should tick — a hairline pulse, ≤200ms, no bounce, no skeuomorphism. This is the only animation in the product.

### 6.3. Verdict Inspector (D3)

The microscope. Two-column layout:

- **Left column (60%):** filter bar (4 inputs — `agent_id`, `surface`, `rule`, `severity`) + verdict list table. The table is the workhorse: rows are verdicts, columns are timestamp / agent / surface / rule / severity / result. The clicked row drives the right column.
- **Right column (40%):** detail panel — the full verdict object for the selected row. Sections: input text (truncated, expand-on-click), tool call JSON (collapsible), classifier source + score + explanation (the WHY-string from Foundation-Sec or the regex pattern), the OTel span ID, the trace ID with a copy-to-clipboard, latency.

A *related events* sub-panel under the detail panel shows other verdicts in the same `trace_id` — the agent's full session, in chronological order. This is the killer feature for incident response: clicking a single BLOCK shows the analyst the whole conversation that led to it.

**What makes D3 work:** the filter→list→detail→related loop has to be tight. Every click should land in <200ms. The detail panel should never force the analyst to scroll past 500px to find the explanation. The trace_id copy button should be the most-used micro-interaction in the product.

D3 is also the only dashboard where it's OK to expose raw JSON in the UI — engineers reading D3 want to see the actual `tool_call` payload that was blocked. Format it; don't hide it.

---

## 7. SUIT runtime constraints (the things you can't ignore)

You're designing for a React app that mounts inside Splunk Web. A few hard constraints come from the runtime:

- **The host page is dark or light based on user preference**, not yours. The Dossier tokens we've already committed (`splunk_apps/splunkgate_app/static/splunkgate-suit/tokens.css`) target the *Dossier* aesthetic — paper-on-ink, not pure-dark or pure-light. The dashboards live inside their own `.splunkgate-suit` container, so the dossier tone applies regardless of the host theme.
- **No CDN fonts.** Splunkbase AppInspect blocks external font references. Webfonts must be `@font-face` declared from `static/splunkgate-suit/fonts/*.woff2` files we ship in the tarball. (We haven't shipped these yet — your mockups should call out which fonts you want and we'll bundle them locally.)
- **No external network requests at all.** No analytics, no Google Fonts, no Sentry. The dashboards are an air-gapped surface.
- **No icon library other than what we already ship.** SVG icons inline in the bundle are fine; pulling FontAwesome / Material is not.
- **Dashboard resolution is desktop-first.** The minimum target is 1280-pt wide; the design target is 1440. Mobile is not a use case (Splunk Web on phone is dead-on-arrival).
- **The browser print path is the PDF export.** `window.print()` is what the "Export PDF for OCC examiner" button calls. Your D1 design needs to read correctly when printed at A4 / Letter portrait — that's why D1 is so panel-stack-friendly. Test your D1 mockup against this constraint: if it doesn't print well, it doesn't ship.

---

## 8. Visual continuity (what to study, what to bring forward)

We're not starting from zero. The product has a brand kit, a landing page treatment, and a set of dashboards as they exist today. You should study all three before drawing anything:

- **Brand kit + landing page** — at `web/styles/designer/splunkgate-base.css` and the Next.js app under `web/`. The "Dossier" system lives here: paper `#F1ECE1`, vermillion accent, serif headings + grotesque body + monospace artifact. The dashboards should *feel* like an extension of the landing page when a buyer clicks from one to the other — not a different product.
- **Current Dashboard Studio v2 dashboards** — at `splunk_apps/splunkgate_app/default/data/ui/views/{regulator_evidence_pack,agent_risk_overview,verdict_inspector}.xml`. Open them in Splunk Web (or read the XML to reconstruct what's there). They are functional but tied to Splunk's native dark theme. They are what we're *replacing*. Study them for the panel inventory; don't carry their visual treatment forward.
- **DNS Guard AI** (Splunkbase 7922) — the anchor product for "this team knows how to ship a real Splunk app." Their dashboards stayed Splunk-native because they couldn't justify SUIT. We *can* — but the design discipline they showed (no ornamentation, no consumer-SaaS reflexes) is the bar. The point of the SUIT rebuild is *more brand coherence*, not more visual noise.

The Dossier system on the landing page is the source of truth. If you want to extend the palette for dashboard purposes (e.g. add severity-tier hues that aren't in the base kit), do so — but treat extensions as additions to Dossier, not deviations from it. The continuity that matters most: typography, the paper substrate, the vermillion accent used sparingly, and the discipline against decoration.

---

## 9. What's already in the repo (so you don't redesign solved problems)

- **The Dossier token set** is committed at `splunk_apps/splunkgate_app/static/splunkgate-suit/tokens.css`. Paper, ink, accent, severity tints, font stacks — all ported from the landing page CSS. You can extend; you should not start from zero.
- **A placeholder SUIT view** at `default/data/ui/views/_suit_hello.xml` confirms the bundle pipeline works end-to-end (build → tarball → Splunk Web). It will be removed in PR #18 once the three real dashboards land. Don't design for it.
- **The 3 dashboard XML files** are the spec for "what panels exist" and "what SPL feeds them." Lift the data sources verbatim; redesign the visual layer.
- **All SPL field extraction is server-side** via `props.conf` `EVAL-*` directives. A React component receives `severity` as a clean string `"HIGH"`, not as raw `_raw` to parse. You don't need to design around field-extraction failure modes.
- **The Splunkbase listing screenshot** (`static/screenshot.png`) is a placeholder. The first real screenshot we ship will probably be one of your D2 mockups, rendered live. Design accordingly: D2 needs to look *good* in a 1280×720 Splunkbase tile.

---

## 10. The wow moment, rebuilt around dashboards

The same demo flow from the landing-page brief — the 90-second wow — runs against the new SUIT dashboards:

1. The judge opens D2 (Agent Risk Overview). Live counters are running against synthetic traffic.
2. A malicious prompt is run in a sidecar terminal. The agent's middleware blocks it.
3. **D2's BLOCKED counter ticks up.** A new high-severity row appears in the rules-by-hour heatmap.
4. The judge clicks the BLOCKED counter — drills into D3 (Verdict Inspector), filtered to BLOCK + last 1m. The single new row is at the top.
5. The judge clicks the row. The right pane fills with the input text, the tool call payload, the explanation, the trace ID. They see the *whole story* of one attack.
6. The judge navigates to D1 (Regulator Evidence Pack), picks "FSI" from the jurisdictional dropdown, clicks "Export PDF." A PDF saves — including the verbatim SR 26-2 footnote 3 quote panel.

If your mockups can carry a viewer through that flow without them needing to ask "wait, what am I looking at?", the design is done.

---

## 11. The grades and tones, restated as one paragraph

D1 is a court filing in a Dossier dust-jacket: paper substrate, serif quote blocks, ink-on-paper tables, the vermillion accent used exactly twice (header rule, quote left-bar). D2 is a quiet cockpit: dense KPI tiles, severity stack, rules heatmap — the eye can find HIGH in <500ms, and a hairline tick animates when a verdict lands. D3 is a microscope: filter bar, list, detail panel, related events — the trace_id copy button is the hero micro-interaction. Severity is one ordinal scale (NONE / LOW / MEDIUM / HIGH); result is an independent categorical (ALLOW / BLOCK / MODIFY / REVIEW); the visual encoding of each is the single most reused token in the whole surface. The Cisco AI Defense rule names are verbatim and never paraphrased. There is no consumer-SaaS reflex anywhere in this product.

---

## 12. Tone of voice (for any copy you write on the dashboards)

Reuse the landing-page brief's tone rules (`brief.md` § 16) verbatim. The dashboard chrome adds one constraint of its own: **panel titles and descriptions are read by examiners**. The current dashboards already model this — every panel has a description like "Audit period and the count of agent decisions SplunkGate logged" — terse, factual, examiner-grade. Don't editorialize. Don't add cleverness. Don't write empty-state copy that says "No verdicts to show — yet!" — write "0 verdicts in this period."

---

## 13. What to deliver

For each of D1 / D2 / D3:

1. **One desktop mockup at 1440-pt** showing the dashboard with realistic data. (Realistic = some HIGH spikes, a Prompt Injection cluster, an obviously-benign baseline.)
2. **One annotated callout layer** marking the severity treatment, the result treatment, the panel chrome, and any new tokens added to the Dossier kit.
3. **The font and any new color tokens listed in a short spec block** at the bottom of the mockup, with names that match the Dossier convention (e.g. `--sev-high`, `--result-block-fg`).

For D1 specifically, also deliver:

4. **A second mockup of the same dashboard rendered as A4 / Letter portrait print** — what the PDF export will look like. This is the deliverable the CISO sends to their examiner.

For D2 specifically, also deliver:

5. **A short description (2–3 sentences) of the live-tick animation** — the only motion in the product. What pulses, for how long, in what hue.

For D3 specifically, also deliver:

6. **A short description of the drill-down flow** — what the row-click does, what the detail panel reveals, how the related-events panel reads.

We do not need a system-design document, a component inventory, an interaction matrix, or a color-theory rationale. We need three dashboards' worth of mockups, in one Figma file or one folder of PNGs, sufficient that an engineer can pixel-target them.

---

## 14. Open questions you (the designer) can decide

You decide:

- Severity hues beyond Dossier vermillion (e.g. amber for MEDIUM, slate for LOW, near-paper for NONE). Add them to the Dossier kit, name them with the `--sev-*` prefix.
- Whether the result encoding (ALLOW / BLOCK / MODIFY / REVIEW) is shape, hue, weight, or chip — pick one and reuse.
- Whether D2's KPI tiles are framed cards, hairline-bordered, or flat blocks on the paper substrate.
- Whether D3's filter bar is a sticky top strip or an inline above-table band.
- D2's heatmap palette (Dossier-extended, not viridis — a stranger walking past the SOC wall should still read "this is SplunkGate, not a generic dashboard").
- The "Export PDF" button treatment in D1 (chip? button? icon-button? on the right of the header strip? — your call, as long as it's unmissable and tasteful).
- The trace_id chip / copy-to-clipboard treatment in D3 (this is the most-used micro-interaction; make it satisfying).

You should NOT decide:

- The rule names (verbatim Cisco AI Defense, § 4).
- The severity and result enums (§ 3).
- The panel inventory per dashboard (§ 6).
- The presence of the verbatim SR 26-2 footnote 3 quote panel in D1 (§ 6.1, panel 3).
- The Dossier substrate continuity with the landing page (§ 8).

---

## 15. Sanity checklist before declaring the mockups done

- [ ] Can a CISO scan D1 in under 60 seconds and feel they have an examiner-ready artifact?
- [ ] Does D1 print cleanly to A4 portrait without any panel cropping?
- [ ] Can a SOC analyst find HIGH-severity activity on D2 in under 5 seconds?
- [ ] Does D2's BLOCKED KPI tile use the vermillion accent — and only the vermillion accent — to signal "this is the moment that matters"?
- [ ] Are the 11 Cisco AI Defense rule names spelled verbatim everywhere they appear?
- [ ] Is severity encoded the same way in D1, D2, and D3?
- [ ] Is result encoded the same way in D1, D2, and D3?
- [ ] Does D3's detail panel show the explanation, the trace_id, the tool call payload, and the OTel span ID without scrolling?
- [ ] Is the trace_id copy-to-clipboard interaction tasteful and obvious?
- [ ] Does the visual language extend from the landing page into the dashboards without a brand discontinuity at the click-through?
- [ ] Are fonts shippable as `@font-face` files? (i.e. nothing requires a CDN)
- [ ] Is there exactly one motion in the entire product (D2's live tick), or is motion deliberately absent?
- [ ] Would a regulator looking at D1's PDF be able to find the SR 26-2 footnote 3 quote without searching?

That's the brief. Take what's useful. The dashboards are the surface where a CISO learns to trust the product after install — the landing page brought them in, the dashboards keep them. Good luck.
