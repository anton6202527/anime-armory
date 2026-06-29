import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { getMediaPort, mediaUrl, readWorkFile, subscribeMediaPort, workTree } from "../api";
import type { SkillTreeEntry, WorkRoot } from "../types";

// The default "文件" tab for every work: a real directory tree of the work root
// (创作区/<line>/<work>/) on the left, with a preview pane on the right. Text via
// read_work_file; images / video / audio via the localhost media server (same
// channel the canvas thumbnails use). Re-reads on `refreshKey` (fs watch).
const IMG = new Set(["png", "jpg", "jpeg", "webp", "gif", "bmp"]);
const VIDEO = new Set(["mp4", "mov", "webm", "m4v"]);
const AUDIO = new Set(["wav", "mp3", "m4a", "aac", "flac", "ogg"]);

function ext(name: string): string {
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i + 1).toLowerCase();
}

export function FilesPane({ root, refreshKey }: { root: WorkRoot; refreshKey: number }) {
  const [tree, setTree] = useState<SkillTreeEntry[]>([]);
  const [sel, setSel] = useState<string>(""); // selected file's rel path
  const [text, setText] = useState<string>("");
  const [err, setErr] = useState<string>("");
  // re-render once the media server port is ready (else media URLs are empty)
  useSyncExternalStore(subscribeMediaPort, getMediaPort);

  useEffect(() => {
    let alive = true;
    workTree(root.path)
      .then((t) => alive && setTree(t))
      .catch(() => alive && setTree([]));
    return () => {
      alive = false;
    };
  }, [root.path, refreshKey]);

  const selEntry = useMemo(() => tree.find((e) => e.path === sel) || null, [tree, sel]);
  const kind = selEntry ? (IMG.has(ext(selEntry.name)) ? "img" : VIDEO.has(ext(selEntry.name)) ? "video" : AUDIO.has(ext(selEntry.name)) ? "audio" : "text") : "";
  const abs = selEntry ? `${root.path}/${selEntry.path}` : "";

  // load text previews (image/video/audio stream straight from the media server)
  useEffect(() => {
    setErr("");
    setText("");
    if (!selEntry || kind !== "text") return;
    let alive = true;
    readWorkFile(root.path, selEntry.path)
      .then((s) => alive && setText(s))
      .catch((e) => alive && setErr(String(e)));
    return () => {
      alive = false;
    };
  }, [root.path, sel, kind]);

  return (
    <div className="files-pane">
      <div className="files-tree">
        {tree.length === 0 && <div className="files-empty">空目录</div>}
        {tree.map((e) => (
          <div
            key={e.path}
            className={
              "tree-line" + (e.is_dir ? " dir" : "") + (e.path === sel ? " active" : "")
            }
            style={{ paddingLeft: 8 + e.depth * 14 }}
            onClick={() => !e.is_dir && setSel(e.path)}
            title={e.path}
          >
            <span className="tree-icon">{e.is_dir ? "📁" : "📄"}</span>
            {e.name}
          </div>
        ))}
      </div>
      <div className="files-preview">
        {!selEntry ? (
          <div className="files-empty">选择左侧文件查看（文本 / 图片 / 视频 / 音频）。</div>
        ) : kind === "img" ? (
          <div className="files-media">{abs && <img src={mediaUrl(abs)} alt={selEntry.name} />}</div>
        ) : kind === "video" ? (
          <div className="files-media">{abs && <video src={mediaUrl(abs)} controls preload="metadata" />}</div>
        ) : kind === "audio" ? (
          <div className="files-media"><audio src={mediaUrl(abs)} controls /></div>
        ) : err ? (
          <div className="files-empty">无法预览：{err}</div>
        ) : (
          <pre className="files-text">{text}</pre>
        )}
      </div>
    </div>
  );
}
