interface SecProps {
  id: string;
  eyebrow?: string;
  title: string;
  children: React.ReactNode;
}

export function Sec({ id, eyebrow, title, children }: SecProps) {
  return (
    <section className="docs-sec" id={id}>
      {eyebrow && <div className="docs-eyebrow">{eyebrow}</div>}
      <h2>{title}</h2>
      {children}
    </section>
  );
}
