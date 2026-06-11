const path = require("path");

module.exports = {
    entry: {
        evidence_pack: "./views/evidence_pack.tsx",
        agent_risk_overview: "./views/agent_risk_overview.tsx",
        verdict_inspector: "./views/verdict_inspector.tsx",
        hello: "./views/hello.tsx"
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
            { test: /\.css$/, use: ["style-loader", "css-loader"] },
            { test: /\.(woff2?|ttf)$/, type: "asset/resource" }
        ]
    },
    externals: {
        react: "React",
        "react-dom": "ReactDOM"
    }
};
