"""Structural tests for the SUIT Agent Risk Overview rebuild (story-suit-agent-risk-overview).

D2 = "cockpit." 5 KPI tiles + verdicts-by-label area + rules-by-hour heatmap
+ top agents by BLOCKED + MSJ scaling. Drill-down on chart/heatmap/row click
to verdict_inspector. Live-tick pulse on the BLOCKED KPI is the only motion.

Goal: lock the contract that the new SUIT view ships verbatim Cisco AI
Defense rule names (heatmap Y-axis), unchanged SPL queries (lifted from
the archive), live-tick pulse with prefers-reduced-motion fallback, the
search-lifecycle errback+timeout+try/catch contract, and TSX/JS drift
detection.
"""

from __future__ import annotations

import re
import tarfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_APP_ROOT = _REPO_ROOT / "splunk_apps" / "splunkgate_app"
_SUIT_STATIC = _APP_ROOT / "static" / "splunkgate-suit"
_SUIT_SRC = _APP_ROOT / "src"
_VIEW_XML = _APP_ROOT / "default" / "data" / "ui" / "views" / "agent_risk_overview.xml"
_ARCHIVE = _REPO_ROOT / "docs" / "archive" / "dashboard-studio-v2" / "agent_risk_overview.xml"
_BUNDLE_JS = _SUIT_STATIC / "agent_risk_overview.js"
_BUNDLE_CSS = _SUIT_STATIC / "agent_risk_overview.css"
_DEV_TSX = _SUIT_SRC / "views" / "agent_risk_overview.tsx"

# Shared invariants — every fragment MUST appear in both implementations.
_DRIFT_INVARIANTS = {
    "panel_titles": (
        "SplunkGate — Agent Risk Overview",
        "Verdicts by label, per hour",
        "Rules-by-hour heatmap",
        "Top agents by BLOCKED count",
        "MSJ scaling indicator",
    ),
    "kpi_labels": (
        "Total verdicts",
        "BLOCKED actions",
        "HIGH severity",
        "Distinct agents",
        "Tokens saved",
    ),
    "cisco_rule_names_verbatim": (
        "Code Detection",
        "Harassment",
        "Hate Speech",
        "PCI",
        "PHI",
        "PII",
        "Prompt Injection",
        "Profanity",
        "Sexual Content & Exploitation",
        "Social Division & Polarization",
        "Violence & Public Safety Threats",
    ),
    "spl_query_fragments": (
        "splunkgate_data` | stats count",
        "verdict_label=block | stats count",
        "severity=HIGH",
        "stats dc(agent_id) as agents",
        "sum(tokens_used) as tokens_saved",
        "timechart span=1h count by verdict_label",
        "mvexpand rule | bin _time span=1h",
        "stats count by agent_id | sort -count | head 10",
        'count(eval(severity!="NONE_SEVERITY"))',
    ),
    "lifecycle_markers": (
        "SEARCH_TIMEOUT_MS",
        "Splunk Search SDK failed to load",
        "SearchManager construction failed",
        "PANEL FAILED TO LOAD",
    ),
    "drilldown_url_fragments": ("/app/splunkgate_app/verdict_inspector", "form.input_agent_id"),
}


def test_view_xml_references_suit_bundle() -> None:
    """The view XML is a SUIT bundle, not Dashboard Studio v2 JSON."""
    text = _VIEW_XML.read_text(encoding="utf-8")
    assert "<dashboard" not in text, "Dashboard Studio v2 still in place; SUIT rebuild not applied"
    assert "<view " in text
    assert "splunkgate-suit/agent_risk_overview.js" in text
    assert "splunkgate-suit/tokens.css" in text
    assert "splunkgate-suit/agent_risk_overview.css" in text
    assert 'id="splunkgate-agent-risk"' in text


def test_view_xml_has_no_isvisible_attribute() -> None:
    """isVisible is not a valid <view> attribute (PR #15 lesson)."""
    text = _VIEW_XML.read_text(encoding="utf-8")
    view_tag = re.search(r"<view\b[^>]*>", text, re.DOTALL)
    assert view_tag is not None
    assert "isVisible" not in view_tag.group(0)


def test_archived_dashboard_studio_v2_original() -> None:
    """Rollback artefact: the Dashboard Studio v2 original ships untouched."""
    assert _ARCHIVE.exists()
    text = _ARCHIVE.read_text(encoding="utf-8")
    assert '<dashboard version="2"' in text
    assert "ds_heatmap" in text


def test_built_bundle_committed() -> None:
    """agent_risk_overview.js + agent_risk_overview.css ship in static/."""
    assert _BUNDLE_JS.exists()
    assert _BUNDLE_CSS.exists()


def test_dev_tsx_source_present() -> None:
    """TypeScript/React source-of-truth lives under src/views/."""
    assert _DEV_TSX.exists()


def test_ar_drift_invariants_match_between_js_and_tsx() -> None:
    """Every shared invariant present in BOTH the JS bundle and the TSX source."""
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    tsx = _DEV_TSX.read_text(encoding="utf-8")
    for category, fragments in _DRIFT_INVARIANTS.items():
        for f in fragments:
            assert f in js, f"{category}: missing from JS bundle: {f!r}"
            assert f in tsx, f"{category}: missing from TSX source: {f!r}"


