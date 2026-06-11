/* SplunkGate SUIT scaffold placeholder bundle — vanilla JS.
 *
 * The full pipeline is documented in src/webpack.config.js; this file
 * is the hand-written equivalent of `npm run build` for src/views/hello.tsx
 * so the .tgz packager doesn't need a Node toolchain. Once PR 16 lands
 * the first real dashboard, this bundle gets webpack-emitted alongside
 * the real chunks.
 */
(function () {
    "use strict";

    function render(root) {
        var html = [
            '<div class="splunkgate-suit">',
            '<div class="card">',
            '<h1>SplunkGate SUIT scaffold</h1>',
            '<p class="serif">The bundle is wired. PR 16 lands ',
            '<span class="accent">Regulator Evidence Pack</span>; ',
            'PR 17 lands <span class="accent">Agent Risk Overview</span>; ',
            'PR 18 lands the <span class="accent">Verdict Inspector</span> ',
            'and removes this placeholder.</p>',
            '<hr class="rule" />',
            '<p class="mono" style="font-size:13px;color:var(--ink-2);">',
            'bundle: /static/splunkgate-suit/hello.js | tokens: Dossier | runtime: SUIT',
            '</p>',
            '</div>',
            '</div>'
        ].join("");
        root.innerHTML = html;
    }

    function mount() {
        var root = document.getElementById("splunkgate-suit-hello");
        if (!root) {
            // Loud breadcrumb so a developer deep-linking the hidden view to
            // debug the bundle sees *why* nothing rendered. Silent no-op would
            // mask XML/JS ID drift across _suit_hello.xml + hello.js + hello.tsx.
            if (typeof console !== "undefined" && console.warn) {
                console.warn(
                    "[splunkgate-suit] mount node #splunkgate-suit-hello not found; " +
                    "check _suit_hello.xml HTML module emitted the host div"
                );
            }
            return;
        }
        render(root);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", mount);
    } else {
        mount();
    }
}());
