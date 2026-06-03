# CLAUDE.md — Aegis Project Conventions for Coding Agents

> Read this before opening any PR against the Aegis repo. Anything not in here is delegated to `docs/architecture.md` + `docs/cicd-spec.md`.

## The hard rules

1. **Every source file ≤ 400 LOC** (excluding blank + pure-comment lines). Enforced via pre-commit + CI fail-on-exceed. No `# noqa: loc-cap` escape hatch — split via composition or extraction.
2. **mypy `--strict` clean** for `packages/aegis_core/` and `packages/aegis_judges/`. Non-strict acceptable for `aegis_mw`, `aegis_mcp`, and `splunk_apps/aegis_app/bin/`.
3. **`ruff` clean** across the entire monorepo.
4. **No real credentials in code or fixtures.** AI Defense mocks default to `mock=True`; live calls require `AEGIS_AI_DEFENSE_API_KEY`.
5. **No `Any` in `aegis_core` or `aegis_judges`.** Use `object` + `repr()` for schema-flexible inputs.
6. **No `verify=False` in production HTTP paths.** Splunk's own `splunklib/ai/tools.py:308` does this — document but don't replicate.

## Verdict shape — single source of truth

`packages/aegis_core/src/aegis_core/verdict.py` defines `Verdict`, `Severity` (including `NONE_SEVERITY`), `VerdictLabel`, and `RuleHit`. **`RuleHit.source` is `Literal["ai_defense", "defenseclaw_regex", "splunklib_security"]` — Foundation-Sec NEVER appears here** (ADR-003: Foundation-Sec is an EXPLAINER not a classifier; it generates `Verdict.explanation` only).

`VerdictContext` lives at `aegis_core.verdict_context` and is the shared agent-side context passed alongside `Verdict` to Foundation-Sec.

## Foundation-Sec — explainer-only

Per ADR-003 and triple-confirmed by primary-source audits:
- Foundation-Sec is positioned by Cisco as a security copilot/generator, NOT a classifier
- Used to populate `Verdict.explanation` only
- NEVER classify a `RuleHit`; NEVER appear in `RuleHit.source`
- Canonical signature: `FoundationSecExplainer.explain(ctx: VerdictContext, verdict: Verdict) -> str`

## OTel evaluation events

All Aegis verdicts emit as OpenTelemetry `gen_ai.evaluation.result` events with custom `score.label` values `block`/`allow`/`modify`/`review` (proposing upstream post-hackathon). MCP sub-convention attrs (`mcp.method.name`, `mcp.session.id`, `mcp.protocol.version`) co-emit when the call originated from the MCP server.

## Cisco AI Defense Inspection API — verbatim rule names

When emitting or matching rule names, use the verbatim 11 per `../context/07-cisco-stack/01-ai-defense-deep.md`:

> Code Detection, Harassment, Hate Speech, PCI, PHI, PII, Prompt Injection, Profanity, Sexual Content & Exploitation, Social Division & Polarization, Violence & Public Safety Threats

DO NOT use legacy/hallucinated names like `Toxicity`, `Self-Harm`, or bare `Violence` — the API will not return them and your code will silently match nothing.

Response field is `rules` (NOT `triggered_rules`). Severity enum includes `NONE_SEVERITY`.

## Splunk MCP — Aegis runs its OWN server

Splunk's MCP Server (`CiscoDevNet/Splunk-MCP-Server-official`) is closed-source — README + LICENSE only. Aegis MCP runs ALONGSIDE Splunk's server, NOT into it. Aegis tools use the `aegis_*` prefix exclusively; they coexist with Splunk's 10 native `splunk_*` tools and 4 `saia_*` tools (when SAIA is co-installed) via standard MCP client multi-server configs.

Pin to MCP spec version `2025-11-25` (Stable). NOT `2025-03-26`.

## Splunk app sourcetype — co-locate with Cisco Security Cloud

All Aegis verdict events land in Splunk under sourcetype `cisco_ai_defense:aegis_verdict` — colocates with the existing `cisco_ai_defense:*` sourcetype family Cisco Security Cloud (Splunkbase app 7404 v3.6.6, 55K+ installs) already populates. SOC analysts get unified search without schema migration.

## Cite back into `../context/` and `../research/`

