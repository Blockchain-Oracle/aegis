// Sidebar information architecture for the docs site. The order of items
// inside each group drives the scroll-spy active highlight and the right-
// rail "on this page" links — keep it consistent with the order sections
// appear in DocsContent.

export interface DocsNavGroup {
  g: string;
  items: ReadonlyArray<readonly [string, string]>;
}

export const DOCS_NAV: ReadonlyArray<DocsNavGroup> = [
  {
    g: "Get started",
    items: [
      ["overview", "Overview"],
      ["install", "Installation"],
      ["quickstart", "Quickstart"],
    ],
  },
  {
    g: "Concepts",
    items: [
      ["verdict-shape", "The Verdict type"],
      ["enums", "Severity & result"],
      ["surfaces", "The four surfaces"],
      ["judgment", "Judgment layer"],
    ],
  },
  {
    g: "Integration",
    items: [
      ["s1", "S1 · Middleware"],
      ["s2", "S2 · MCP server"],
      ["s3", "S3 · DefenseClaw"],
      ["s4", "S4 · Splunk app"],
      ["configuration", "Configuration"],
    ],
  },
  {
    g: "Operations",
    items: [
      ["otel", "OTel emission"],
      ["hec", "HEC sourcetype"],
      ["failure", "Failure modes"],
      ["errors", "Error reference"],
    ],
  },
  {
    g: "Regulatory",
    items: [
      ["nist", "NIST AI RMF"],
      ["sr262", "SR 26-2"],
      ["euact", "EU AI Act Art. 6"],
    ],
  },
  { g: "Evaluation", items: [["eval", "Datasets & results"]] },
] as const;

export const DOCS_IDS = DOCS_NAV.flatMap((g) => g.items.map((i) => i[0]));
