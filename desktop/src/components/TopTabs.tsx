import type { LineInfo, WorkRoot } from "../types";

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
  return (
    <div className="topbar" data-tauri-drag-region style={{ paddingLeft: isMac ? 78 : 8 }}>
      <button
        className={"home-tab" + (activeId === null ? " active" : "")}
        title="首页"
        onClick={onHome}
      >
        <span className="home-glyph">⌂</span>
      </button>
      <div className="tabs" data-tauri-drag-region>
        {tabs.map((t) => (
          <div
            key={t.id}
            className={"work-tab" + (activeId === t.id ? " active" : "")}
            onClick={() => onSelect(t.id)}
            title={t.root.path}
          >
            <span className="tab-label">{t.root.name}</span>
            <button
              className="tab-close"
              title="关闭"
              onClick={(e) => {
                e.stopPropagation();
                onClose(t.id);
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      <div className="topbar-fill" data-tauri-drag-region />
    </div>
  );
}
