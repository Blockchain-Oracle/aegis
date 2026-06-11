/**
 * SplunkGate — Agent Risk Overview (SUIT view, story-suit-agent-risk-overview).
 *
 * TypeScript source-of-truth for the built bundle at
 * `static/splunkgate-suit/agent_risk_overview.js`. Per the PR-15 contract,
 * the vanilla-JS bundle ships hand-written so the tarball packer needs no
 * Node toolchain at pack time. This TSX file is what the Phase-2 webpack
 * build will emit once CI gains a Node lane.
 *
 * **DRIFT CONTRACT**: when you fix a bug in this file, you MUST fix the
 * same bug in `static/splunkgate-suit/agent_risk_overview.js`. The test
 * `test_ar_drift_invariants_match` enforces shared invariants (Cisco AI
 * Defense rule names, SPL queries, panel titles, lifecycle markers).
 *
 * SPL data sources lift verbatim from
 * `docs/archive/dashboard-studio-v2/agent_risk_overview.xml`.
 */

import * as React from "react";
import { createRoot } from "react-dom/client";
import "../styles/tokens.css";

/* eslint-disable @typescript-eslint/no-explicit-any */
declare const require: any;

const MOUNT_ID = "splunkgate-agent-risk";
const SEARCH_TIMEOUT_MS = 30000;

/* 11 Cisco AI Defense rule names — VERBATIM. Heatmap Y-axis order is
 * load-bearing for examiner artifacts; do not re-sort. */
const CISCO_AI_DEFENSE_RULES = [
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
] as const;

const QUERIES = {
    total: "`splunkgate_data` | stats count",
    block: "`splunkgate_data` verdict_label=block | stats count",
    high: "`splunkgate_data` severity=HIGH | stats count",
    agents: "`splunkgate_data` | stats dc(agent_id) as agents",
    tokens_saved: "`splunkgate_data` verdict_label=block | stats sum(tokens_used) as tokens_saved",
    ts: "`splunkgate_data` | timechart span=1h count by verdict_label",
    heatmap: "`splunkgate_data` | mvexpand rule | bin _time span=1h | stats sum(severity_score) as score by _time, rule",
    top_agents: "`splunkgate_data` verdict_label=block | stats count by agent_id | sort -count | head 10",
    msj: '`splunkgate_data` | stats count(eval(severity!="NONE_SEVERITY")) as detections count as total_msgs by agent_id | eval detection_rate=round(detections/total_msgs,4) | sort -total_msgs',
} as const;

type SearchKey = keyof typeof QUERIES;
type Row = Record<string, string>;
type Status = "loading" | "ok" | "error" | "idle";

interface SearchState {
    status: Status;
    rows: Row[];
    error?: string;
}

interface SearchManagerInstance {
    cancel?: () => void;
    on: (event: string, cb: (props?: { message?: string }) => void) => void;
    data: (kind: string, params?: { count: number; offset: number }) => {
        on: (event: string, cb: (_unused: unknown, data: { results: Row[] }) => void) => void;
    };
}

interface TimePreset {
    value: string;
    label: string;
}

const TIME_PRESETS: ReadonlyArray<TimePreset> = [
    { value: "-1h@h", label: "Last 1 hour" },
    { value: "-24h@h", label: "Last 24 hours" },
    { value: "-7d@d", label: "Last 7 days" },
    { value: "-30d@d", label: "Last 30 days" },
];

const REFRESH_PRESETS = [
    { value: 0, label: "Off" },
    { value: 30000, label: "Every 30s" },
    { value: 60000, label: "Every 60s" },
    { value: 300000, label: "Every 5m" },
];

