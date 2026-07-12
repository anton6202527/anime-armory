import {
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type CSSProperties,
  type MouseEvent as ReactMouseEvent,
} from "react";
import { workDir } from "../api";
import type { EditorBreadcrumbCursorStore } from "../editorBreadcrumbCursor";
import type { EditorBreadcrumbDocumentStore } from "../editorBreadcrumbDocument";
import type {
  BreadcrumbSymbolRequest,
  BreadcrumbSymbolResponse,
  EditorBreadcrumbSymbol,
  EditorBreadcrumbSymbolKind,
} from "../editorBreadcrumbTypes";
import { useI18n } from "../i18n";
import type { SkillTreeEntry } from "../types";
import { Codicon } from "./Codicon";
import { WorkFileIcon } from "./FileIcon";

const DIRECTORY_PAGE_SIZE = 200;
const SYMBOL_TEXT_LIMIT = 2 * 1024 * 1024;
const SYMBOL_CACHE_LIMIT = 24;
const PICKER_MAX_WIDTH = 380;

type DirectoryPage = {
  entries: SkillTreeEntry[];
  hasMore: boolean;
  nextOffset: number;
};

type PickerPosition = {
  left: number;
  width: number;
  arrowLeft: number;
};

type PathPicker = PickerPosition & {
  kind: "path";
  dir: string;
};

type SymbolPicker = PickerPosition & {
  kind: "symbols";
};

type PickerState = PathPicker | SymbolPicker;

let symbolWorker: Worker | null = null;
let symbolRequestId = 0;
const symbolRequests = new Map<
  number,
  { resolve: (symbols: EditorBreadcrumbSymbol[]) => void; reject: (error: unknown) => void }
>();

function getSymbolWorker(): Worker {
  if (symbolWorker) return symbolWorker;
  symbolWorker = new Worker(new URL("../breadcrumbSymbols.worker.ts", import.meta.url), { type: "module" });
  symbolWorker.onmessage = (event: MessageEvent<BreadcrumbSymbolResponse>) => {
    const request = symbolRequests.get(event.data.id);
    if (!request) return;
    symbolRequests.delete(event.data.id);
    request.resolve(event.data.symbols);
  };
  symbolWorker.onerror = (error) => {
    for (const request of symbolRequests.values()) request.reject(error);
    symbolRequests.clear();
    symbolWorker?.terminate();
    symbolWorker = null;
  };
  return symbolWorker;
}

function requestSymbols(name: string, text: string): Promise<EditorBreadcrumbSymbol[]> {
  const id = ++symbolRequestId;
  return new Promise((resolve, reject) => {
    symbolRequests.set(id, { resolve, reject });
    const request: BreadcrumbSymbolRequest = { id, name, text: text.slice(0, SYMBOL_TEXT_LIMIT) };
    getSymbolWorker().postMessage(request);
  });
}

function parentPath(path: string): string {
  const index = path.lastIndexOf("/");
  return index < 0 ? "" : path.slice(0, index);
}

function symbolIcon(kind: EditorBreadcrumbSymbolKind): "symbolClass" | "symbolFunction" | "symbolKey" | "symbolString" {
  if (kind === "class") return "symbolClass";
  if (kind === "function") return "symbolFunction";
  if (kind === "property") return "symbolKey";
  return "symbolString";
}

function activeSymbolTrail(symbols: EditorBreadcrumbSymbol[], cursorLine: number): EditorBreadcrumbSymbol[] {
  const stack: EditorBreadcrumbSymbol[] = [];
  for (const symbol of symbols) {
    if (symbol.line > cursorLine) break;
    while (stack.length > 0 && stack[stack.length - 1].level >= symbol.level) stack.pop();
    stack.push(symbol);
  }
  return stack;
}

