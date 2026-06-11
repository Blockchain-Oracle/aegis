// JSON syntax-highlighter — emits <span class="tok-*"> spans the designer's CSS targets.
// The output is HTML and is injected via dangerouslySetInnerHTML into <CodeBlock>.

const ESCAPE = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const TOKEN_RE = /("(?:\\.|[^\\"])*"(\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?)/g;

export function jsonHighlight(obj: unknown): string {
  const json = ESCAPE(JSON.stringify(obj, null, 2));
  return json.replace(TOKEN_RE, (m) => {
    let cls = "tok-num";
    if (/^"/.test(m)) cls = /:\s*$/.test(m) ? "tok-blue" : "tok-str";
    else if (/true|false|null/.test(m)) cls = "tok-kw";
    return `<span class="${cls}">${m}</span>`;
  });
}
