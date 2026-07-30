import type { CreationLine, DraftAttachment, WebWork, WorkCreationConfig } from "../types";

const NOVEL_EXTENSIONS = new Set(["txt", "md", "markdown", "mdx", "doc", "docx", "pdf"]);

function cleanName(value: string) {
  return value
    .replace(/[\\/:*?"<>|]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[. ]+$/g, "")
    .slice(0, 40);
}

function attachmentTitle(attachments: DraftAttachment[]) {
  for (const attachment of attachments) {
    const dot = attachment.name.lastIndexOf(".");
    if (dot <= 0) continue;
    if (!NOVEL_EXTENSIONS.has(attachment.name.slice(dot + 1).toLowerCase())) continue;
    const title = cleanName(attachment.name.slice(0, dot));
    if (title) return title;
  }
  return "";
}

function promptTitle(prompt: string) {
  const value = prompt.trim();
  if (!value) return "";
  const marked = value.match(/[《「『“]([^》」』”\n]{1,40})[》」』”]/)?.[1]
    ?? value.match(/["']([^"'\n]{1,40})["']/)?.[1];
  if (marked) return cleanName(marked);

  const firstSentence = value.split(/\r?\n/, 1)[0]?.split(/[。！？!?]/, 1)[0]?.trim() ?? "";
  const source = firstSentence.match(/^(.{1,30}?)(?:制作|改编|做|画)成(?:一部|一个)?/)?.[1]
    ?.replace(/^(?:请|麻烦|帮我|帮忙|开始|把|将)/, "")
    .trim();
  if (source) return cleanName(source);
  return cleanName(firstSentence.replace(/^(?:请|麻烦|帮我|帮忙|开始)/, "").trim());
}

export function createWebWork(
  line: CreationLine,
  prompt: string,
  attachments: DraftAttachment[],
  creationConfig?: WorkCreationConfig,
): WebWork {
  return {
    id: crypto.randomUUID(),
    name: attachmentTitle(attachments) || promptTitle(prompt) || "unnamed",
    line,
    prompt: prompt.trim(),
    ...(creationConfig ? { creationConfig } : {}),
    attachments: attachments.map(({ id, name, size, type, assetId }) => ({
      id,
      name,
      size,
      type,
      ...(assetId ? { assetId } : {}),
    })),
    createdAt: new Date().toISOString(),
    cloudState: "local",
  };
}

const workKey = (id: string) => `anime-armory.web.work.${id}`;

export function saveWork(work: WebWork) {
  const value = JSON.stringify(work);
  localStorage.setItem(workKey(work.id), value);
  sessionStorage.removeItem(workKey(work.id));
}

export function loadWork(id: string): WebWork | null {
  const key = workKey(id);
  const raw = localStorage.getItem(key) ?? sessionStorage.getItem(key);
  if (!raw) return null;
  try {
    const work = JSON.parse(raw) as WebWork;
    if (!localStorage.getItem(key)) {
      localStorage.setItem(key, raw);
      sessionStorage.removeItem(key);
    }
    return work;
  } catch {
    return null;
  }
}

export function removeWork(id: string) {
  const key = workKey(id);
  localStorage.removeItem(key);
  sessionStorage.removeItem(key);
}

export function workStorageKey(id: string) {
  return workKey(id);
}