export function EditorBreadcrumbs({
  rootName,
  rootPath,
  entry,
  documentStore,
  contentVersion,
  directoryVersion,
  cursorStore,
  onOpenFile,
  onNavigateLine,
}: {
  rootName: string;
  rootPath: string;
  entry: SkillTreeEntry;
  documentStore: EditorBreadcrumbDocumentStore;
  contentVersion: string;
  directoryVersion: string;
  cursorStore: EditorBreadcrumbCursorStore;
  onOpenFile: (path: string) => void;
  onNavigateLine: (line: number) => void;
}) {
  const { t } = useI18n();
  const cursorLine = useSyncExternalStore(cursorStore.subscribe, cursorStore.getSnapshot, cursorStore.getSnapshot);
  const activeDocument = useSyncExternalStore(documentStore.subscribe, documentStore.getSnapshot, documentStore.getSnapshot);
  const text = activeDocument.path === entry.path ? activeDocument.text : "";
  const barRef = useRef<HTMLDivElement>(null);
  const pickerListRef = useRef<HTMLDivElement>(null);
  const directoryCacheRef = useRef<Map<string, Promise<DirectoryPage>>>(new Map());
  const directoryRequestRef = useRef(0);
  const symbolCacheRef = useRef<Map<string, EditorBreadcrumbSymbol[]>>(new Map());
  const [symbols, setSymbols] = useState<EditorBreadcrumbSymbol[]>([]);
  const [picker, setPicker] = useState<PickerState | null>(null);
  const [directoryPage, setDirectoryPage] = useState<DirectoryPage | null>(null);
  const [directoryLoading, setDirectoryLoading] = useState(false);
  const [directoryError, setDirectoryError] = useState("");

  const pathSegments = useMemo(() => {
    const names = entry.path.split("/").filter(Boolean);
    return names.map((name, index) => ({
      name,
      path: names.slice(0, index + 1).join("/"),
      isDir: index < names.length - 1,
    }));
  }, [entry.path]);

  useEffect(() => {
    directoryRequestRef.current += 1;
    directoryCacheRef.current.clear();
    setPicker(null);
  }, [directoryVersion, rootPath]);

  useEffect(() => {
    let alive = true;
    const cacheKey = `${rootPath}\0${entry.path}\0${contentVersion}\0${activeDocument.revision}`;
    const cached = symbolCacheRef.current.get(cacheKey);
    if (cached) {
      setSymbols(cached);
      return;
    }
    if (!text) {
      setSymbols([]);
      return;
    }
    setSymbols([]);
    requestSymbols(entry.name, text)
      .then((next) => {
        if (!alive) return;
        const cache = symbolCacheRef.current;
        cache.set(cacheKey, next);
        while (cache.size > SYMBOL_CACHE_LIMIT) {
          const first = cache.keys().next().value;
          if (first === undefined) break;
          cache.delete(first);
        }
        setSymbols(next);
      })
      .catch(() => {
        if (alive) setSymbols([]);
      });
    return () => {
      alive = false;
    };
  }, [activeDocument.revision, contentVersion, entry.name, entry.path, rootPath, text]);

  useEffect(() => {
    if (!picker) return;
    const close = (event: PointerEvent) => {
      const target = event.target;
      if (target instanceof Node && barRef.current?.parentElement?.contains(target)) return;
      setPicker(null);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setPicker(null);
    };
    const onResize = () => setPicker(null);
    window.addEventListener("pointerdown", close);
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("pointerdown", close);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
    };
  }, [picker]);

  useEffect(() => {
    if (!picker || (picker.kind === "path" && directoryLoading)) return;
    const frame = window.requestAnimationFrame(() => {
      const list = pickerListRef.current;
      const target = list?.querySelector<HTMLButtonElement>("button.active")
        ?? list?.querySelector<HTMLButtonElement>("button");
      target?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [directoryLoading, directoryPage?.entries.length, picker, symbols.length]);

  const symbolTrail = useMemo(() => activeSymbolTrail(symbols, cursorLine), [cursorLine, symbols]);

  function pickerPosition(button: HTMLButtonElement): PickerPosition {
    const barWidth = barRef.current?.clientWidth ?? PICKER_MAX_WIDTH;
    const width = Math.max(220, Math.min(PICKER_MAX_WIDTH, barWidth - 8));
    const left = Math.max(4, Math.min(button.offsetLeft, barWidth - width - 4));
    const center = button.offsetLeft + button.offsetWidth / 2 - left;
    return { left, width, arrowLeft: Math.max(12, Math.min(width - 12, center)) };
  }

  function readDirectory(dir: string, offset = 0): Promise<DirectoryPage> {
    const cacheKey = `${dir}\0${offset}`;
    const cached = directoryCacheRef.current.get(cacheKey);
    if (cached) return cached;
    const pending = workDir(rootPath, dir, offset, DIRECTORY_PAGE_SIZE)
      .then((listing) => ({
        entries: listing.entries,
        hasMore: listing.has_more,
        nextOffset: listing.offset + listing.entries.length,
      }))
      .catch((error) => {
        directoryCacheRef.current.delete(cacheKey);
        throw error;
      });
    directoryCacheRef.current.set(cacheKey, pending);
    if (directoryCacheRef.current.size > 48) {
      const first = directoryCacheRef.current.keys().next().value;
      if (first !== undefined) directoryCacheRef.current.delete(first);
    }
    return pending;
  }

  async function showDirectory(dir: string, position?: PickerPosition) {
    const current = picker?.kind === "path" ? picker : null;
    const placement = position ?? (current
      ? { left: current.left, width: current.width, arrowLeft: current.arrowLeft }
      : { left: 4, width: 320, arrowLeft: 20 });
    const request = ++directoryRequestRef.current;
    setPicker({ kind: "path", dir, ...placement });
    setDirectoryPage(null);
    setDirectoryLoading(true);
    setDirectoryError("");
    try {
      const page = await readDirectory(dir);
      if (request !== directoryRequestRef.current) return;
      setDirectoryPage(page);
    } catch (error) {
      if (request !== directoryRequestRef.current) return;
      setDirectoryPage(null);
      setDirectoryError(String(error));
    } finally {
      if (request === directoryRequestRef.current) setDirectoryLoading(false);
    }
  }

  function openPathPicker(event: ReactMouseEvent<HTMLButtonElement>, dir: string) {
    event.stopPropagation();
    void showDirectory(dir, pickerPosition(event.currentTarget));
  }

  function openSymbolPicker(event: ReactMouseEvent<HTMLButtonElement>) {
    event.stopPropagation();
    setPicker({ kind: "symbols", ...pickerPosition(event.currentTarget) });
  }

  async function loadMoreDirectory() {
    if (!picker || picker.kind !== "path" || !directoryPage?.hasMore || directoryLoading) return;
    setDirectoryLoading(true);
    setDirectoryError("");
    try {
      const next = await readDirectory(picker.dir, directoryPage.nextOffset);
      setDirectoryPage({
        entries: [...directoryPage.entries, ...next.entries],
        hasMore: next.hasMore,
        nextOffset: next.nextOffset,
      });
    } catch (error) {
      setDirectoryError(String(error));
    } finally {
      setDirectoryLoading(false);
    }
  }

  function onPickerKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    const rows = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button"));
    if (rows.length === 0) return;
    event.preventDefault();
    const current = rows.indexOf(document.activeElement as HTMLButtonElement);
    const nextIndex = event.key === "Home"
      ? 0
      : event.key === "End"
        ? rows.length - 1
        : event.key === "ArrowDown"
          ? Math.min(rows.length - 1, Math.max(0, current + 1))
          : Math.max(0, current < 0 ? rows.length - 1 : current - 1);
    rows[nextIndex].focus();
  }

  const pickerStyle = picker
    ? ({
        left: picker.left,
        width: picker.width,
        "--breadcrumb-picker-arrow-left": `${picker.arrowLeft}px`,
      } as CSSProperties)
    : undefined;

  return (
    <div className="files-editor-breadcrumb-shell">
      <div className="files-editor-breadcrumb" ref={barRef} aria-label={t("files.breadcrumbAria")}>
        <button type="button" className="files-breadcrumb-item root" onClick={(event) => openPathPicker(event, "")}>
          <WorkFileIcon entry={{ name: rootName, is_dir: true }} collapsed={false} />
          <span>{rootName}</span>
        </button>
        {pathSegments.map((segment, index) => (
          <span className="files-breadcrumb-part" key={segment.path}>
            <Codicon name="chevronRight" className="files-breadcrumb-separator" />
            <button
              type="button"
              className={`files-breadcrumb-item${index === pathSegments.length - 1 ? " current" : ""}`}
              title={segment.path}
              onClick={(event) => openPathPicker(event, parentPath(segment.path))}
            >
              {!segment.isDir && <WorkFileIcon entry={entry} collapsed />}
              <span>{segment.name}</span>
            </button>
          </span>
        ))}
        {symbolTrail.map((symbol) => (
          <span className="files-breadcrumb-part symbol" key={`${symbol.line}:${symbol.name}`}>
            <Codicon name="chevronRight" className="files-breadcrumb-separator" />
            <button type="button" className="files-breadcrumb-item symbol current" onClick={openSymbolPicker}>
              <Codicon name={symbolIcon(symbol.kind)} className={`breadcrumb-symbol-icon kind-${symbol.kind}`} />
              <span>{symbol.name}</span>
            </button>
          </span>
        ))}
      </div>

      {picker && (
        <div className="files-breadcrumb-picker" style={pickerStyle} role="dialog">
          {picker.kind === "path" ? (
            <div
              className="files-breadcrumb-picker-list"
              ref={pickerListRef}
              role="listbox"
              onKeyDown={onPickerKeyDown}
            >
              {picker.dir && (
                <button type="button" className="files-breadcrumb-picker-row parent" role="option" onClick={() => showDirectory(parentPath(picker.dir))}>
                  <Codicon name="chevronLeft" />
                  <span>{t("files.breadcrumbParent")}</span>
                </button>
              )}
              {directoryPage?.entries.map((item) => (
                <button
                  type="button"
                  className={`files-breadcrumb-picker-row${item.path === entry.path ? " active" : ""}`}
                  role="option"
                  key={item.path}
                  title={item.path}
                  onClick={() => {
                    if (item.is_dir) void showDirectory(item.path);
                    else {
                      onOpenFile(item.path);
                      setPicker(null);
                    }
                  }}
                >
                  {item.is_dir ? (
                    <Codicon name="chevronRight" className="files-breadcrumb-directory-icon" />
                  ) : (
                    <WorkFileIcon entry={item} collapsed />
                  )}
                  <span>{item.name}</span>
                  {item.status && <span className="files-breadcrumb-picker-status">{item.status}</span>}
                </button>
              ))}
              {!directoryLoading && !directoryError && directoryPage?.entries.length === 0 && (
                <div className="files-breadcrumb-picker-message">{t("common.emptyDir")}</div>
              )}
              {directoryError && <div className="files-breadcrumb-picker-message error">{directoryError}</div>}
              {directoryPage?.hasMore && (
                <button type="button" className="files-breadcrumb-picker-row more" role="option" onClick={loadMoreDirectory}>
                  <Codicon name="more" />
                  <span>{t("files.breadcrumbLoadMore")}</span>
                </button>
              )}
              {directoryLoading && <div className="files-breadcrumb-picker-message">{t("common.loading")}</div>}
            </div>
          ) : (
            <div
              className="files-breadcrumb-picker-list symbols"
              ref={pickerListRef}
              role="listbox"
              onKeyDown={onPickerKeyDown}
            >
              {symbols.map((symbol) => (
                <button
                  type="button"
                  className={`files-breadcrumb-picker-row symbol${symbolTrail.at(-1)?.line === symbol.line ? " active" : ""}`}
                  role="option"
                  key={`${symbol.line}:${symbol.name}`}
                  title={`${symbol.name} · ${t("files.breadcrumbLine", { line: symbol.line })}`}
                  style={{ paddingLeft: 8 + (symbol.level - 1) * 12 }}
                  onClick={() => {
                    onNavigateLine(symbol.line);
                    setPicker(null);
                  }}
                >
                  <Codicon name={symbolIcon(symbol.kind)} className={`breadcrumb-symbol-icon kind-${symbol.kind}`} />
                  <span>{symbol.name}</span>
                  <span className="files-breadcrumb-picker-line">{symbol.line}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
