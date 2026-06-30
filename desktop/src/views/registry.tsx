// Shared props for the left-pane views. The operation page now renders a
// sub-tab bar (see pages/Operation.tsx):
//   文件 (default, every line) -> FilesPane (real work-folder tree + preview)
//   画布 (canvas lines n2d/ad/mv) -> CanvasPane (infinite canvas / kanban board)
import type { CanvasData, WorkRoot } from "../types";

export interface ViewProps {
  canvas: CanvasData | null;
  root: WorkRoot;
  ep: string;
  refreshKey?: number;
}