function useSplunkSearch(
    key: SearchKey,
    query: string,
    earliest: string,
    latest: string,
    resultsCount: number,
    tick: number
): SearchState {
    const [s, setS] = React.useState<SearchState>({ status: "idle", rows: [] });

    React.useEffect(() => {
        setS({ status: "loading", rows: [] });
        let cancelled = false;
        let mgr: SearchManagerInstance | null = null;
        const timer = setTimeout(() => {
            if (cancelled) {
                return;
            }
            cancelled = true;
            mgr?.cancel?.();
            setS({
                status: "error",
                rows: [],
                error: `Search timed out after ${SEARCH_TIMEOUT_MS / 1000}s — no response from Splunk Search SDK`,
            });
        }, SEARCH_TIMEOUT_MS);

        if (typeof require !== "function") {
            clearTimeout(timer);
            setS({ status: "error", rows: [], error: "Splunk runtime not detected" });
            return;
        }
        require(
            ["splunkjs/mvc/searchmanager"],
            (SearchManager: new (cfg: object) => SearchManagerInstance) => {
                if (cancelled) {
                    return;
                }
                try {
                    mgr = new SearchManager({
                        id: `splunkgate-ar-${key}-${Date.now()}`,
                        preview: false,
                        cache: false,
                        search: query,
                        earliest_time: earliest,
                        latest_time: latest,
                    });
                } catch (e: unknown) {
                    if (cancelled) {
                        return;
                    }
                    cancelled = true;
                    clearTimeout(timer);
                    setS({
                        status: "error",
                        rows: [],
                        error: `SearchManager construction failed: ${(e as Error).message ?? "unknown error"}`,
                    });
                    return;
                }
                mgr.on("search:error", (props) => {
                    if (cancelled) {
                        return;
                    }
                    cancelled = true;
                    clearTimeout(timer);
                    setS({
                        status: "error",
                        rows: [],
                        error: props?.message ?? "Splunk search returned an error (no message)",
                    });
                });
                mgr.data("results", { count: resultsCount, offset: 0 }).on("data", (_unused, data) => {
                    if (cancelled) {
                        return;
                    }
                    cancelled = true;
                    clearTimeout(timer);
                    setS({ status: "ok", rows: data?.results ?? [] });
                });
            },
            (err: { message?: string; requireType?: string }) => {
                if (cancelled) {
                    return;
                }
                cancelled = true;
                clearTimeout(timer);
                setS({
                    status: "error",
                    rows: [],
                    error: `Splunk Search SDK failed to load: ${err?.message ?? err?.requireType ?? "unknown require error"}`,
                });
            }
        );
        return () => {
            cancelled = true;
            clearTimeout(timer);
            mgr?.cancel?.();
        };
    }, [key, query, earliest, latest, resultsCount, tick]);

    return s;
}

function formatNumber(s: string | undefined): string {
    const num = parseInt(s ?? "0", 10);
    if (isNaN(num)) {
        return "0";
    }
    if (num >= 1000000) {
        return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
        return `${(num / 1000).toFixed(1)}k`;
    }
    return String(num);
}

interface KpiProps {
    id: string;
    label: string;
    suffix: string;
    state: SearchState;
    field: string;
    extraClass?: string;
    onIncrease?: (n: number) => void;
}

function Kpi({ id, label, suffix, state, field, extraClass, onIncrease }: KpiProps): React.ReactElement {
    const [tickClass, setTickClass] = React.useState<string>("");
    const value = state.status === "ok" ? formatNumber(state.rows[0]?.[field]) : "—";
    const prevRef = React.useRef<number | null>(null);

    React.useEffect(() => {
        if (state.status !== "ok") {
            return;
        }
        const num = parseInt(state.rows[0]?.[field] ?? "0", 10) || 0;
        if (prevRef.current !== null && num > prevRef.current) {
            if (onIncrease) {
                onIncrease(num);
            }
            setTickClass("ar-tick");
            const timer = setTimeout(() => setTickClass(""), 240);
            return () => clearTimeout(timer);
        }
        prevRef.current = num;
    }, [state, field, onIncrease]);

    const errorSuffix = state.status === "error" ? "load failed" : suffix;
    const displayValue = state.status === "loading" ? "—" : value;

    return (
        <div className={`ar-kpi ${extraClass ?? ""} ${tickClass}`} id={`ar-${id}`}>
            <div className="ar-kpi-label">{label}</div>
            <div className="ar-kpi-value">{displayValue}</div>
            <div className="ar-kpi-suffix">{errorSuffix}</div>
        </div>
    );
}

interface PanelStateProps {
    state: SearchState;
}

function PanelLoadingOrError({ state }: PanelStateProps): React.ReactElement | null {
    if (state.status === "loading" || state.status === "idle") {
        return <div className="ar-state">Loading…</div>;
    }
    if (state.status === "error") {
        return (
            <div className="ar-state-error-wrap">
                <div className="ar-state-error-head">PANEL FAILED TO LOAD</div>
                <div className="ar-state-error-msg">{state.error}</div>
            </div>
        );
    }
    return null;
}

