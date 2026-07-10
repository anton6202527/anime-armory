import type { LineInfo, WorkRoot } from "../types";
import { useI18n } from "../i18n";
import { Codicon } from "./Codicon";

export interface WorkTab {
  id: string; // = root.path (unique)
  line: LineInfo;
  root: WorkRoot;
  lastUsedAt: number;
}

const isMac = typeof navigator !== "undefined" && navigator.userAgent.includes("Macintosh");

/** Window-level tab strip: a pinned Home button + one closable tab per opened
 *  work (creation window). Lives in the overlay titlebar; empty areas drag the
 *  window. macOS leaves room on the left for the traffic-light buttons. */
export function TopTabs(props: {
  tabs: WorkTab[];
  activeId: string | null; // null = Home/创作区 (no work tab active)
  onHome: () => void;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
}) {
  const { tabs, activeId, onHome, onSelect, onClose } = props;
  const { t } = useI18n();
  return (
    <div className="topbar" data-tauri-drag-region style={{ paddingLeft: isMac ? 78 : 8 }}>
      <button
        className={"home-tab" + (activeId === null ? " active" : "")}
        title={t("tabs.home")}
        onClick={onHome}
      >
        <svg className="home-glyph" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="M4.75 11.2 12 4.95l7.25 6.25" />
          <path d="M6.6 10.5v8.3h10.8v-8.3" />
          <path d="M9.65 18.8v-5.25h4.7v5.25" />
        </svg>
      </button>
      <div className="tabs" data-tauri-drag-region>
        {tabs.map((tab) => (
          <div
            key={tab.id}
            className={"work-tab" + (activeId === tab.id ? " active" : "")}
            onClick={() => onSelect(tab.id)}
            title={tab.root.path}
          >
            <span className="tab-label">{tab.root.name}</span>
            <button
              className="tab-close"
              title={t("tabs.close")}
              aria-label={t("tabs.close")}
              onClick={(e) => {
                e.stopPropagation();
                onClose(tab.id);
              }}
            >
              <Codicon name="close" />
            </button>
          </div>
        ))}
      </div>
      <div className="topbar-fill" data-tauri-drag-region />
    </div>
  );
}
