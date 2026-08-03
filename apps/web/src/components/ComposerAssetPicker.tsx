import {
  Check,
  ChevronLeft,
  ChevronRight,
  File,
  FileAudio,
  FileImage,
  FileText,
  FileUp,
  Folder,
  Images,
  MoreHorizontal,
  Plus,
  Search,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

export interface ComposerAssetItem {
  id: string;
  name: string;
  size: number;
  type: string;
}

type AssetCategory = "全部" | "其它" | "人物" | "场景" | "物品" | "风格" | "音效";

interface AssetFolder {
  id: string;
  name: string;
  createdAt: string;
}

const ASSET_CATEGORIES: AssetCategory[] = ["全部", "其它", "人物", "场景", "物品", "风格", "音效"];
const UNFILED_FOLDER_ID = "unfiled";
const FOLDERS_STORAGE_KEY = "anime-armory.asset-folders.v1";
const ASSIGNMENTS_STORAGE_KEY = "anime-armory.asset-folder-assignments.v1";
const PAGE_SIZE = 20;

function today() {
  return new Date().toISOString().slice(0, 10);
}

function defaultFolders(): AssetFolder[] {
  return [{ id: UNFILED_FOLDER_ID, name: "待分类资产", createdAt: today() }];
}

function readFolders(): AssetFolder[] {
  try {
    const stored = localStorage.getItem(FOLDERS_STORAGE_KEY);
    if (stored === null) return defaultFolders();
    const parsed = JSON.parse(stored) as AssetFolder[];
    const valid = parsed.filter((folder) => folder && typeof folder.id === "string" && typeof folder.name === "string" && typeof folder.createdAt === "string");
    return valid;
  } catch {
    return defaultFolders();
  }
}

function readAssignments(): Record<string, string> {
  try {
    const parsed = JSON.parse(localStorage.getItem(ASSIGNMENTS_STORAGE_KEY) ?? "{}") as Record<string, unknown>;
    return Object.fromEntries(Object.entries(parsed).filter((entry): entry is [string, string] => typeof entry[1] === "string"));
  } catch {
    return {};
  }
}

function categoryFor(asset: ComposerAssetItem): Exclude<AssetCategory, "全部"> {
  const value = `${asset.name} ${asset.type}`.toLocaleLowerCase();
  if (asset.type.startsWith("audio/") || /音效|配乐|music|audio|sound|voice/.test(value)) return "音效";
  if (/人物|角色|人像|肖像|character|portrait|person/.test(value)) return "人物";
  if (/场景|环境|背景|scene|landscape|environment|background/.test(value)) return "场景";
  if (/物品|道具|产品|object|prop|product/.test(value)) return "物品";
  if (/风格|画风|style|mood|reference/.test(value)) return "风格";
  return "其它";
}

function assetIcon(asset: ComposerAssetItem): ReactNode {
  if (asset.type.startsWith("image/")) return <FileImage size={32} />;
  if (asset.type.startsWith("audio/")) return <FileAudio size={32} />;
  if (asset.type.startsWith("text/") || /json|markdown|pdf|document/.test(asset.type)) return <FileText size={32} />;
  return <File size={32} />;
}

function formatAssetSize(size: number) {
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(size / 1024))} KB`;
}

export function ComposerAssetPicker({
  assets,
  selectedIds,
  menuOpen,
  onMenuOpenChange,
  onUpload,
  onSelectionChange,
  buttonClassName = "composer-icon-button",
}: {
  assets: ComposerAssetItem[];
  selectedIds: string[];
  menuOpen: boolean;
  onMenuOpenChange: (open: boolean) => void;
  onUpload: (files: File[]) => Promise<string[]> | string[];
  onSelectionChange: (ids: string[]) => void;
  buttonClassName?: string;
}) {
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadFromLibraryRef = useRef(false);
  const uploadFolderRef = useRef(UNFILED_FOLDER_ID);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [draftSelection, setDraftSelection] = useState<string[]>(selectedIds);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<AssetCategory>("全部");
  const [activeFolderId, setActiveFolderId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [newMenuOpen, setNewMenuOpen] = useState(false);
  const [folderMenuId, setFolderMenuId] = useState<string | null>(null);
  const [createFolderOpen, setCreateFolderOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [toast, setToast] = useState("");
  const [folders, setFolders] = useState<AssetFolder[]>(readFolders);
  const [folderAssignments, setFolderAssignments] = useState<Record<string, string>>(readAssignments);

  useEffect(() => {
    if (!menuOpen) return;
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as globalThis.Node)) onMenuOpenChange(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onMenuOpenChange(false);
    };
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [menuOpen, onMenuOpenChange]);

  useEffect(() => {
    if (!libraryOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (createFolderOpen) setCreateFolderOpen(false);
      else if (folderMenuId) setFolderMenuId(null);
      else if (newMenuOpen) setNewMenuOpen(false);
      else setLibraryOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [createFolderOpen, folderMenuId, libraryOpen, newMenuOpen]);

  useEffect(() => {
    setFolderAssignments((current) => {
      const next = { ...current };
      let changed = false;
      for (const asset of assets) {
        if (!next[asset.id] || !folders.some((folder) => folder.id === next[asset.id])) {
          next[asset.id] = UNFILED_FOLDER_ID;
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [assets, folders]);

  useEffect(() => {
    localStorage.setItem(FOLDERS_STORAGE_KEY, JSON.stringify(folders));
  }, [folders]);

  useEffect(() => {
    localStorage.setItem(ASSIGNMENTS_STORAGE_KEY, JSON.stringify(folderAssignments));
  }, [folderAssignments]);

  useEffect(() => {
    setPage(1);
  }, [activeFolderId, category, query]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(""), 2200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  function chooseLocalFiles(fromLibrary: boolean) {
    uploadFromLibraryRef.current = fromLibrary;
    const targetFolderId = activeFolderId ?? UNFILED_FOLDER_ID;
    if (!folders.some((folder) => folder.id === targetFolderId)) {
      setFolders((current) => [...current, defaultFolders()[0]]);
    }
    uploadFolderRef.current = targetFolderId;
    onMenuOpenChange(false);
    setNewMenuOpen(false);
    setFolderMenuId(null);
    inputRef.current?.click();
  }

  function openLibrary() {
    setDraftSelection(selectedIds.filter((id) => assets.some((asset) => asset.id === id)));
    setQuery("");
    setCategory("全部");
    setActiveFolderId(null);
    setPage(1);
    setNewMenuOpen(false);
    setFolderMenuId(null);
    setCreateFolderOpen(false);
    onMenuOpenChange(false);
    setLibraryOpen(true);
  }

  async function handleFiles(files: File[]) {
    if (!files.length) return;
    const ids = await onUpload(files);
    if (uploadFromLibraryRef.current && ids.length) {
      setDraftSelection((current) => [...new Set([...current, ...ids])]);
      setFolderAssignments((current) => ({
        ...current,
        ...Object.fromEntries(ids.map((id) => [id, uploadFolderRef.current])),
      }));
    }
    uploadFromLibraryRef.current = false;
  }

  function createFolder() {
    const name = newFolderName.trim();
    if (!name) return;
    const existing = folders.find((folder) => folder.name.toLocaleLowerCase() === name.toLocaleLowerCase());
    if (existing) {
      setActiveFolderId(existing.id);
    } else {
      const folder = { id: crypto.randomUUID(), name, createdAt: today() };
      setFolders((current) => [...current, folder]);
      setActiveFolderId(folder.id);
    }
    setNewFolderName("");
    setCreateFolderOpen(false);
    setNewMenuOpen(false);
  }

  function assetsInFolder(folderId: string) {
    return assets.filter((asset) => (folderAssignments[asset.id] ?? UNFILED_FOLDER_ID) === folderId);
  }

  function publishFolder(folder: AssetFolder) {
    const publishable = assetsInFolder(folder.id);
    setFolderMenuId(null);
    if (!publishable.length) {
      setToast("没有可以发布项");
      return;
    }
    setDraftSelection((current) => [...new Set([...current, ...publishable.map((asset) => asset.id)])]);
    setToast(`已选择 ${publishable.length} 个发布项`);
  }

  function deleteFolder(folder: AssetFolder) {
    const assigned = assetsInFolder(folder.id);
    setFolderMenuId(null);
    if (folder.id === UNFILED_FOLDER_ID && assigned.length) {
      setToast("文件夹内还有资产，暂时不能删除");
      return;
    }
    setFolders((current) => {
      const remaining = current.filter((item) => item.id !== folder.id);
      if (assigned.length && !remaining.some((item) => item.id === UNFILED_FOLDER_ID)) remaining.unshift(defaultFolders()[0]);
      return remaining;
    });
    if (assigned.length) {
      setFolderAssignments((current) => ({
        ...current,
        ...Object.fromEntries(assigned.map((asset) => [asset.id, UNFILED_FOLDER_ID])),
      }));
    }
    if (activeFolderId === folder.id) setActiveFolderId(null);
    setToast("文件夹已删除");
  }

  const activeFolder = folders.find((folder) => folder.id === activeFolderId) ?? null;
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const entries = useMemo(() => {
    const visibleFolders = !activeFolderId && category === "全部"
      ? folders.filter((folder) => !normalizedQuery || folder.name.toLocaleLowerCase().includes(normalizedQuery))
      : [];
    const visibleAssets = assets.filter((asset) => {
      if (activeFolderId && (folderAssignments[asset.id] ?? UNFILED_FOLDER_ID) !== activeFolderId) return false;
      if (!activeFolderId && category === "全部" && !normalizedQuery) return false;
      if (category !== "全部" && categoryFor(asset) !== category) return false;
      return !normalizedQuery || asset.name.toLocaleLowerCase().includes(normalizedQuery);
    });
    return [
      ...visibleFolders.map((folder) => ({ kind: "folder" as const, folder })),
      ...visibleAssets.map((asset) => ({ kind: "asset" as const, asset })),
    ];
  }, [activeFolderId, assets, category, folderAssignments, folders, normalizedQuery]);
  const pageCount = Math.max(1, Math.ceil(entries.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const pageEntries = entries.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const selectedCount = draftSelection.filter((id) => assets.some((asset) => asset.id === id)).length;

  return (
    <div className="composer-asset-picker" ref={rootRef}>
      <input
        ref={inputRef}
        type="file"
        multiple
        hidden
        onChange={(event) => {
          const input = event.currentTarget;
          void handleFiles(Array.from(input.files ?? [])).finally(() => { input.value = ""; });
        }}
      />
      <button
        className={`${buttonClassName}${menuOpen ? " is-active" : ""}`}
        type="button"
        title="添加素材"
        aria-label="添加素材"
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        onClick={() => onMenuOpenChange(!menuOpen)}
      >
        <Plus size={20} strokeWidth={1.6} />
      </button>

      {menuOpen && (
        <div className="composer-asset-menu" role="menu" aria-label="添加素材">
          <button type="button" role="menuitem" onClick={() => chooseLocalFiles(false)}><FileUp size={17} /><span>本地上传</span></button>
          <button type="button" role="menuitem" onClick={openLibrary}><Images size={17} /><span>素材库添加</span></button>
        </div>
      )}

      {libraryOpen && createPortal(
        <div className="composer-asset-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setLibraryOpen(false); }}>
          <section className="composer-asset-dialog" role="dialog" aria-modal="true" aria-label="资产管理">
            <header>
              <strong>资产管理</strong>
              <button type="button" aria-label="关闭" onClick={() => setLibraryOpen(false)}><X size={18} /></button>
            </header>

            <div className="composer-asset-dialog-body">
              <div className="composer-asset-breadcrumb">
                <button type="button" onClick={() => setActiveFolderId(null)}>个人资产库</button>
                {activeFolder && <><ChevronRight size={14} /><span>{activeFolder.name}</span></>}
              </div>

              <div className="composer-asset-toolbar">
                <label>
                  <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="请输入搜索内容" aria-label="搜索资产" />
                  <Search size={16} />
                </label>
                <div className="composer-asset-new-wrap">
                  <button type="button" className="composer-asset-new-button" aria-expanded={newMenuOpen} onClick={() => setNewMenuOpen((open) => !open)}><Plus size={18} />新建</button>
                  {newMenuOpen && <div className="composer-asset-new-menu" role="menu">
                    <button type="button" role="menuitem" onClick={() => { setNewFolderName(""); setCreateFolderOpen(true); setNewMenuOpen(false); }}>新建文件夹</button>
                    <button type="button" role="menuitem" onClick={() => chooseLocalFiles(true)}>上传资产</button>
                  </div>}
                </div>
              </div>

              <nav className="composer-asset-categories" aria-label="资产分类">
                {ASSET_CATEGORIES.map((item) => <button key={item} type="button" className={category === item ? "is-active" : ""} onClick={() => setCategory(item)}>{item}</button>)}
              </nav>

              {pageEntries.length ? <div className="composer-asset-grid">
                {pageEntries.map((entry) => entry.kind === "folder" ? (
                  <article key={entry.folder.id} className="composer-asset-folder-card" onMouseLeave={() => setFolderMenuId(null)}>
                    <button type="button" className="composer-asset-folder-open" aria-label={`打开${entry.folder.name}`} onClick={() => { setFolderMenuId(null); setActiveFolderId(entry.folder.id); }}><Folder size={46} fill="currentColor" /></button>
                    <button type="button" className="composer-asset-folder-more" aria-label={`${entry.folder.name}更多操作`} aria-expanded={folderMenuId === entry.folder.id} onClick={() => setFolderMenuId((current) => current === entry.folder.id ? null : entry.folder.id)}><MoreHorizontal size={18} /></button>
                    {folderMenuId === entry.folder.id && <div className="composer-asset-folder-menu" role="menu"><button type="button" role="menuitem" onClick={() => deleteFolder(entry.folder)}>删除</button></div>}
                    <button type="button" className="composer-asset-folder-publish" onClick={() => publishFolder(entry.folder)}>发布</button>
                    <button type="button" className="composer-asset-folder-meta" onClick={() => { setFolderMenuId(null); setActiveFolderId(entry.folder.id); }}><b>{entry.folder.name}</b><small>{entry.folder.createdAt}</small></button>
                  </article>
                ) : (() => {
                  const selected = draftSelection.includes(entry.asset.id);
                  return <button key={entry.asset.id} type="button" className={`composer-asset-card${selected ? " is-selected" : ""}`} aria-pressed={selected} onClick={() => setDraftSelection((current) => selected ? current.filter((id) => id !== entry.asset.id) : [...current, entry.asset.id])}>
                    <span className="composer-asset-card-preview">{assetIcon(entry.asset)}<i>{selected && <Check size={15} />}</i></span>
                    <b>{entry.asset.name}</b>
                    <small>{categoryFor(entry.asset)} · {formatAssetSize(entry.asset.size)}</small>
                  </button>;
                })())}
              </div> : <div className="composer-asset-library-empty">
                <span>{activeFolder ? <Folder size={30} /> : <Images size={28} />}</span>
                <b>{normalizedQuery ? "没有匹配的资产" : activeFolder ? "文件夹内暂无资产" : "个人资产库暂无内容"}</b>
                <p>{normalizedQuery ? "换个关键词或分类试试。" : "上传图片、文本、音频或视频，之后可在创作时重复使用。"}</p>
                {!normalizedQuery && <button type="button" onClick={() => chooseLocalFiles(true)}><FileUp size={16} />上传资产</button>}
              </div>}
            </div>

            <footer>
              <div className="composer-asset-selection-actions">
                <span>已选择 {selectedCount} 项</span>
                <button type="button" onClick={() => setLibraryOpen(false)}>取消</button>
                <button type="button" className="is-primary" onClick={() => { onSelectionChange(draftSelection.filter((id) => assets.some((asset) => asset.id === id))); setLibraryOpen(false); }}>{selectedCount ? `添加 (${selectedCount})` : "完成"}</button>
              </div>
              <div className="composer-asset-pagination">
                <button type="button" disabled={safePage <= 1} aria-label="上一页" onClick={() => setPage((current) => Math.max(1, current - 1))}><ChevronLeft size={15} /></button>
                <b>{safePage}</b>
                <button type="button" disabled={safePage >= pageCount} aria-label="下一页" onClick={() => setPage((current) => Math.min(pageCount, current + 1))}><ChevronRight size={15} /></button>
                <span>{PAGE_SIZE}条/页</span>
              </div>
            </footer>

            {createFolderOpen && <div className="composer-folder-dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setCreateFolderOpen(false); }}>
              <section className="composer-folder-dialog" role="dialog" aria-modal="true" aria-label="新建文件夹">
                <header><strong>新建文件夹</strong><button type="button" aria-label="关闭" onClick={() => setCreateFolderOpen(false)}><X size={17} /></button></header>
                <label><span>文件夹名称</span><input autoFocus value={newFolderName} maxLength={40} placeholder="请输入文件夹名称" onChange={(event) => setNewFolderName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") createFolder(); }} /></label>
                <footer><button type="button" onClick={() => setCreateFolderOpen(false)}>取消</button><button type="button" className="is-primary" disabled={!newFolderName.trim()} onClick={createFolder}>创建</button></footer>
              </section>
            </div>}
            {toast && <div className="composer-asset-toast" role="status">{toast}</div>}
          </section>
        </div>,
        document.body,
      )}
    </div>
  );
}
