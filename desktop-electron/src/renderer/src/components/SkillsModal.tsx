import { useEffect, useState } from "react";
import { useI18n, useLineLabel } from "../i18n";
import type { LineInfo } from "../types";
import { SkillsBrowser } from "./SkillsBrowser";

/** Overlay listing one line's skill roster, parsed live from each SKILL.md.
 *  Split view: sidebar list + detail view (title, desc, and file tree). */
export function SkillsModal(props: {
  repoRoot: string;
  line: LineInfo;
  onClose: () => void;
}) {
  const { repoRoot, line, onClose } = props;
  const { t } = useI18n();
  const lineLabel = useLineLabel();
  const [skillCount, setSkillCount] = useState(0);

  // close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>
            {lineLabel(line)} · {t("skills.skills")} <span className="count">{skillCount}</span>
          </h2>
          <button className="modal-close" aria-label={t("skills.close")} onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="modal-body">
          <SkillsBrowser repoRoot={repoRoot} line={line} onCountChange={setSkillCount} />
        </div>
      </div>
    </div>
  );
}
