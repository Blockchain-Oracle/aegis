interface SectionHeadProps {
  kicker?: string;
  title?: string;
  lead?: string;
  right?: React.ReactNode;
  id?: string;
}

export function SectionHead({ kicker, title, lead, right, id }: SectionHeadProps) {
  return (
    <div className="sec-head" id={id}>
      <div className="sec-head-row">
        <div>
          {kicker && <div className="kicker">{kicker}</div>}
          {title && <h2 className="sec-h2">{title}</h2>}
        </div>
        {right}
      </div>
      {lead && <p className="sec-lead">{lead}</p>}
    </div>
  );
}
