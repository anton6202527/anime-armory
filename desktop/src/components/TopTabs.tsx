import type { LineInfo, WorkRoot } from "../types";
import { LanguageSwitcher, useI18n } from "../i18n";

export interface WorkTab {
  id: string; // = root.path (unique)
  line: LineInfo;
  root: WorkRoot;
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
        <span className="home-glyph">⌂</span>
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
              onClick={(e) => {
                e.stopPropagation();
                onClose(tab.id);
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      <div className="topbar-fill" data-tauri-drag-region />
      <LanguageSwitcher />
    </div>
  );
}