def test_cisco_rule_names_verbatim_in_heatmap_order() -> None:
    """The 11 Cisco AI Defense rule names appear verbatim AND in the exact
    canonical order in both files (the heatmap Y-axis order is examiner-facing)."""
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    tsx = _DEV_TSX.read_text(encoding="utf-8")
    canonical = _DRIFT_INVARIANTS["cisco_rule_names_verbatim"]
    # In JS bundle: the rule array literal.
    js_block = js.split("CISCO_AI_DEFENSE_RULES", 1)[1].split("];", 1)[0]
    for r in canonical:
        assert r in js_block, f"rule missing from JS canonical array: {r!r}"
    # Order check: indices of each rule in the canonical block are monotonic.
    last_idx = -1
    for r in canonical:
        idx = js_block.find(r)
        assert idx > last_idx, f"rule order broken at {r!r} (JS bundle)"
        last_idx = idx
    # TSX block.
    tsx_block = tsx.split("CISCO_AI_DEFENSE_RULES", 1)[1].split("] as const", 1)[0]
    last_idx = -1
    for r in canonical:
        idx = tsx_block.find(r)
        assert idx > last_idx, f"rule order broken at {r!r} (TSX source)"
        last_idx = idx


def test_spl_queries_lifted_verbatim_from_archive() -> None:
    """The 9 SPL data sources are lifted verbatim from the archive."""
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    archive_normalized = _ARCHIVE.read_text(encoding="utf-8").replace('\\"', '"')
    for fragment in _DRIFT_INVARIANTS["spl_query_fragments"]:
        assert fragment in js, f"SPL fragment missing from bundle: {fragment!r}"
        assert fragment in archive_normalized, f"SPL fragment missing from archive: {fragment!r}"


def test_live_tick_animation_present() -> None:
    """The .ar-tick pulse + the @keyframes ar-pulse + prefers-reduced-motion override."""
    css = _BUNDLE_CSS.read_text(encoding="utf-8")
    assert ".ar-tick" in css
    assert "@keyframes ar-pulse" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_blocked_kpi_uses_vermillion_accent() -> None:
    """The BLOCKED KPI tile carries the vermillion accent — only brand-moment cue."""
    css = _BUNDLE_CSS.read_text(encoding="utf-8")
    assert ".ar-kpi-block" in css
    # The vermillion accent comes through var(--accent) or var(--accent-deep);
    # the BLOCKED tile must use one of them as border or color.
    block_section = css.split(".ar-kpi-block", 1)[1].split("@", 1)[0]
    assert "var(--accent" in block_section


def test_search_lifecycle_errback_and_timeout() -> None:
    """F1-style fix from PR #16 carried forward: errback + try/catch + 30s timeout in both files."""
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    tsx = _DEV_TSX.read_text(encoding="utf-8")
    for src in (js, tsx):
        assert "SEARCH_TIMEOUT_MS" in src
        assert "Splunk Search SDK failed to load" in src
        assert "SearchManager construction failed" in src
        assert "cancelled" in src


def test_hard_edged_error_treatment() -> None:
    """Error state has 'PANEL FAILED TO LOAD' header + 3px border so it survives B&W print."""
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    css = _BUNDLE_CSS.read_text(encoding="utf-8")
    tsx = _DEV_TSX.read_text(encoding="utf-8")
    assert "PANEL FAILED TO LOAD" in js
    assert "PANEL FAILED TO LOAD" in tsx
    assert ".ar-state-error-wrap" in css
    assert "border-top: 3px solid" in css


def test_drilldown_links_to_verdict_inspector() -> None:
    """Top-agents row click + chart-click drill-down point at verdict_inspector."""
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    tsx = _DEV_TSX.read_text(encoding="utf-8")
    for src in (js, tsx):
        assert "/app/splunkgate_app/verdict_inspector" in src
        assert "form.input_agent_id" in src


def test_safe_html_escaping_in_bundle() -> None:
    """escapeHtml is defined and applied at innerHTML construction points."""
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    assert "function escapeHtml" in js
    # Spot-check: KPI helper escapes label/value/suffix.
    assert "escapeHtml(value)" in js
    assert "escapeHtml(suffix)" in js


def test_dossier_tokens_used() -> None:
    """The overlay uses Dossier var(--*) tokens, not raw hex outside @media print."""
    css = _BUNDLE_CSS.read_text(encoding="utf-8")
    main_path = css.split("@media print", 1)[0] if "@media print" in css else css
    assert "var(--accent)" in main_path
    assert "var(--paper)" in main_path
    assert "var(--ink)" in main_path
    # Heatmap intensity ramp uses rgba over Dossier accent — confirm rgba is
    # a vermillion ramp, not viridis.
    assert "rgba(188, 58, 38" in css


def test_tarball_includes_agent_risk_bundle() -> None:
    """The tarball ships agent_risk_overview.{js,css} and the new view XML."""
    import os  # noqa: PLC0415
    import subprocess  # noqa: PLC0415

    dist = _REPO_ROOT / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "SKIP_APPINSPECT": "1"}
    try:
        subprocess.run(
            ["bash", str(_REPO_ROOT / "scripts" / "build_splunk_app_tgz.sh")],
            check=True,
            env=env,
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        msg = (
            f"build_splunk_app_tgz.sh failed (rc={exc.returncode})\n"
            f"--- stdout ---\n{exc.stdout}\n"
            f"--- stderr ---\n{exc.stderr}"
        )
        raise AssertionError(msg) from exc
    tgz = next(dist.glob("splunkgate_app-*.tgz"))
    with tarfile.open(tgz, "r:gz") as tar:
        names = tar.getnames()
    top = "splunkgate_app"
    assert f"{top}/static/splunkgate-suit/agent_risk_overview.js" in names
    assert f"{top}/static/splunkgate-suit/agent_risk_overview.css" in names
    assert f"{top}/default/data/ui/views/agent_risk_overview.xml" in names
    # AppInspect rule: src/ stays out.
    src_leaks = [n for n in names if n == f"{top}/src" or n.startswith(f"{top}/src/")]
    assert src_leaks == [], f"src/ leaked into tarball: {src_leaks}"
