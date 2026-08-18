const DEFAULT_API_BASE_URL = "/api";
const DEFAULT_TIMEOUT_MS = 30_000;
const DEFAULT_JSON_LIMIT_BYTES = 32 * 1024 * 1024;
const DEFAULT_BINARY_LIMIT_BYTES = 512 * 1024 * 1024;
const ERROR_LIMIT_BYTES = 256 * 1024;

export type ApiErrorCode =
  | "invalid_api_base_url"
  | "network_error"
  | "request_cancelled"
  | "request_timeout"
  | "response_too_large"
  | "invalid_json"
  | string;

export class ApiError extends Error {
  readonly name = "ApiError";

  constructor(
    message: string,
    readonly status: number,
    readonly code: ApiErrorCode,
    readonly payload?: unknown,
  ) {
    super(message);
  }
}

export interface ApiRequestInit extends RequestInit {
  /** Includes connection time and response-body download time. */
  timeoutMs?: number;
  /** Rejects a response before retaining more than this many bytes in memory. */
  maxResponseBytes?: number;
}

type ApiResponseBytes = {
  bytes: Uint8Array;
  contentType: string;
  status: number;
};

function normalizeApiBaseUrl(value: string | undefined): string {
  const candidate = value?.trim() || DEFAULT_API_BASE_URL;
  if (/^https?:\/\//i.test(candidate)) {
    try {
      const url = new URL(candidate);
      if (url.username || url.password) throw new Error("credentials are not allowed");
      return url.toString().replace(/\/+$/, "");
    } catch {
      throw new ApiError("VITE_API_BASE_URL 不是有效的 HTTP(S) 地址", 0, "invalid_api_base_url");
    }
  }
  if (/^[a-z][a-z\d+.-]*:/i.test(candidate) || candidate.startsWith("//")) {
    throw new ApiError("VITE_API_BASE_URL 只支持同源路径或 HTTP(S) 地址", 0, "invalid_api_base_url");
  }
  const pathname = `/${candidate.replace(/^\/+/, "")}`.replace(/\/+$/, "");
  return pathname || "";
}

export const API_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

export function apiUrl(path: string): string {
  if (!path || /^[a-z][a-z\d+.-]*:/i.test(path) || path.startsWith("//")) {
    throw new ApiError("API 请求路径必须是后端内的相对路径", 0, "invalid_api_base_url");
  }
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

function errorPayload(bytes: Uint8Array, contentType: string): unknown {
  if (!bytes.byteLength) return null;
  const text = new TextDecoder().decode(bytes);
  if (contentType.includes("json")) {
    try {
      return JSON.parse(text) as unknown;
    } catch {
      return null;
    }
  }
  return text.trim().slice(0, 1_000);
}

function serverError(status: number, payload: unknown): ApiError {
  const record = payload && typeof payload === "object" && !Array.isArray(payload)
    ? payload as Record<string, unknown>
    : null;
  const nested = record?.error && typeof record.error === "object" && !Array.isArray(record.error)
    ? record.error as Record<string, unknown>
    : null;
  const code = typeof nested?.code === "string"
    ? nested.code
    : typeof record?.code === "string"
      ? record.code
      : `http_${status}`;
  const message = typeof nested?.message === "string"
    ? nested.message
    : typeof record?.message === "string"
      ? record.message
      : typeof payload === "string" && payload
        ? payload
        : `后端请求失败（${status}）`;
  return new ApiError(message, status, code, payload);
}

async function readResponseBytes(response: Response, maxBytes: number): Promise<Uint8Array> {
  const declaredLength = Number(response.headers.get("content-length") ?? Number.NaN);
  if (Number.isFinite(declaredLength) && declaredLength > maxBytes) {
    await response.body?.cancel().catch(() => undefined);
    throw new ApiError("后端响应超过浏览器安全上限", response.status, "response_too_large");
  }
  if (!response.body) return new Uint8Array();

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let byteLength = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      byteLength += value.byteLength;
      if (byteLength > maxBytes) {
        await reader.cancel().catch(() => undefined);
        throw new ApiError("后端响应超过浏览器安全上限", response.status, "response_too_large");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }

  const bytes = new Uint8Array(byteLength);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return bytes;
}

async function requestBytes(path: string, options: ApiRequestInit, defaultLimit: number): Promise<ApiResponseBytes> {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    maxResponseBytes = defaultLimit,
    signal: callerSignal,
    headers: initialHeaders,
    ...init
  } = options;
  const controller = new AbortController();
  let timedOut = false;
  const abortFromCaller = () => controller.abort(callerSignal?.reason);
  if (callerSignal?.aborted) abortFromCaller();
  else callerSignal?.addEventListener("abort", abortFromCaller, { once: true });
  const timer = globalThis.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, Math.max(1, timeoutMs));

  try {
    const response = await fetch(apiUrl(path), {
      ...init,
      headers: new Headers(initialHeaders),
      credentials: init.credentials ?? "include",
      signal: controller.signal,
    });
    const contentType = response.headers.get("content-type")?.toLocaleLowerCase() ?? "";
    const bytes = await readResponseBytes(response, response.ok ? maxResponseBytes : ERROR_LIMIT_BYTES);
    if (!response.ok) throw serverError(response.status, errorPayload(bytes, contentType));
    return { bytes, contentType, status: response.status };
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (callerSignal?.aborted) {
      throw new ApiError("请求已取消", 0, "request_cancelled");
    }
    if (timedOut) {
      throw new ApiError("连接后端服务超时", 504, "request_timeout");
    }
    throw new ApiError("无法连接 LabuTV 后端服务", 0, "network_error");
  } finally {
    globalThis.clearTimeout(timer);
    callerSignal?.removeEventListener("abort", abortFromCaller);
  }
}

export async function apiJson<T>(path: string, options: ApiRequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("accept")) headers.set("accept", "application/json");
  const response = await requestBytes(path, { ...options, headers }, DEFAULT_JSON_LIMIT_BYTES);
  if (response.status === 204 || !response.bytes.byteLength) return undefined as T;
  try {
    return JSON.parse(new TextDecoder().decode(response.bytes)) as T;
  } catch {
    throw new ApiError("后端返回了无效 JSON", response.status, "invalid_json");
  }
}

export async function apiText(path: string, options: ApiRequestInit = {}): Promise<string> {
  const headers = new Headers(options.headers);
  if (!headers.has("accept")) headers.set("accept", "text/plain, text/markdown, */*;q=0.1");
  const response = await requestBytes(path, { ...options, headers }, DEFAULT_JSON_LIMIT_BYTES);
  return new TextDecoder().decode(response.bytes);
}

export async function apiBinary(path: string, options: ApiRequestInit = {}): Promise<Blob> {
  const headers = new Headers(options.headers);
  if (!headers.has("accept")) headers.set("accept", "application/octet-stream, */*;q=0.1");
  const response = await requestBytes(path, { ...options, headers }, DEFAULT_BINARY_LIMIT_BYTES);
  const bytes = new ArrayBuffer(response.bytes.byteLength);
  new Uint8Array(bytes).set(response.bytes);
  return new Blob([bytes], { type: response.contentType || "application/octet-stream" });
}
