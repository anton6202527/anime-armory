import { useEffect, useState } from "react";
import { readNextAction } from "../api";
import type { NextAction } from "../types";

// Read-only "what to do next" strip, driven by `run.py next --json`.
// Shows the headline + the exact command the user can copy into the terminal.
export function NextActionStrip(props: {
  repoRoot: string;
  root: string;
  ep: string;
  refreshKey?: number;
}) {
  const { repoRoot, root, ep, refreshKey } = props;
  const [na, setNa] = useState<NextAction | null>(null);

  useEffect(() => {
    let alive = true;
    readNextAction(repoRoot, root, ep)
      .then((d) => alive && setNa(d))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [repoRoot, root, ep, refreshKey]);

  if (!na) return <div className="next-strip reason">下一步：分析中…</div>;
  if (na.error) return <div className="next-strip reason">run.py 不可用（{na.error.slice(0, 80)}）</div>;

  const head = na.action_card?.headline || na.frontier?.label || na.stop_reason || "—";
  const cmd = na.action_card?.exact_command;
  return (
    <div className="next-strip">
      <span className="headline">下一步</span>
      <span>{head}</span>
      {cmd && <code title="复制到右侧终端">{cmd}</code>}
      {na.stop_reason && <span className="reason">· {na.stop_reason}</span>}
    </div>
  );
}
