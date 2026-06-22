// Per-line view registry. The left pane of the operation page renders a
// different view depending on the creative line:
//   n2d / ad / mv  -> infinite canvas (React Flow), reading review_ui/storyboard
//   novel          -> file tree (stub)
//   song           -> audio / takes (stub)
import type { CanvasData, WorkRoot } from "../types";
import { CanvasPane } from "../components/CanvasPane";

export interface ViewProps {
  canvas: CanvasData | null;
  root: WorkRoot;
  ep: string;
}

function FilesView({ root }: ViewProps) {
  return (
    <div className="stub-view">
      <h3>文件视图（novel 线 · 待实现）</h3>
      <p>v1 计划：Tauri fs 读取 {root.path} 的目录树 + Monaco markdown 预览。</p>
      <div className="tree">创作区/写小说/&lt;剧名&gt;/<br/>&nbsp;&nbsp;├─ 章节/<br/>&nbsp;&nbsp;├─ 设定/<br/>&nbsp;&nbsp;└─ 导出/</div>
    </div>
  );
}

function AudioView({ root }: ViewProps) {
  return (
    <div className="stub-view">
      <h3>音频视图（song 线 · 待实现）</h3>
      <p>v1 计划：wavesurfer.js 波形 + takes_manifest 多版挑版，根目录 {root.path}。</p>
    </div>
  );
}

export function viewForLine(view: "canvas" | "files" | "audio") {
  switch (view) {
    case "files":
      return FilesView;
    case "audio":
      return AudioView;
    case "canvas":
    default:
      return CanvasPane;
  }
}
