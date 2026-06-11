"use client";

import { useState } from "react";

interface CodeBlockProps {
  name: string;
  html: string; // Pre-highlighted HTML (tok-* spans). Trusted, built at compile time.
  plain?: string; // Optional clipboard text; falls back to stripped HTML.
}

export function CodeBlock({ name, html, plain }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    const text = plain ?? html.replace(/<[^>]+>/g, "");
    navigator.clipboard
      ?.writeText(text)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1400);
      })
      .catch(() => {});
  };
  return (
    <div className="code">
      <div className="code-bar">
        <span className="code-name">{name}</span>
        <button className={"code-copy" + (copied ? " copied" : "")} onClick={copy}>
          {copied ? "✓ copied" : "copy"}
        </button>
      </div>
      <pre>
        <code dangerouslySetInnerHTML={{ __html: html }} />
      </pre>
    </div>
  );
}
