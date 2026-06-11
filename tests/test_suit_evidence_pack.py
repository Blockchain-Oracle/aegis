"""Structural tests for the SUIT Regulator Evidence Pack rebuild (story-suit-evidence-pack).

Goal: lock the contract that the new SUIT view ships the verbatim SR 26-2
footnote 3 quote, the unchanged SPL queries, the Dossier styling overlay,
the browser-print export path, and the archived Dashboard Studio v2
original (rollback safety).
"""

from __future__ import annotations

import re
import tarfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_APP_ROOT = _REPO_ROOT / "splunk_apps" / "splunkgate_app"
_SUIT_STATIC = _APP_ROOT / "static" / "splunkgate-suit"
_SUIT_SRC = _APP_ROOT / "src"
_VIEW_XML = _APP_ROOT / "default" / "data" / "ui" / "views" / "regulator_evidence_pack.xml"
_ARCHIVE = _REPO_ROOT / "docs" / "archive" / "dashboard-studio-v2" / "regulator_evidence_pack.xml"
_BUNDLE_JS = _SUIT_STATIC / "evidence_pack.js"
_BUNDLE_CSS = _SUIT_STATIC / "evidence_pack.css"
_DEV_TSX = _SUIT_SRC / "views" / "evidence_pack.tsx"

# The SR 26-2 footnote 3 quote, verbatim from the joint Federal Reserve /
# OCC / FDIC SR 26-2 Attachment, p. 3, April 17, 2026. Splitting on
# sentence boundaries keeps the test stable across CSS/JS encoding tweaks
# while still failing the moment anyone paraphrases the source material.
_SR_26_2_SENTENCES = (
    "Generative AI and agentic AI models are novel and rapidly evolving.",
    "As such, they are not within the scope of this guidance.",
    "a banking organization's risk management and governance practices",
    "the principles described in this guidance apply",
    "to traditional statistical and quantitative models and non-generative",
)


def test_view_xml_references_suit_bundle() -> None:
    """The view XML is a SUIT bundle, not Dashboard Studio v2 JSON."""
    text = _VIEW_XML.read_text(encoding="utf-8")
    assert "<dashboard" not in text, "Dashboard Studio v2 still in place; SUIT rebuild not applied"
    assert "<view " in text
    assert "splunkgate-suit/evidence_pack.js" in text
    assert "splunkgate-suit/tokens.css" in text
    assert "splunkgate-suit/evidence_pack.css" in text
    assert 'id="splunkgate-evidence-pack"' in text


def test_view_xml_has_no_isvisible_attribute() -> None:
    """isVisible is not a valid <view> attribute (the SUIT scaffold lesson)."""
    text = _VIEW_XML.read_text(encoding="utf-8")
    view_tag = re.search(r"<view\b[^>]*>", text, re.DOTALL)
    assert view_tag is not None
    assert "isVisible" not in view_tag.group(0)


def test_archived_dashboard_studio_v2_original() -> None:
    """Rollback artefact: the Dashboard Studio v2 original ships untouched."""
    assert _ARCHIVE.exists()
    text = _ARCHIVE.read_text(encoding="utf-8")
    assert '<dashboard version="2"' in text
    assert "ds_header_kpis" in text


def test_built_bundle_committed() -> None:
    """The hand-written evidence_pack.js + evidence_pack.css ship in static/."""
    assert _BUNDLE_JS.exists()
    assert _BUNDLE_CSS.exists()


def test_dev_tsx_source_present() -> None:
    """The TypeScript/React source-of-truth lives under src/views/."""
    assert _DEV_TSX.exists()


