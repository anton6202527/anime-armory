import type { PendingAttachment } from "../types";

const files = new Map<string, File>();
const DATABASE_NAME = "labutv-local-assets";
const STORE_NAME = "files";

function database(): Promise<IDBDatabase | null> {
  if (!("indexedDB" in window)) return Promise.resolve(null);
  return new Promise((resolve) => {
    const request = indexedDB.open(DATABASE_NAME, 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE_NAME)) request.result.createObjectStore(STORE_NAME);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => resolve(null);
  });
}

async function persistFile(id: string, file: File) {
  const db = await database();
  if (!db) return;
  await new Promise<void>((resolve) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).put(file, id);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => resolve();
  });
  db.close();
}

export function registerLocalFiles(attachments: PendingAttachment[]) {
  for (const attachment of attachments) {
    files.set(attachment.id, attachment.file);
    void persistFile(attachment.id, attachment.file);
  }
}

export async function localFile(id: string): Promise<File | undefined> {
  const cached = files.get(id);
  if (cached) return cached;
  const db = await database();
  if (!db) return undefined;
  const file = await new Promise<File | undefined>((resolve) => {
    const request = db.transaction(STORE_NAME, "readonly").objectStore(STORE_NAME).get(id);
    request.onsuccess = () => resolve(request.result instanceof File ? request.result : undefined);
    request.onerror = () => resolve(undefined);
  });
  db.close();
  if (file) files.set(id, file);
  return file;
}

export async function removeLocalFiles(ids: string[]) {
  if (!ids.length) return;
  ids.forEach((id) => files.delete(id));
  const db = await database();
  if (!db) return;
  await new Promise<void>((resolve) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    ids.forEach((id) => store.delete(id));
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => resolve();
    transaction.onabort = () => resolve();
  });
  db.close();
}