Every load-bearing factual claim in any PR description, code comment, or test must cite back to:
- `../context/<folder>/<file>.md` for verified domain facts (primary-source-grounded by R1-R12 audit)
- `../research/splunk-agentic-ops-2026/<file>.md` for hackathon-specific facts (PRD references, judging criteria)

Pattern: `# Per ../context/05-splunk-core/05-spl-reference.md, ...`

NOTE: `01-prizes-tracks.md` and `04-judges.md` live in `../research/`, NOT `../context/`.

## The PR workflow (the only way code lands on main)

1. **Pick a GitHub issue.** Read the BDD acceptance criteria + file modification map verbatim — those are the contract.
2. **Branch from `main`** with `git checkout -b feat/<story-slug>` (or `fix/...`, `docs/...`).
3. **Implement.** Stay within the file modification map. If you need to touch a file outside the map, stop and check with Abu first.
4. **Verify locally.** Run the BDD criteria's shell verification block + the story's tests. All must pass before pushing.
5. **`git commit -s`** with a message starting `feat(<area>): <one-line summary>` and including a `Closes #<issue>` footer.
6. **`git push -u origin feat/<story-slug>`** and open a PR with `gh pr create --fill`.
7. **Fire the PR reviewer** the moment the PR is up:
   ```
   /pr-review-toolkit:review-pr
   ```
   This runs the multi-agent review fleet (code-reviewer, silent-failure-hunter, type-design-analyzer, comment-analyzer, pr-test-analyzer, code-simplifier). It WILL find things.
8. **Address every blocking finding.** Non-blocking suggestions can be deferred to a follow-up PR with a tracking issue.
9. **Re-run** `/pr-review-toolkit:review-pr` after addressing findings until it returns clean (or only non-blocking).
10. **Merge to main** via squash-merge (`gh pr merge --squash`). DO NOT merge while CI is red — fix the underlying issue first.
11. **Rebase your next branch on the merged main** before starting the next story.

### Why this workflow

- CI runs (lint / typecheck / test / loc-cap / appinspect / eval-smoke / build / security) gate every merge. CI is the catch-all.
- `pr-review-toolkit` adds a SECOND layer of review specifically for the kinds of bugs CI misses: silent failures, type-design smells, comment-rot, test-quality gaps, simplification opportunities.
- Squash-merging keeps `main` linear and easy to revert.

### When CI doesn't exist yet (very early stories)

If you're working on story-cicd-01 through story-cicd-08 (the CI/CD foundation epic) and there's literally no CI to run yet:

- Open the PR as normal
- Fire `/pr-review-toolkit:review-pr` as the substitute for CI
- Only merge once the reviewer fleet returns clean
- The first story to land a green `ci.yml` workflow unlocks normal CI-gated merging for everyone after

## Audit discipline (don't accept findings blindly)

This repo went through a 5-pass + 2-pass audit cycle during the spec phase. Pattern learned:

- Audit findings are recommendations, not ground truth. **Verify against primary sources before applying.**
- Sub-agents that touch many files cascade defects. After any large rewrite, **walk the diff** and check for cross-cutting consequences (paths, depends_on, file ownership).
- `grep -F` with `\|` alternation is a footgun — backslash-pipe is literal under `-F`. Use plain `grep -cE` for extended regex alternation, or loop per-key with `-c`.
- Synthesis docs can drift from what's correct. Implementer's choice against primary source > synthesis recommendation. Document the override in `docs/plans/` when you take that call.

## Reference docs

- `docs/PRD.md` — product vision + demo moment + judging criteria alignment
- `docs/architecture.md` — stack + repo structure + library choices + 11 ADRs
- `docs/cicd-spec.md` — pipelines + gates + secrets list + branch protection requirements
- `docs/eval-spec.md` — datasets + metrics + 3 baselines
- `docs/ux-spec.md` — three Dashboard Studio v2 dashboards (Surface 4)
- `docs/epics.md` — 12 epics + dispatch queue
- `docs/sprint-status.yaml` — story dependency graph (orchestrator reads this)
- `docs/plans/` — design + audit history
- `../context/` — verified domain knowledge corpus (12 folders, primary-source-grounded)
- `../research/splunk-agentic-ops-2026/` — hackathon-specific research (PRD, judges, etc.)
