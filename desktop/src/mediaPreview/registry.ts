export type ImagePreviewStrategy = "worker-bitmap" | "native-image";

export interface ImagePreviewPlugin {
  id: string;
  priority: number;
  strategy: ImagePreviewStrategy;
  matches: (source: string) => boolean;
}

const plugins: ImagePreviewPlugin[] = [];

function sourceExtension(source: string): string {
  try {
    const url = new URL(source, window.location.href);
    const path = url.searchParams.get("path") || url.pathname;
    const clean = path.split(/[?#]/, 1)[0];
    const dot = clean.lastIndexOf(".");
    return dot < 0 ? "" : clean.slice(dot + 1).toLowerCase();
  } catch {
    const clean = source.split(/[?#]/, 1)[0];
    const dot = clean.lastIndexOf(".");
    return dot < 0 ? "" : clean.slice(dot + 1).toLowerCase();
  }
}

export function registerImagePreviewPlugin(plugin: ImagePreviewPlugin): () => void {
  const existing = plugins.findIndex((item) => item.id === plugin.id);
  if (existing >= 0) plugins.splice(existing, 1);
  plugins.push(plugin);
  plugins.sort((a, b) => b.priority - a.priority);
  return () => {
    const index = plugins.findIndex((item) => item.id === plugin.id);
    if (index >= 0) plugins.splice(index, 1);
  };
}

export function resolveImagePreviewPlugin(source: string): ImagePreviewPlugin {
  return plugins.find((plugin) => plugin.matches(source)) ?? nativeImagePlugin;
}

const workerBitmapPlugin: ImagePreviewPlugin = {
  id: "worker-bitmap",
  priority: 100,
  strategy: "worker-bitmap",
  matches: (source) => new Set(["png", "jpg", "jpeg", "webp"]).has(sourceExtension(source)),
};

const nativeImagePlugin: ImagePreviewPlugin = {
  id: "native-image",
  priority: 0,
  strategy: "native-image",
  // SVG and animated formats stay native so animation/vector semantics are kept.
  matches: () => true,
};

registerImagePreviewPlugin(workerBitmapPlugin);
registerImagePreviewPlugin(nativeImagePlugin);

