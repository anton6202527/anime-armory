type DecodeRequest = {
  type: "decode";
  id: number;
  source: string;
  maxDimension: number;
};

type CancelRequest = {
  type: "cancel";
  id: number;
};

type WorkerRequest = DecodeRequest | CancelRequest;

type WorkerScope = {
  onmessage: ((event: MessageEvent<WorkerRequest>) => void) | null;
  postMessage: (message: unknown, transfer?: Transferable[]) => void;
};

const scope = globalThis as unknown as WorkerScope;
const controllers = new Map<number, AbortController>();

function isAnimatedWebp(bytes: Uint8Array): boolean {
  if (bytes.length < 16) return false;
  const hasBytes = (offset: number, values: number[]) =>
    values.every((value, index) => bytes[offset + index] === value);
  if (!hasBytes(0, [82, 73, 70, 70]) || !hasBytes(8, [87, 69, 66, 80])) return false;
  for (let offset = 12; offset + 4 <= bytes.length; offset += 1) {
    if (
      hasBytes(offset, [65, 78, 73, 77]) ||
      hasBytes(offset, [65, 78, 77, 70])
    ) return true;
  }
  return false;
}

async function decode(request: DecodeRequest): Promise<void> {
  if (typeof createImageBitmap !== "function") {
    scope.postMessage({ id: request.id, status: "native", reason: "createImageBitmap unavailable" });
    return;
  }

  const controller = new AbortController();
  controllers.set(request.id, controller);
  let bitmap: ImageBitmap | null = null;
  try {
    const response = await fetch(request.source, { signal: controller.signal, cache: "default" });
    if (!response.ok) throw new Error(`media request failed (${response.status})`);
    const blob = await response.blob();
    if (blob.type === "image/webp") {
      const probe = new Uint8Array(await blob.slice(0, Math.min(blob.size, 1024 * 1024)).arrayBuffer());
      if (isAnimatedWebp(probe)) {
        scope.postMessage({ id: request.id, status: "native", reason: "animated WebP" });
        return;
      }
    }
    if (controller.signal.aborted) return;

    try {
      bitmap = await createImageBitmap(blob, { imageOrientation: "from-image" });
    } catch {
      bitmap = await createImageBitmap(blob);
    }
    const originalWidth = bitmap.width;
    const originalHeight = bitmap.height;
    const maxDimension = Math.max(0, Math.floor(request.maxDimension));
    if (maxDimension > 0 && Math.max(bitmap.width, bitmap.height) > maxDimension) {
      const scale = maxDimension / Math.max(bitmap.width, bitmap.height);
      const width = Math.max(1, Math.round(bitmap.width * scale));
      const height = Math.max(1, Math.round(bitmap.height * scale));
      const resized = await createImageBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, {
        resizeWidth: width,
        resizeHeight: height,
        resizeQuality: "high",
      });
      bitmap.close();
      bitmap = resized;
    }
    if (controller.signal.aborted) {
      bitmap.close();
      return;
    }

    scope.postMessage(
      {
        id: request.id,
        status: "decoded",
        bitmap,
        width: bitmap.width,
        height: bitmap.height,
        originalWidth,
        originalHeight,
      },
      [bitmap],
    );
    bitmap = null;
  } catch (error) {
    if (!controller.signal.aborted) {
      scope.postMessage({
        id: request.id,
        status: "error",
        error: error instanceof Error ? error.message : String(error),
      });
    }
  } finally {
    bitmap?.close();
    controllers.delete(request.id);
  }
}

scope.onmessage = (event) => {
  const request = event.data;
  if (request.type === "cancel") {
    controllers.get(request.id)?.abort();
    return;
  }
  void decode(request);
};
