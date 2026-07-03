import type { LineInfo, WorkRoot } from "../types";
import { openSourceRepo } from "../api";
import { LanguageSwitcher, useI18n } from "../i18n";

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
              aria-label={t("tabs.close")}
              onClick={(e) => {
                e.stopPropagation();
                onClose(tab.id);
              }}
            >
              <svg viewBox="0 0 12 12" aria-hidden="true" focusable="false">
                <path d="M3 3l6 6M9 3L3 9" />
              </svg>
            </button>
          </div>
        ))}
      </div>
      <div className="topbar-fill" data-tauri-drag-region />
      <LanguageSwitcher />
      <button
        type="button"
        className="source-link"
        title={t("source.title")}
        aria-label={t("source.title")}
        onClick={() => {
          openSourceRepo().catch(() => {
            window.open("https://github.com/anton6202527/anime-armory", "_blank", "noopener,noreferrer");
          });
        }}
      >
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <path
            fill="currentColor"
            d="M8 0.25a7.75 7.75 0 0 0-2.45 15.1c0.39 0.07 0.53-0.17 0.53-0.38v-1.35c-2.18 0.47-2.64-0.94-2.64-0.94-0.36-0.91-0.87-1.15-0.87-1.15-0.71-0.49 0.05-0.48 0.05-0.48 0.79 0.06 1.2 0.81 1.2 0.81 0.7 1.2 1.83 0.85 2.28 0.65 0.07-0.51 0.27-0.85 0.5-1.05-1.74-0.2-3.57-0.87-3.57-3.87 0-0.85 0.31-1.55 0.81-2.1-0.08-0.2-0.35-1 0.08-2.07 0 0 0.66-0.21 2.14 0.8a7.42 7.42 0 0 1 3.9 0c1.48-1.01 2.13-0.8 2.13-0.8 0.43 1.07 0.16 1.87 0.08 2.07 0.5 0.55 0.8 1.25 0.8 2.1 0 3.01-1.83 3.67-3.58 3.86 0.28 0.24 0.53 0.72 0.53 1.45v2.15c0 0.21 0.14 0.45 0.54 0.38A7.75 7.75 0 0 0 8 0.25Z"
          />
        </svg>
      </button>
    </div>
  );
}