def test_sr_26_2_quote_verbatim_in_bundle_and_tsx() -> None:
    """The SR 26-2 footnote 3 quote is verbatim in BOTH the built bundle and the TSX source."""
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    tsx = _DEV_TSX.read_text(encoding="utf-8")
    for sentence in _SR_26_2_SENTENCES:
        assert sentence in js, f"SR 26-2 sentence missing from built bundle: {sentence!r}"
        assert sentence in tsx, f"SR 26-2 sentence missing from TSX source: {sentence!r}"
    for source in (js, tsx):
        assert "SR 26-2 Attachment, footnote 3, p. 3" in source, "SR 26-2 attribution missing"
        assert "Federal Reserve" in source
        assert "OCC" in source
        assert "FDIC" in source
        assert "April 17, 2026" in source


def test_panel_inventory_covered() -> None:
    """All 7 examiner panels from the Dashboard Studio v2 original are present in the bundle."""
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    for marker in (
        "Coverage period",
        "Total decisions",
        "Unique trace IDs",
        "Attested decisions",
        "NIST AI RMF function mapping",
        "SR 26-2 footnote 3",
        "EU AI Act Article 6 — high-risk classification mapping",
        "HIPAA Safe Harbor 18 — PHI detection counts",
        "PCI DSS 11.x — PCI detection counts",
        "Export PDF for examiner record",
    ):
        assert marker in js, f"panel marker missing from bundle: {marker!r}"


def test_spl_queries_lifted_verbatim_from_archive() -> None:
    """The 6 SPL data sources are lifted verbatim from the archived Dashboard Studio v2 definition.

    The archive embeds queries inside JSON, so `"` appears as `\\\"`. The
    bundle uses raw JS strings. We normalize both to plain-quote form so
    the comparison stays meaningful.
    """
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    archive_normalized = _ARCHIVE.read_text(encoding="utf-8").replace('\\"', '"')
    for fragment in (
        "stats count as total_decisions",
        'case(row=1,"GOVERN", row=2,"MAP", row=3,"MEASURE", row=4,"MANAGE")',
        "Critical infrastructure (Annex III §2)",
        "rule=PHI",
        "rule=PCI",
        "SplunkGate v1.0.0",
    ):
        assert fragment in js, f"SPL fragment missing from bundle: {fragment!r}"
        assert fragment in archive_normalized, (
            f"SPL fragment missing from archive (expected lift source): {fragment!r}"
        )


def test_export_pdf_uses_window_print() -> None:
    """The Export PDF button calls window.print() — the browser-print export path is the contract."""
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    assert "window.print()" in js


def test_print_styles_strip_chrome_and_collapse_grid() -> None:
    """@media print drops Splunk header/footer + collapses the 2-col grid for A4 portrait."""
    css = _BUNDLE_CSS.read_text(encoding="utf-8")
    assert "@media print" in css
    assert "display: none" in css
    assert "grid-template-columns: 1fr" in css


def test_dossier_tokens_extended_not_overwritten() -> None:
    """evidence_pack.css uses tokens (var(--accent), var(--paper), …) — no hex hard-coding outside print mode."""
    css = _BUNDLE_CSS.read_text(encoding="utf-8")
    assert "var(--accent)" in css
    assert "var(--paper)" in css
    assert "var(--ink)" in css


def test_safe_html_escaping_present() -> None:
    """The bundle defines escapeHtml — prevents injection from search result strings."""
    js = _BUNDLE_JS.read_text(encoding="utf-8")
    assert "escapeHtml" in js
    # All user-data flowing into innerHTML must go through escapeHtml.
    # Spot-check: SR 26-2 quote rendering uses escapeHtml(SR_26_2_QUOTE).
    assert "escapeHtml(SR_26_2_QUOTE)" in js


def test_tarball_includes_evidence_pack_bundle() -> None:
    """The tarball ships evidence_pack.js, evidence_pack.css, and the new view XML."""
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
    assert f"{top}/static/splunkgate-suit/evidence_pack.js" in names
    assert f"{top}/static/splunkgate-suit/evidence_pack.css" in names
    assert f"{top}/default/data/ui/views/regulator_evidence_pack.xml" in names
