export const FILES_SIDE_STORAGE_KEY = "aa.files.sideWidth";
export const FILES_SIDE_WIDTH_CHANGED_EVENT = "anime-armory:files-side-width-changed";
export const COLLAPSE_LEFT_SIDEBAR_EVENT = "anime-armory:collapse-left-sidebar";

export const FILES_SIDE_DEFAULT_WIDTH = 280;
export const FILES_SIDE_RESIZE_MIN_WIDTH = 72;
export const FILES_SIDE_EXPANDED_MIN_WIDTH = 180;
export const FILES_SIDE_COLLAPSE_WIDTH = 96;

let resizeEventScheduled = false;

/** Coalesce global resize notifications to one per animation frame — splitter
 *  drags fire pointermove far faster than the layout listeners (xterm refit,
 *  tree measurements) can usefully react, and each listener forces a reflow. */
export function scheduleWindowResizeEvent(): void {
  if (resizeEventScheduled) return;
  resizeEventScheduled = true;
  window.requestAnimationFrame(() => {
    resizeEventScheduled = false;
    window.dispatchEvent(new Event("resize"));
  });
}

export function clampFilesSideWidth(width: number, total: number): number {
  const minPreview = Math.min(320, Math.max(180, total * 0.35));
  const maxSide = Math.max(0, total - minPreview);
  const minSide = Math.min(FILES_SIDE_RESIZE_MIN_WIDTH, maxSide);
  return Math.min(maxSide, Math.max(minSide, width));
}

export function normalizeFilesSideWidth(value: number, fallback = FILES_SIDE_DEFAULT_WIDTH): number {
  if (!Number.isFinite(value) || value <= FILES_SIDE_COLLAPSE_WIDTH) return fallback;
  return Math.max(FILES_SIDE_EXPANDED_MIN_WIDTH, value);
}

export function readStoredFilesSideWidth(fallback = FILES_SIDE_DEFAULT_WIDTH): number {
  const raw = window.localStorage.getItem(FILES_SIDE_STORAGE_KEY);
  if (raw == null) return fallback;
  const saved = Number(raw);
  const next = normalizeFilesSideWidth(saved, fallback);
  if (!Number.isFinite(saved) || Math.round(saved) !== Math.round(next)) {
    window.localStorage.setItem(FILES_SIDE_STORAGE_KEY, String(Math.round(next)));
  }
  return next;
}

export function readStoredFilesSideWidthOrNull(): number | null {
  const raw = window.localStorage.getItem(FILES_SIDE_STORAGE_KEY);
  if (raw == null) return null;
  const saved = Number(raw);
  const next = normalizeFilesSideWidth(saved);
  if (!Number.isFinite(saved) || Math.round(saved) !== Math.round(next)) {
    window.localStorage.setItem(FILES_SIDE_STORAGE_KEY, String(Math.round(next)));
  }
  return next;
}

export function readCurrentFilesSideWidth(fallback = FILES_SIDE_DEFAULT_WIDTH): number {
  const raw = window.localStorage.getItem(FILES_SIDE_STORAGE_KEY);
  if (raw == null) return fallback;
  const value = Number(raw);
  if (!Number.isFinite(value)) return fallback;
  return Math.max(FILES_SIDE_RESIZE_MIN_WIDTH, value);
}

export function readCurrentFilesSideWidthOrNull(): number | null {
  const raw = window.localStorage.getItem(FILES_SIDE_STORAGE_KEY);
  if (raw == null) return null;
  const value = Number(raw);
  if (!Number.isFinite(value)) return null;
  return Math.max(FILES_SIDE_RESIZE_MIN_WIDTH, value);
}

export function emitFilesSideWidthChanged(): void {
  window.dispatchEvent(new Event(FILES_SIDE_WIDTH_CHANGED_EVENT));
}

export function draftFilesSideWidth(width: number): number {
  const next = Math.round(width);
  window.localStorage.setItem(FILES_SIDE_STORAGE_KEY, String(next));
  emitFilesSideWidthChanged();
  return next;
}

export function commitFilesSideWidth(width: number): number | null {
  if (width <= FILES_SIDE_COLLAPSE_WIDTH) {
    clearStoredFilesSideWidth();
    return null;
  }
  const next = Math.round(normalizeFilesSideWidth(width));
  window.localStorage.setItem(FILES_SIDE_STORAGE_KEY, String(next));
  emitFilesSideWidthChanged();
  return next;
}

export function clearStoredFilesSideWidth(): void {
  window.localStorage.removeItem(FILES_SIDE_STORAGE_KEY);
  emitFilesSideWidthChanged();
}
