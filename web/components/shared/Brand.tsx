import { Shield } from "./Shield";

export function Brand({ size = 22 }: { size?: number }) {
  return (
    <a href="#top" className="ag-brand" style={{ textDecoration: "none" }}>
      <Shield size={size} />
      <span className="ag-wordmark">SplunkGate</span>
    </a>
  );
}