function TopAgentsPanel({ state }: { state: SearchState }): React.ReactElement {
    const wrap = <PanelLoadingOrError state={state} />;
    if (wrap) {
        return wrap;
    }
    if (state.rows.length === 0) {
        return <div className="ar-state">No BLOCKED verdicts in the selected window.</div>;
    }
    return (
        <table className="ar-table">
            <thead>
                <tr>
                    <th>Agent ID</th>
                    <th>BLOCKs</th>
                </tr>
            </thead>
            <tbody>
                {state.rows.map((r, i) => {
                    const aid = r.agent_id ?? "";
                    const c = r.count ?? "0";
                    const url = `/app/splunkgate_app/verdict_inspector?form.input_agent_id=${encodeURIComponent(aid)}`;
                    return (
                        <tr key={i}>
                            <td className="ar-mono">
                                <a href={url}>{aid}</a>
                            </td>
                            <td className="ar-count">{c}</td>
                        </tr>
                    );
                })}
            </tbody>
        </table>
    );
}

function HeatmapPanel({ state }: { state: SearchState }): React.ReactElement {
    const wrap = <PanelLoadingOrError state={state} />;
    if (wrap) {
        return wrap;
    }
    if (state.rows.length === 0) {
        return <div className="ar-state">No rule hits in the selected time range.</div>;
    }
    const hourSet: Record<string, true> = {};
    state.rows.forEach((r) => {
        const t = r._time ?? "";
        const hh = t.length >= 13 ? `${t.substring(0, 13)}:00` : t;
        if (hh) {
            hourSet[hh] = true;
        }
    });
    const hours = Object.keys(hourSet).sort();
    const map: Record<string, number> = {};
    state.rows.forEach((r) => {
        const t = r._time ?? "";
        const hh = t.length >= 13 ? `${t.substring(0, 13)}:00` : t;
        const rule = r.rule ?? "";
        const score = parseFloat(r.score ?? "0") || 0;
        const key = `${rule}||${hh}`;
        map[key] = (map[key] ?? 0) + score;
    });
    const maxScore = Math.max(1, ...Object.values(map));
    const bucket = (score: number): number => {
        if (score <= 0) {
            return 0;
        }
        const pct = score / maxScore;
        if (pct < 0.2) {
            return 1;
        }
        if (pct < 0.4) {
            return 2;
        }
        if (pct < 0.6) {
            return 3;
        }
        if (pct < 0.8) {
            return 4;
        }
        return 5;
    };
    return (
        <div className="ar-heatmap">
            <table className="ar-heatmap-table">
                <thead>
                    <tr>
                        <th className="ar-rule-label">Cisco AI Defense rule</th>
                        {hours.map((hh) => (
                            <th key={hh} className="ar-hour-label">
                                {hh.length >= 13 ? hh.substring(11, 13) : hh}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {CISCO_AI_DEFENSE_RULES.map((rule) => (
                        <tr key={rule}>
                            <th className="ar-rule-label">{rule}</th>
                            {hours.map((hh) => {
                                const score = map[`${rule}||${hh}`] ?? 0;
                                return (
                                    <td
                                        key={hh}
                                        className="ar-heatmap-cell"
                                        data-intensity={bucket(score)}
                                        title={`${rule} @ ${hh} — score=${score.toFixed(1)}`}
                                    />
                                );
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function AgentRiskView(): React.ReactElement {
    const [earliest, setEarliest] = React.useState<string>("-24h@h");
    const [refreshIntervalMs, setRefreshIntervalMs] = React.useState<number>(30000);
    const [tick, setTick] = React.useState<number>(0);

    React.useEffect(() => {
        if (refreshIntervalMs === 0) {
            return;
        }
        const id = setInterval(() => setTick((t) => t + 1), refreshIntervalMs);
        return () => clearInterval(id);
    }, [refreshIntervalMs]);

    const total = useSplunkSearch("total", QUERIES.total, earliest, "now", 1, tick);
    const block = useSplunkSearch("block", QUERIES.block, earliest, "now", 1, tick);
    const high = useSplunkSearch("high", QUERIES.high, earliest, "now", 1, tick);
    const agents = useSplunkSearch("agents", QUERIES.agents, earliest, "now", 1, tick);
    const tokensSaved = useSplunkSearch("tokens_saved", QUERIES.tokens_saved, earliest, "now", 1, tick);
    const ts = useSplunkSearch("ts", QUERIES.ts, earliest, "now", 200, tick);
    const heatmap = useSplunkSearch("heatmap", QUERIES.heatmap, earliest, "now", 5000, tick);
    const topAgents = useSplunkSearch("top_agents", QUERIES.top_agents, earliest, "now", 10, tick);
    const msj = useSplunkSearch("msj", QUERIES.msj, "-7d", "now", 500, tick);

    return (
        <div className="splunkgate-suit">
            <div className="ar-page">
                <header className="ar-header">
                    <div>
                        <h1 className="ar-header-title">SplunkGate — Agent Risk Overview</h1>
                        <div className="ar-header-subtitle">
                            Real-time CISO/SOC view of AI agent safety verdicts across the estate.
                        </div>
                    </div>
                    <div className="ar-controls">
                        <div className="ar-control">
                            <label htmlFor="ar-time">Time range</label>
                            <select id="ar-time" value={earliest} onChange={(e) => setEarliest(e.target.value)}>
                                {TIME_PRESETS.map((p) => (
                                    <option key={p.value} value={p.value}>
                                        {p.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="ar-control">
                            <label htmlFor="ar-refresh">Auto-refresh</label>
                            <select
                                id="ar-refresh"
                                value={refreshIntervalMs}
                                onChange={(e) => setRefreshIntervalMs(parseInt(e.target.value, 10) || 0)}
                            >
                                {REFRESH_PRESETS.map((p) => (
                                    <option key={p.value} value={p.value}>
                                        {p.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="ar-refresh">{refreshIntervalMs > 0 ? "live" : "manual"}</div>
                    </div>
                </header>

                <section className="ar-kpis">
                    <Kpi id="kpi-total" label="Total verdicts" suffix="verdicts in window" state={total} field="count" />
                    <Kpi
                        id="kpi-block"
                        label="BLOCKED actions"
                        suffix="intercepted before LLM/tool"
                        state={block}
                        field="count"
                        extraClass="ar-kpi-block"
                    />
                    <Kpi
                        id="kpi-high"
                        label="HIGH severity"
                        suffix="rule hits"
                        state={high}
                        field="count"
                        extraClass="ar-kpi-high"
                    />
                    <Kpi id="kpi-agents" label="Distinct agents" suffix="active in window" state={agents} field="agents" />
                    <Kpi
                        id="kpi-tokens"
                        label="Tokens saved"
                        suffix="BLOCK × tokens_used"
                        state={tokensSaved}
                        field="tokens_saved"
                    />
                </section>

                <div className="ar-panel">
                    <h2>Verdicts by label, per hour</h2>
                    <p className="ar-panel-desc">
                        Stacked verdict counts per hour over the selected window. The Phase-2 webpack build will swap
                        the SVG renderer for a `@splunk/react-visualizations` chart; until then the vanilla bundle
                        emits the SVG inline.
                    </p>
                    {ts.status === "ok" ? (
                        <div className="ar-state">
                            Verdicts by label rendered in vanilla bundle ({ts.rows.length} buckets).
                        </div>
                    ) : (
                        <PanelLoadingOrError state={ts} />
                    )}
                </div>

                <section className="ar-grid">
                    <div className="ar-panel">
                        <h2>Rules-by-hour heatmap</h2>
                        <p className="ar-panel-desc">
                            Per-hour severity-weighted score for each of the 11 Cisco AI Defense rule names. Row order
                            is verbatim from the Cisco Offer Description.
                        </p>
                        <HeatmapPanel state={heatmap} />
                    </div>
                    <div className="ar-panel">
                        <h2>Top agents by BLOCKED count</h2>
                        <p className="ar-panel-desc">Click a row to drill into the Verdict Inspector for that agent.</p>
                        <TopAgentsPanel state={topAgents} />
                    </div>
                </section>

                <div className="ar-panel">
                    <h2>MSJ scaling indicator (last 7 days)</h2>
                    <p className="ar-panel-desc">
                        Detection rate vs. in-context message count per agent — Many-Shot Jailbreaking probabilistic
                        floor (Anthropic 2024). Higher detection_rate at high total_msgs = healthier agent.
                    </p>
                    {msj.status === "ok" ? (
                        <div className="ar-state">MSJ scaling rendered in vanilla bundle ({msj.rows.length} agents).</div>
                    ) : (
                        <PanelLoadingOrError state={msj} />
                    )}
                </div>

                <footer className="ar-footer">
                    <span>SplunkGate v1.0.0</span>
                    <span>{TIME_PRESETS.find((p) => p.value === earliest)?.label ?? earliest}</span>
                    <span>Last refresh tick: {tick}</span>
                </footer>
            </div>
        </div>
    );
}

const root = document.getElementById(MOUNT_ID);
if (!root) {
    // eslint-disable-next-line no-console
    console.warn(`[splunkgate-agent-risk] mount node #${MOUNT_ID} not found`);
} else {
    createRoot(root).render(<AgentRiskView />);
}
