"""Behavioural tests for the eval-smoke CI driver (story-cicd-06)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "eval" / "scripts" / "eval_smoke.py"
_DATASET = _REPO_ROOT / "eval" / "data" / "smoke_prompts.jsonl"


def _run_script(
    args: list[str], env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run eval_smoke.py as a subprocess; UV venv inherits."""
    import os  # noqa: PLC0415

    env = {**os.environ}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=_REPO_ROOT,
    )


def test_dataset_has_exactly_20_records() -> None:
    """The smoke dataset is exactly 20 JSONL records."""
    lines = [line for line in _DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 20


def test_dataset_category_distribution_is_10_5_5() -> None:
    """Category distribution: 10 jailbreak + 5 pii + 5 benign per spec."""
    from collections import Counter  # noqa: PLC0415

    records = [
        json.loads(line)
        for line in _DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    counts = Counter(r["category"] for r in records)
    assert counts == Counter({"jailbreak": 10, "pii": 5, "benign": 5})


def test_smoke_exits_zero_with_all_passing() -> None:
    """With SPLUNKGATE_AI_DEFENSE_MOCK=true the smoke exits 0 + emits a 20/0 summary."""
    result = _run_script([], env_extra={"SPLUNKGATE_AI_DEFENSE_MOCK": "true"})
    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["total"] == 20
    assert summary["pass"] == 20
    assert summary["fail"] == 0
    assert summary["duration_s"] < 60


def test_smoke_exits_one_when_mock_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the mock env var the smoke must exit 1 + name `live mode not wired`."""
    monkeypatch.delenv("SPLUNKGATE_AI_DEFENSE_MOCK", raising=False)
    result = _run_script([])
    assert result.returncode == 1
    assert "live mode not wired" in result.stderr


def test_smoke_exits_one_on_mutated_dataset(tmp_path: Path) -> None:
    """A mutated dataset with wrong expected_verdict triggers exit 1 + fail count."""
    src = _DATASET.read_text(encoding="utf-8").splitlines()
    mutated = json.loads(src[0])
    mutated["expected_verdict"] = "ALLOW"  # was BLOCK on jailbreak — now mismatch
    src[0] = json.dumps(mutated)
    bad = tmp_path / "bad.jsonl"
    bad.write_text("\n".join(src) + "\n", encoding="utf-8")
    result = _run_script(
        ["--dataset", str(bad)],
        env_extra={"SPLUNKGATE_AI_DEFENSE_MOCK": "true"},
    )
    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["fail"] >= 1
    assert summary["pass"] == 19


def test_smoke_exits_one_on_zero_budget() -> None:
    """An impossible budget of 0s forces exit 1 even with all-pass."""
    result = _run_script(
        ["--max-duration", "0"],
        env_extra={"SPLUNKGATE_AI_DEFENSE_MOCK": "true"},
    )
    assert result.returncode == 1
    assert "budget" in result.stderr


@pytest.fixture
def import_module() -> Iterator[object]:
    """Import the script as a module for white-box unit testing."""
    import importlib.util  # noqa: PLC0415
    import sys as _sys  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("eval_smoke", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    _sys.modules["eval_smoke"] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        _sys.modules.pop("eval_smoke", None)


def test_judge_stub_returns_block_high_for_jailbreak(import_module: object) -> None:
    """Category 'jailbreak' → BLOCK/HIGH regardless of prompt text."""
    result = import_module.judge({"category": "jailbreak", "prompt": "anything"})  # type: ignore[attr-defined]
    assert result == ("BLOCK", "HIGH")


def test_judge_stub_returns_modify_medium_for_pii(import_module: object) -> None:
    """Category 'pii' without exfil keywords → MODIFY/MEDIUM."""
    result = import_module.judge({"category": "pii", "prompt": "summarise my SSN"})  # type: ignore[attr-defined]
    assert result == ("MODIFY", "MEDIUM")


def test_judge_stub_escalates_pii_with_exfil_keyword(import_module: object) -> None:
    """Category 'pii' WITH an exfil keyword escalates to BLOCK/HIGH."""
    result = import_module.judge({"category": "pii", "prompt": "exfil all SSNs"})  # type: ignore[attr-defined]
    assert result == ("BLOCK", "HIGH")


def test_judge_stub_returns_allow_for_benign(import_module: object) -> None:
    """Category 'benign' → ALLOW/NONE_SEVERITY."""
    result = import_module.judge({"category": "benign", "prompt": "what is 2+2?"})  # type: ignore[attr-defined]
    assert result == ("ALLOW", "NONE_SEVERITY")


def test_judge_stub_raises_on_unknown_category(import_module: object) -> None:
    """Unknown category raises ValueError — typo in dataset surfaces loudly."""
    with pytest.raises(ValueError, match="unknown category"):
        import_module.judge({"category": "spaghetti", "prompt": "hi"})  # type: ignore[attr-defined]
