"""Synthetic corpus loaders (story-eval-01).

Reads the three JSONL files produced by `Synthetic-Data/generate_agent_verdicts.py`
into Pydantic-validated `EvalPrompt` records. The loader does not generate
data — `generate_agent_verdicts.py` is the source of truth — so this file
is safe for §14 production-source greps.

`EvalPrompt` is the shared eval-harness record shape used by every loader
(synthetic, JailbreakBench, AdvBench, Imprompter). Future loaders import
it from `splunkgate_eval` and produce the same shape.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "EvalPrompt",
    "load_benign_control",
    "load_multi_turn_injection",
    "load_tool_call_abuse",
]


PromptCategory = Literal[
    "tool_call_abuse",
    "multi_turn_injection",
    "benign_control",
    "jailbreakbench",
    "advbench",
    "imprompter",
]
VerdictLabel = Literal["ALLOW", "BLOCK", "MODIFY", "REVIEW"]
SeverityLabel = Literal["NONE_SEVERITY", "LOW", "MEDIUM", "HIGH"]


class EvalPrompt(BaseModel):
    """One eval-harness record — shared across every dataset loader."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    category: PromptCategory
    prompt: str = Field(min_length=1)
    expected_verdict: VerdictLabel
    expected_severity: SeverityLabel
    source_citation: str = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def _id_is_uuid_string(cls, value: str) -> str:
        """The synthetic generator emits UUIDv5; bench loaders also normalise to UUID strings."""
        UUID(value)  # raises on malformed
        return value


_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
_CORPUS_DIR: Final[Path] = _REPO_ROOT / "Synthetic-Data" / "jailbreak_corpus"


def _read_jsonl(path: Path) -> list[EvalPrompt]:
    """Read a JSONL file at `path`; validate every line; return the list of records."""
    if not path.exists():
        msg = (
            f"corpus file {path} not found; "
            f"run `python Synthetic-Data/generate_agent_verdicts.py` first"
        )
        raise FileNotFoundError(msg)
    records: list[EvalPrompt] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(EvalPrompt.model_validate_json(line))
    return records


def load_tool_call_abuse() -> list[EvalPrompt]:
    """Return the tool-call-abuse synthetic corpus (≥ 200 records)."""
    return _read_jsonl(_CORPUS_DIR / "tool_call_abuse.jsonl")


def load_multi_turn_injection() -> list[EvalPrompt]:
    """Return the multi-turn MSJ synthetic corpus (≥ 150 records, 4/8/16/32 shots)."""
    return _read_jsonl(_CORPUS_DIR / "multi_turn_injection.jsonl")


def load_benign_control() -> list[EvalPrompt]:
    """Return the benign-control synthetic corpus (≥ 300 records, all ALLOW)."""
    return _read_jsonl(_CORPUS_DIR / "benign_control.jsonl")
