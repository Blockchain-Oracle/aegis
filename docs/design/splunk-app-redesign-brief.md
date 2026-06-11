# Splunk app redesign brief — Option B (full SUIT rebuild)

> **Status:** locked. Owner chose Option B (full rebuild of all 3
> operational dashboards) over my recommended Option C (hybrid). Risk
> profile + mitigation documented below.

## What we're shipping

Replace the three Dashboard-Studio-XML operational dashboards in
`splunk_apps/splunkgate_app/default/data/ui/views/` with SUIT (custom
Splunk UI Toolkit) views backed by the **Dossier** design system
(`web/styles/designer/splunkgate-base.css`). The setup wizard
(`splunkgate_setup.xml`) is untouched.

| View | Reason for rebuild |
|---|---|
| `regulator_evidence_pack.xml` | Buyer-facing surface. Strongest visual statement of "this is OUR product." Lowest data-density → cleanest SUIT first-implementation. |
| `agent_risk_overview.xml` | Operator-facing surface. 8 panels (5 KPI tiles + stacked area + heatmap + MSJ scaling line) — the most product-feel. |
| `verdict_inspector.xml` | Forensic surface. Drill-down filter bar + table + detail panel. Demonstrates SOC workflow. |

## Design system source of truth

`web/styles/designer/splunkgate-base.css` — "The Dossier":

- **Palette (PAPER, default)**: `--paper #F1ECE1`, `--ink #1D1A13`,
  vermillion accent `--accent #BC3A26`, severity tints reserved for
  dark product-artifact panels.
- **Palette (DARK)**: warm charcoal `--paper #17140E`, warm cream
  `--ink #F0EADD`, soft vermillion `#E5786A`.
- **Type**: Newsreader (editorial serif headlines), Hanken Grotesk
  (grotesque body), JetBrains Mono (data + code). All three bundled
  locally per AppInspect "no CDN" rule.
- **Radius**: 3px globally. Sharp by default — softness signals
  documentation, not product chrome.
- **Severity tokens** (`--block`, `--med`, `--allow`) used ONLY inside
  dark product artifacts (verdict cards, code panels, terminal
  embeds) — never on the paper layer.

The Brand-Kit-derived tokens port into `splunk_apps/splunkgate_app/src/styles/tokens.css`.

## Track-4 PR layout

1. **PR 15 — `feat/suit-scaffold`** (this PR): scaffold + build
   pipeline integration. Webpack bundle landing at
   `splunk_apps/splunkgate_app/static/splunkgate-suit/main.js`,
   committed so `_pack_tarball.py` survives cruft filtering. Temporary
   `_suit_hello.xml` view confirms the wiring; removed in PR 18.
2. **PR 16 — `feat/suit-evidence-pack`**: `RegulatorEvidencePack.tsx`
   + sub-components. SPL queries lifted verbatim from
   `ds_header_kpis`, `ds_nist_rmf_table`, `ds_eu_article_6_table`,
   `ds_hipaa_safe_harbor`, `ds_pci_dss_11x`, `ds_coverage_footer`,
   `ds_sr_26_2_quote_panel`. Print-to-PDF via `window.print()`.
3. **PR 17 — `feat/suit-agent-risk-overview`**: `AgentRiskOverview.tsx`
   + 8 sub-components (5 KPI tiles, stacked area chart, heatmap,
   top-agents table, MSJ scaling line). Charts via
   `@splunk/react-visualizations`.
4. **PR 18 — `feat/suit-verdict-inspector`**: `VerdictInspector.tsx`
   + filter bar + table + detail panel. Removes the `_suit_hello.xml`
   placeholder. Drops the placeholder from `default/data/ui/nav/default.xml`.

## SPL data layer

All 20 data sources lift verbatim. Field extraction is server-side via
`EVAL-*` directives in `props.conf` (the 2026-06-09 FIELDALIAS fix —
remember `[[aegis_splunk_eval_x_no_chain]]`: EVAL-X reads indexed
fields only, not other EVAL outputs). SUIT components consume
already-extracted fields via Splunk Search SDK calls.

## Risk profile

- **HIGH risk on AppInspect failures.** Custom React Splunk views can
  fail late in the rebuild cycle (rebuild + re-inspect cycle is slow).
  **Mitigation**: every dashboard's original `*.xml` is archived as
  `*.xml.bak` (not packaged in the tarball) so revert is one-line per
  dashboard.
- **Build pipeline complexity.** The webpack bundle must commit to
  `static/splunkgate-suit/` so CI doesn't need a Node toolchain at
  `_pack_tarball.py` time. PR 15 establishes the cruft-filter rules
  (`DEV_CRUFT_PATTERNS` keeps `src/node_modules/` out).
- **Font licensing**: Hanken Grotesk + Newsreader + JetBrains Mono
  are all SIL OFL; bundle locally in `src/assets/fonts/`. Verified
  against AppInspect "no CDN" constraint.

## What's NOT in scope

- The `splunkgate_setup.xml` Simple XML form is the install wizard, not
  a dashboard — not touched.
- Splunkbase artifact signing/upload — owned by EPIC-12.
- Theme toggle (light/dark switch) — locked to PAPER (light) for the
  hackathon submission per memory:feedback_deadline_no_excuse_mediocre
  (no half-finished features).
