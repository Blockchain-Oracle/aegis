// Inline footnote-style provenance link. Renders a small ↗ arrow.

interface SrcProps {
  href: string;
  children?: React.ReactNode;
}

export function Src({ href, children = "source" }: SrcProps) {
  return (
    <a className="ag-src mono" href={href} target="_blank" rel="noreferrer">
      {children}
      <svg
        width="8"
        height="8"
        viewBox="0 0 8 8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      >
        <path d="M2.5 1.5H6.5V5.5M6.5 1.5L1.5 6.5" />
      </svg>
    </a>
  );
}
