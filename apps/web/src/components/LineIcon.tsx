import type { CreationLine } from "../types";

export function LineIcon({ line }: { line: CreationLine }) {
  const common = { viewBox: "0 0 24 24", "aria-hidden": true } as const;
  if (line === "novel") return <svg {...common}><path d="M4 5.5c3.2-.9 5.8-.3 8 1.8v12c-2.2-2.1-4.8-2.7-8-1.8Zm16 0c-3.2-.9-5.8-.3-8 1.8v12c2.2-2.1 4.8-2.7 8-1.8Z" /></svg>;
  if (line === "n2d") return <svg {...common}><rect x="3.5" y="5" width="17" height="14" rx="2" /><path d="m10 9 6 3-6 3Z" /></svg>;
  if (line === "comic") return <svg {...common}><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M12 4v16M4 12h16" /></svg>;
  if (line === "ad") return <svg {...common}><path d="m4 13 11-5v8L4 13Zm11-3 4-2v8l-4-2M7 14l2 6h4l-2-7" /></svg>;
  if (line === "mv") return <svg {...common}><path d="M9 17V6l10-2v11M9 9l10-2" /><circle cx="6" cy="18" r="3" /><circle cx="16" cy="16" r="3" /></svg>;
  return <svg {...common}><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11v1a7 7 0 0 0 14 0v-1M12 19v3M8 22h8" /></svg>;
}
