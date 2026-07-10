import ImageDecodeWorker from "./imageDecode.worker?worker";

export type DecodedImageResult =
  | {
      kind: "bitmap";
      bitmap: ImageBitmap;
      width: number;
      height: number;
      originalWidth: number;
      originalHeight: number;
    }
  | { kind: "native"; reason: string };

type WorkerResponse =
  | ({ id: number; status: "decoded" } & Omit<Extract<DecodedImageResult, { kind: "bitmap" }>, "kind">)
  | { id: number; status: "native"; reason: string }
  | { id: number; status: "error"; error: string };

type DecodeJob = {
  id: number;
  source: string;
  maxDimension: number;
  resolve: (result: DecodedImageResult) => void;
  reject: (error: Error) => void;
  slot?: WorkerSlot;
};

type WorkerSlot = {
  worker: Worker;
  job: DecodeJob | null;
};

type DecodeRequest = {
  promise: Promise<DecodedImageResult>;
  cancel: () => void;
};

type CacheEntry = Extract<DecodedImageResult, { kind: "bitmap" }> & {
  bytes: number;
};

const CACHE_MAX_BYTES = 96 * 1024 * 1024;
const CACHE_MAX_ENTRIES = 72;

class DecodeWorkerPool {
  private nextId = 1;
  private readonly queue: DecodeJob[] = [];
  private readonly jobs = new Map<number, DecodeJob>();
  private readonly slots: WorkerSlot[] = [];

  constructor() {
    const concurrency = (navigator.hardwareConcurrency || 4) >= 8 ? 2 : 1;
    for (let index = 0; index < concurrency; index += 1) this.slots.push(this.createSlot());
  }

  decode(source: string, maxDimension: number): DecodeRequest {
    let job: DecodeJob;
    const promise = new Promise<DecodedImageResult>((resolve, reject) => {
      job = {
        id: this.nextId++,
        source,
        maxDimension,
        resolve,
        reject,
      };
      this.jobs.set(job.id, job);
      this.queue.push(job);
      this.dispatch();
    });
    return {
      promise,
      cancel: () => this.cancel(job.id),
    };
  }

  private createSlot(): WorkerSlot {
    const worker = new ImageDecodeWorker();
    const slot: WorkerSlot = { worker, job: null };
    const handleMessage = (event: MessageEvent<WorkerResponse>) => this.complete(slot, event.data);
    const handleError = (event: ErrorEvent) => {
      const active = slot.job;
      if (active) {
        this.jobs.delete(active.id);
        active.reject(new Error(event.message || "image decode worker failed"));
      }
      slot.worker.terminate();
      slot.worker = new ImageDecodeWorker();
      slot.worker.onmessage = handleMessage;
      slot.worker.onerror = handleError;
      slot.job = null;
      this.dispatch();
    };
    worker.onmessage = handleMessage;
    worker.onerror = handleError;
    return slot;
  }

  private dispatch(): void {
    for (const slot of this.slots) {
      if (slot.job) continue;
      const job = this.queue.shift();
      if (!job) return;
      slot.job = job;
      job.slot = slot;
      slot.worker.postMessage({
        type: "decode",
        id: job.id,
        source: job.source,
        maxDimension: job.maxDimension,
      });
    }
  }

  private complete(slot: WorkerSlot, response: WorkerResponse): void {
    const job = slot.job;
    if (!job || job.id !== response.id) return;
    this.jobs.delete(job.id);
    slot.job = null;
    if (response.status === "decoded") {
      job.resolve({
        kind: "bitmap",
        bitmap: response.bitmap,
        width: response.width,
        height: response.height,
        originalWidth: response.originalWidth,
        originalHeight: response.originalHeight,
      });
    } else if (response.status === "native") {
      job.resolve({ kind: "native", reason: response.reason });
    } else {
      job.reject(new Error(response.error));
    }
    this.dispatch();
  }

  private cancel(id: number): void {
    const job = this.jobs.get(id);
    if (!job) return;
    this.jobs.delete(id);
    const queueIndex = this.queue.findIndex((item) => item.id === id);
    if (queueIndex >= 0) this.queue.splice(queueIndex, 1);
    if (job.slot) {
      job.slot.worker.postMessage({ type: "cancel", id });
      job.slot.job = null;
    }
    job.reject(new DOMException("Image decode cancelled", "AbortError"));
    this.dispatch();
  }
}

type SharedDecode = {
  refs: number;
  request: DecodeRequest;
  promise: Promise<DecodedImageResult>;
};

export type ImageDecodeLease = {
  promise: Promise<DecodedImageResult>;
  release: () => void;
};

class ImageDecodeRuntime {
  private pool: DecodeWorkerPool | null = null;
  private readonly cache = new Map<string, CacheEntry>();
  private readonly inflight = new Map<string, SharedDecode>();
  private cacheBytes = 0;

  acquire(source: string, maxDimension = 0): ImageDecodeLease {
    const key = `${source}\0${Math.max(0, Math.floor(maxDimension))}`;
    const cached = this.cache.get(key);
    if (cached) {
      this.cache.delete(key);
      this.cache.set(key, cached);
      return { promise: Promise.resolve(cached), release: () => {} };
    }

    let shared = this.inflight.get(key);
    if (!shared) {
      this.pool ??= new DecodeWorkerPool();
      const request = this.pool.decode(source, maxDimension);
      const promise = request.promise.then((result) => {
        if (result.kind === "bitmap") this.store(key, result);
        return result;
      }).finally(() => {
        if (this.inflight.get(key)?.promise === promise) this.inflight.delete(key);
      });
      shared = { refs: 0, request, promise };
      this.inflight.set(key, shared);
    }
    shared.refs += 1;
    let released = false;
    return {
      promise: shared.promise,
      release: () => {
        if (released) return;
        released = true;
        const current = this.inflight.get(key);
        if (!current) return;
        current.refs -= 1;
        if (current.refs <= 0) {
          this.inflight.delete(key);
          current.request.cancel();
        }
      },
    };
  }

  private store(key: string, result: Extract<DecodedImageResult, { kind: "bitmap" }>): void {
    const old = this.cache.get(key);
    if (old) {
      this.cacheBytes -= old.bytes;
      old.bitmap.close();
    }
    const entry: CacheEntry = {
      ...result,
      bytes: result.width * result.height * 4,
    };
    this.cache.set(key, entry);
    this.cacheBytes += entry.bytes;
    while (this.cache.size > 1 && (this.cache.size > CACHE_MAX_ENTRIES || this.cacheBytes > CACHE_MAX_BYTES)) {
      const oldestKey = this.cache.keys().next().value as string | undefined;
      if (!oldestKey || oldestKey === key) break;
      const oldest = this.cache.get(oldestKey);
      this.cache.delete(oldestKey);
      if (oldest) {
        this.cacheBytes -= oldest.bytes;
        oldest.bitmap.close();
      }
    }
  }
}

export const imageDecodeRuntime = new ImageDecodeRuntime();
