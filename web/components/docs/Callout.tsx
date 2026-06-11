interface CalloutProps {
  kind?: "note" | "warn" | "default";
  icon?: React.ReactNode;
  children: React.ReactNode;
}

export function Callout({ kind = "default", icon, children }: CalloutProps) {
  const fallback = kind === "warn" ? "🟡" : "◆";
  const className = kind === "default" ? "callout" : `callout ${kind}`;
  return (
    <div className={className}>
      <span className="ic">{icon ?? fallback}</span>
      <p>{children}</p>
    </div>
  );
}
