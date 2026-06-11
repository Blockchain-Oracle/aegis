/**
 * SUIT scaffold placeholder view (story-suit-scaffold).
 *
 * Renders a Dossier-styled hello-world card from data-attributes on the
 * host element. PR 18 (verdict-inspector) removes this view + bundle
 * once the three real dashboards land.
 */

import * as React from "react";
import { createRoot } from "react-dom/client";
import "../styles/tokens.css";

function HelloView(): React.ReactElement {
    return (
        <div className="splunkgate-suit">
            <div className="card">
                <h1>SplunkGate SUIT scaffold</h1>
                <p className="serif">
                    The bundle is wired. PR 16 lands{" "}
                    <span className="accent">Regulator Evidence Pack</span>; PR 17 lands{" "}
                    <span className="accent">Agent Risk Overview</span>; PR 18 lands the{" "}
                    <span className="accent">Verdict Inspector</span> and removes this
                    placeholder.
                </p>
                <hr className="rule" />
                <p className="mono" style={{ fontSize: 13, color: "var(--ink-2)" }}>
                    bundle: /static/splunkgate-suit/hello.js · tokens: Dossier · runtime: SUIT
                </p>
            </div>
        </div>
    );
}

const root = document.getElementById("splunkgate-suit-hello");
if (root) {
    createRoot(root).render(<HelloView />);
}
