# Story — Template-based verdict explainer (v1 of EPIC-05)

**ID:** story-explainer-01-template-based-verdict-explainer
**Epic:** EPIC-05 — Verdict explainer (template v1, Foundation-Sec future)
**Depends on:** story-core-01-verdict-pydantic-types
**Estimate:** ~1h (~30 LOC src + ~60 LOC tests)
**Status:** PENDING
**Added:** 2026-06-05 (per ADR-013 — replaces deferred Foundation-Sec stories foundsec-02 + foundsec-03)

---

## Why this story exists (read ADR-013 first)

ADR-013 deferred the Foundation-Sec invocation stories because Splunk Hosted Models access is undocumented for Trial-tier Cloud tenants (confirmed via live Playwright probe + AITK 5.7.4 official docs + Splunk Feb 18 2026 launch blog). The Verdict shape (`packages/aegis_core/src/aegis_core/verdict.py`) has an `explanation: str | None` field that the dashboards, regulator-evidence-pack PDF, and demo video all surface. Something has to populate it.

This story ships a **deterministic, template-based explainer** that:
- Takes a `VerdictContext` (the same input shape the Foundation-Sec story would have taken)
- Returns a human-readable explanation string built from the verdict's `verdict`, `severity`, `rules`, and `redacted_text` fields
- Has **zero external dependencies** (no model inference, no HTTP, no SPL)
- Preserves the ADR-003 invariant (explainer-only, never classifier)
- Is structurally swappable for the future Foundation-Sec implementation: same function signature, same output type

When Splunk Slack confirms the Hosted Models access path, replacing this with a real Foundation-Sec call is a one-file swap inside `aegis_judges/explainer.py`.

---

## File modification map

- `packages/aegis_judges/src/aegis_judges/explainer.py` — NEW — ~30 LOC. Single module containing `explain_verdict(ctx: VerdictContext) -> str`. No I/O, no async, no external deps. Pure function over `aegis_core` types.
- `packages/aegis_judges/src/aegis_judges/__init__.py` — UPDATE — export `explain_verdict` so `from aegis_judges import explain_verdict` works.
- `packages/aegis_judges/tests/test_explainer.py` — NEW — ~60 LOC. Behavioral tests for every branch.

---

## Function shape

```python
from aegis_core import VerdictContext

def explain_verdict(ctx: VerdictContext) -> str:
    """Return a human-readable explanation string for a Verdict.

    Deterministic and dependency-free. Replaceable with a Foundation-Sec
    call when Splunk Hosted Models access is unblocked (see ADR-013).

    Invariant: this function NEVER returns a verdict label or severity —
    only a free-text WHY-string for human consumption. Per ADR-003,
    Foundation-Sec (and any successor explainer) is explainer-only.
    """
```

The implementation composes a short paragraph from `ctx.verdict`, `ctx.severity`, `ctx.rules` (rule names + sources), and optional `ctx.redacted_text` excerpt. No more than ~200 characters per typical input.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a VerdictContext with verdict=BLOCK, severity=HIGH, rules=[RuleHit(rule="Prompt Injection", confidence=1.0, source="ai_defense")]
When  explain_verdict(ctx) is called
Then  the returned string contains "Prompt Injection" AND "BLOCK" AND "HIGH"
And   the string does NOT contain literal None or null

Given a VerdictContext with verdict=ALLOW, severity=NONE_SEVERITY, rules=[]
When  explain_verdict(ctx) is called
Then  the returned string is non-empty
And   contains the word "ALLOW" or "no rules" or "safe"

Given a VerdictContext with multiple rules from different sources
When  explain_verdict(ctx) is called
Then  every rule name appears in the output exactly once
And   the source for each rule is preserved (e.g., "ai_defense" or "splunklib_security")

Given two distinct VerdictContext instances with identical field values
When  explain_verdict is called on both
Then  the two output strings are byte-equal (determinism — no random / timestamp / process-state input)

Given a VerdictContext with redacted_text="[REDACTED PII]"
When  explain_verdict(ctx) is called
Then  the output references the redaction but does NOT inline raw PII patterns

Given the test file
When  `uv run pytest packages/aegis_judges/tests/test_explainer.py -v` runs
Then  ≥ 5 tests pass and 0 fail

Given the src file
When  `uv run mypy --strict packages/aegis_judges/src/aegis_judges/explainer.py` runs
Then  exit code is 0

Given the src file
When  `wc -l packages/aegis_judges/src/aegis_judges/explainer.py` runs
Then  the line count is ≤ 60 (well under the 400 cap)
```

---

## Shell verification

```bash
cd packages/aegis_judges
uv run pytest tests/test_explainer.py -v 2>&1 | grep -cE "PASSED" # must output >= 5
uv run mypy --strict -p aegis_judges                                # must exit 0
test "$(wc -l < src/aegis_judges/explainer.py)" -le 60 || exit 1
echo OK
```

---

## Notes for coding agent

- **No HTTP, no async, no model inference.** This is a pure, side-effect-free function. Tests do not need `respx` or `pytest-asyncio`.
- The explainer **does not classify**. It composes a string from already-decided verdict fields. The classification (BLOCK / ALLOW / MODIFY) comes from `pre_inference_scan` in `aegis_mw/model_middleware.py` and the Cisco AI Defense client; this story only renders the result.
- Per ADR-003, `RuleHit.source` is `Literal["ai_defense", "defenseclaw_regex", "splunklib_security"]`. The explainer must surface the source verbatim in the output string so the reader knows which evaluator fired.
- **Future swap point:** when Splunk Slack confirms Hosted Models access, replace the body of `explain_verdict` with a `| ai prompt=... provider=splunk_hosted` SPL call. The function signature stays. Downstream callers (S1 middleware, S4 dashboards, eval harness) do not change.
- Keep the explanation under ~280 characters typical — it lands in a Splunk dashboard cell and a PDF regulator-evidence-pack table cell, both of which truncate longer strings.
- Cite ADR-013 in the module docstring header so future readers understand why this isn't an `| ai` call.
