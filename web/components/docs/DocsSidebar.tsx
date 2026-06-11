import { DOCS_NAV } from "@/lib/docs-nav";

interface DocsSidebarProps {
  active: string;
  open: boolean;
  onNav: () => void;
}

export function DocsSidebar({ active, open, onNav }: DocsSidebarProps) {
  return (
    <aside className={"docs-side" + (open ? " open" : "")}>
      {DOCS_NAV.map((grp) => (
        <div className="docs-side-group" key={grp.g}>
          <h4>{grp.g}</h4>
          {grp.items.map(([id, label]) => (
            <a
              key={id}
              href={`#${id}`}
              className={active === id ? "active" : ""}
              onClick={onNav}
            >
              {label}
            </a>
          ))}
        </div>
      ))}
    </aside>
  );
}
