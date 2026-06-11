const path = require("path");

// ENTRIES MUST MATCH committed bundles in static/splunkgate-suit/. Do not add
// `hello` here — the hello.js placeholder is hand-written vanilla JS so the
// tarball packer needs no Node toolchain; webpack would overwrite it on build.
// PR 18 deletes the hello placeholder; PR 16/17/18 each add their dashboard
// entry below.
//
// CSS is NOT processed by webpack — `tokens.css` is committed verbatim and
// copied to ../static/splunkgate-suit/tokens.css via `npm run build:css`.
// This keeps the .css file as a real static file that Splunk's view stylesheet
// attribute can reference directly, rather than getting inlined into a JS bundle.

module.exports = {
    entry: {
        evidence_pack: "./views/evidence_pack.tsx",
        agent_risk_overview: "./views/agent_risk_overview.tsx",
        verdict_inspector: "./views/verdict_inspector.tsx"
    },
    output: {
        path: path.resolve(__dirname, "../static/splunkgate-suit"),
        filename: "[name].js",
        clean: false
    },
    resolve: { extensions: [".tsx", ".ts", ".js"] },
    module: {
        rules: [
            { test: /\.tsx?$/, use: "ts-loader", exclude: /node_modules/ },
            { test: /\.(woff2?|ttf)$/, type: "asset/resource" }
        ]
    },
    externals: {
        react: "React",
        "react-dom": "ReactDOM"
    }
};
