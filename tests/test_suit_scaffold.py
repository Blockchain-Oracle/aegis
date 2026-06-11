"""Structural tests for the SUIT scaffold (story-suit-scaffold)."""

from __future__ import annotations

import tarfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_APP_ROOT = _REPO_ROOT / "splunk_apps" / "splunkgate_app"
_SUIT_STATIC = _APP_ROOT / "static" / "splunkgate-suit"
_SUIT_SRC = _APP_ROOT / "src"


def test_built_bundle_committed() -> None:
    """The hand-written `hello.js` placeholder bundle ships in static/."""
    assert (_SUIT_STATIC / "hello.js").exists()
    assert (_SUIT_STATIC / "tokens.css").exists()


def test_dev_source_present() -> None:
    """The webpack/TypeScript scaffold lives under src/ for the next 3 PRs."""
    assert (_SUIT_SRC / "package.json").exists()
    assert (_SUIT_SRC / "webpack.config.js").exists()
    assert (_SUIT_SRC / "tsconfig.json").exists()
    assert (_SUIT_SRC / "views" / "hello.tsx").exists()


def test_hello_view_xml_present() -> None:
    """`_suit_hello.xml` view references the static bundle."""
    view = _APP_ROOT / "default" / "data" / "ui" / "views" / "_suit_hello.xml"
    assert view.exists()
    text = view.read_text(encoding="utf-8")
    assert "splunkgate-suit/hello.js" in text
    assert "splunkgate-suit/tokens.css" in text


def test_brand_kit_tokens_ported() -> None:
    """The Dossier palette (`#F1ECE1` paper, `#BC3A26` vermillion accent) is in the bundle CSS."""
    css = (_SUIT_STATIC / "tokens.css").read_text(encoding="utf-8")
    assert "#F1ECE1" in css  # --paper
    assert "#BC3A26" in css  # --accent
    assert "Newsreader" in css
    assert "Hanken Grotesk" in css
    assert "JetBrains Mono" in css


def test_tarball_excludes_src_includes_static() -> None:
    """`_pack_tarball.py` cruft filter keeps src/ out and static/splunkgate-suit/ in."""
    import os  # noqa: PLC0415
    import subprocess  # noqa: PLC0415

    dist = _REPO_ROOT / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "SKIP_APPINSPECT": "1"}
    subprocess.run(
        ["bash", str(_REPO_ROOT / "scripts" / "build_splunk_app_tgz.sh")],
        check=True,
        env=env,
        cwd=_REPO_ROOT,
        capture_output=True,
    )
    tgz = next(dist.glob("splunkgate_app-*.tgz"))
    with tarfile.open(tgz, "r:gz") as tar:
        names = tar.getnames()
    src_entries = [n for n in names if "/src/" in n or n.endswith("/src")]
    assert src_entries == [], f"src/ leaked into tarball: {src_entries}"
    suit_entries = [n for n in names if "splunkgate-suit/" in n]
    assert any(n.endswith("hello.js") for n in suit_entries)
    assert any(n.endswith("tokens.css") for n in suit_entries)
    appinspect_dirt = [
        n for n in names if n.endswith((".appinspect.warnings.md", ".appinspect.manualcheck.yaml"))
    ]
    assert appinspect_dirt == [], f"appinspect dirt in tarball: {appinspect_dirt}"
