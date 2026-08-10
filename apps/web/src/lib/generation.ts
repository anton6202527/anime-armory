const LOCAL_BRIDGE_URL = "http://127.0.0.1:43117/v1";
const VITE_MODEL_BRIDGE_URL = "/__labutv_local_model/v1";
const LOCAL_BRIDGE_TOKEN_KEY = "anime-armory.local-bridge-token";
const MAX_PROMPT_CHARS = 24_000;
const MAX_TEXT_OUTPUT_CHARS = 200_000;
const MAX_IMAGE_BASE64_CHARS = 28 * 1024 * 1024;
const MAX_INPUT_IMAGE_BASE64_CHARS = 16 * 1024 * 1024;
const MAX_SMALL_RESPONSE_BYTES = 256 * 1024;
const MAX_GENERATION_RESPONSE_BYTES = 32 * 1024 * 1024;
const STATUS_CACHE_MS = 15_000;
const MODEL_ID_PATTERN = /^[a-zA-Z0-9._:/-]{1,160}$/;
const ASPECT_RATIOS = new Set(["1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16"]);

export type CanvasGenerationModality = "text" | "image";

export interface CanvasModel {
  id: string;
  label: string;
  modality: CanvasGenerationModality;
  provider: "cli-proxy-api";
}

export interface CanvasGenerationInput {
  modality: CanvasGenerationModality;
  model: string;
  prompt: string;
  aspectRatio?: string;
  image?: { base64: string; mimeType: string };
  signal?: AbortSignal;
}

export type CanvasGenerationResult =
  | { modality: "text"; model: string; text: string }
  | {
      modality: "image";
      model: string;
      image: { base64: string; mimeType: string; revisedPrompt?: string };
    };

export type CanvasGenerationErrorCode =
  | "bridge_unavailable"
  | "bridge_unsupported"
  | "pairing_denied"
  | "proxy_unavailable"
  | "invalid_request"
  | "model_unavailable"
  | "generation_failed";

export class CanvasGenerationError extends Error {
  readonly name = "CanvasGenerationError";

  constructor(
    readonly code: CanvasGenerationErrorCode,
    message: string,
    readonly status?: number,
    readonly serverCode?: string,
  ) {
    super(message);
  }
}

interface LocalBridgeStatus {
  service: string;
  version: number;
  capabilities?: { canvasGeneration?: boolean };
}

type GenerationBridge = "desktop" | "vite";

interface ErrorEnvelope {
  error?: { code?: string; message?: string };
}

let supportedUntil = 0;
let supportedBridge: GenerationBridge | null = null;
let pairingPromise: Promise<string> | null = null;
let memoryToken: string | null = null;

function storedToken(): string | null {
  try {
    return window.sessionStorage.getItem(LOCAL_BRIDGE_TOKEN_KEY) ?? memoryToken;
  } catch {
    return memoryToken;
  }
}

function storeToken(token: string | null): void {
  memoryToken = token;
  try {
    if (token) window.sessionStorage.setItem(LOCAL_BRIDGE_TOKEN_KEY, token);
    else window.sessionStorage.removeItem(LOCAL_BRIDGE_TOKEN_KEY);
  } catch {
    // A private browser context may disable storage; the current request can still use the token in memory.
  }
}

async function limitedJson(response: Response, maxBytes: number): Promise<unknown> {
  const declaredLength = Number(response.headers.get("content-length") ?? Number.NaN);
  if (Number.isFinite(declaredLength) && declaredLength > maxBytes) {
    await response.body?.cancel().catch(() => undefined);
    throw new CanvasGenerationError("generation_failed", "本地桥接返回内容超过安全上限", 502);
  }
  if (!response.body) return null;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let bytes = 0;
  let text = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > maxBytes) {
        await reader.cancel().catch(() => undefined);
        throw new CanvasGenerationError("generation_failed", "本地桥接返回内容超过安全上限", 502);
      }
      text += decoder.decode(value, { stream: true });
    }
    text += decoder.decode();
  } finally {
    reader.releaseLock();
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    throw new CanvasGenerationError("generation_failed", "本地桥接返回了无效 JSON", 502);
  }
}

function envelope(value: unknown): ErrorEnvelope {
  return value && typeof value === "object" && !Array.isArray(value) ? value as ErrorEnvelope : {};
}

function serverError(response: Response, value: unknown, fallback: CanvasGenerationErrorCode): CanvasGenerationError {
  const payload = envelope(value);
  const serverCode = typeof payload.error?.code === "string" ? payload.error.code : undefined;
  const message = typeof payload.error?.message === "string"
    ? payload.error.message
    : `本地桥接请求失败（${response.status}）`;
  let code = fallback;
  if (response.status === 404) code = "bridge_unsupported";
  else if (serverCode === "canvas_generation_invalid_request") code = "invalid_request";
  else if (serverCode === "canvas_model_unavailable") code = "model_unavailable";
  else if ([
    "cli_proxy_not_configured",
    "cli_proxy_invalid_config",
    "cli_proxy_auth_failed",
    "cli_proxy_unavailable",
    "cli_proxy_endpoint_unsupported",
  ].includes(serverCode ?? "")) code = "proxy_unavailable";
  else if (serverCode?.startsWith("cli_proxy_")) code = "generation_failed";
  return new CanvasGenerationError(code, message, response.status, serverCode);
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
  unavailableMessage = "未检测到 LabuTV 桌面端本地桥接",
): Promise<Response> {
  const controller = new AbortController();
  const callerSignal = init.signal;
  let timedOut = false;
  const abortFromCaller = () => controller.abort(callerSignal?.reason);
  if (callerSignal?.aborted) abortFromCaller();
  else callerSignal?.addEventListener("abort", abortFromCaller, { once: true });
  const timer = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      if (callerSignal?.aborted) {
        throw new CanvasGenerationError("generation_failed", "生成已取消");
      }
      if (timedOut) {
        throw new CanvasGenerationError("bridge_unavailable", "连接本地桥接超时");
      }
    }
    throw new CanvasGenerationError("bridge_unavailable", unavailableMessage);
  } finally {
    window.clearTimeout(timer);
    callerSignal?.removeEventListener("abort", abortFromCaller);
  }
}

async function bridgeStatus(bridge: GenerationBridge): Promise<void> {
  const desktop = bridge === "desktop";
  const response = await fetchWithTimeout(
    `${desktop ? LOCAL_BRIDGE_URL : VITE_MODEL_BRIDGE_URL}/status`,
    { method: "GET", credentials: desktop ? "omit" : "same-origin" },
    desktop ? 1_500 : 5_000,
    desktop ? "未检测到 LabuTV 桌面端本地桥接" : "未检测到本地 Web 模型服务",
  );
  const value = await limitedJson(response, MAX_SMALL_RESPONSE_BYTES);
  if (!response.ok) throw serverError(response, value, "bridge_unavailable");
  const status = value && typeof value === "object" && !Array.isArray(value)
    ? value as LocalBridgeStatus
    : null;
  const expectedService = desktop ? "anime-armory-local-bridge" : "anime-armory-vite-model-bridge";
  const expectedVersion = desktop ? 2 : 1;
  if (status?.service !== expectedService) {
    throw new CanvasGenerationError(
      "bridge_unavailable",
      desktop ? "本地端口不是 LabuTV 桌面桥接" : "当前站点未启用本地 Web 模型服务",
    );
  }
  if (status.version < expectedVersion || status.capabilities?.canvasGeneration !== true) {
    throw new CanvasGenerationError(
      "bridge_unsupported",
      desktop ? "当前 LabuTV 桌面端版本尚不支持画布模型生成" : "本地 Web 模型服务版本不兼容",
    );
  }
}

async function assertGenerationBridge(): Promise<GenerationBridge> {
  if (supportedBridge && supportedUntil > Date.now()) return supportedBridge;
  supportedBridge = null;
  supportedUntil = 0;
  let desktopError: CanvasGenerationError | null = null;
  try {
    await bridgeStatus("desktop");
    supportedBridge = "desktop";
  } catch (error) {
    if (!(error instanceof CanvasGenerationError)
      || (error.code !== "bridge_unavailable" && error.code !== "bridge_unsupported")) throw error;
    desktopError = error;
  }
  if (!supportedBridge && import.meta.env.DEV) {
    try {
      await bridgeStatus("vite");
      supportedBridge = "vite";
    } catch (error) {
      if (!(error instanceof CanvasGenerationError)) throw error;
      throw new CanvasGenerationError(
        error.code,
        `${desktopError?.message ?? "桌面桥接不可用"}；${error.message}`,
        error.status,
        error.serverCode,
      );
    }
  }
  if (!supportedBridge) {
    throw desktopError ?? new CanvasGenerationError("bridge_unavailable", "未检测到本地模型服务");
  }
  supportedUntil = Date.now() + STATUS_CACHE_MS;
  return supportedBridge;
}

async function pairToken(force = false): Promise<string> {
  if (!force) {
    const token = storedToken();
    if (token) return token;
  }
  if (pairingPromise) return pairingPromise;
  pairingPromise = (async () => {
    const response = await fetchWithTimeout(`${LOCAL_BRIDGE_URL}/pair`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    }, 120_000);
    const value = await limitedJson(response, MAX_SMALL_RESPONSE_BYTES);
    if (!response.ok) {
      const error = serverError(response, value, response.status === 403 ? "pairing_denied" : "bridge_unavailable");
      if (response.status === 403) {
        throw new CanvasGenerationError("pairing_denied", error.message, error.status, error.serverCode);
      }
      throw error;
    }
    const token = value && typeof value === "object" && !Array.isArray(value)
      && typeof (value as Record<string, unknown>).token === "string"
      ? (value as Record<string, unknown>).token as string
      : "";
    if (!token || token.length > 4096) {
      throw new CanvasGenerationError("bridge_unavailable", "本地桥接没有返回有效的配对令牌");
    }
    storeToken(token);
    return token;
  })();
  try {
    return await pairingPromise;
  } finally {
    pairingPromise = null;
  }
}

async function authorizedRequest(
  bridge: GenerationBridge,
  pathname: string,
  init: RequestInit,
  timeoutMs: number,
  maxBytes: number,
  retry = true,
): Promise<unknown> {
  const headers = new Headers(init.headers);
  if (bridge === "desktop") headers.set("authorization", `Bearer ${await pairToken()}`);
  const response = await fetchWithTimeout(
    `${bridge === "desktop" ? LOCAL_BRIDGE_URL : VITE_MODEL_BRIDGE_URL}${pathname}`,
    { ...init, headers, credentials: bridge === "desktop" ? "omit" : "same-origin" },
    timeoutMs,
    bridge === "desktop" ? "未检测到 LabuTV 桌面端本地桥接" : "未检测到本地 Web 模型服务",
  );
  if (bridge === "desktop" && response.status === 401 && retry) {
    storeToken(null);
    await pairToken(true);
    return authorizedRequest(bridge, pathname, init, timeoutMs, maxBytes, false);
  }
  const value = await limitedJson(response, response.ok ? maxBytes : MAX_SMALL_RESPONSE_BYTES);
  if (!response.ok) throw serverError(response, value, "generation_failed");
  return value;
}

function validModel(value: unknown): value is CanvasModel {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const model = value as Partial<CanvasModel>;
  return MODEL_ID_PATTERN.test(model.id ?? "")
    && typeof model.label === "string"
    && (model.modality === "text" || model.modality === "image")
    && model.provider === "cli-proxy-api";
}

export function isCanvasGenerationError(error: unknown): error is CanvasGenerationError {
  return error instanceof CanvasGenerationError;
}

export async function discoverCanvasModels(signal?: AbortSignal): Promise<CanvasModel[]> {
  const bridge = await assertGenerationBridge();
  const value = await authorizedRequest(bridge, "/canvas/models", { method: "GET", signal }, 10_000, MAX_SMALL_RESPONSE_BYTES);
  const models = value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>).models
    : null;
  if (!Array.isArray(models)) {
    throw new CanvasGenerationError("generation_failed", "本地桥接返回的模型列表格式无效");
  }
  return models.filter(validModel);
}

export async function generateCanvasContent(input: CanvasGenerationInput): Promise<CanvasGenerationResult> {
  if ((input.modality !== "text" && input.modality !== "image")
    || !MODEL_ID_PATTERN.test(input.model)
    || !input.prompt.trim()
    || input.prompt.trim().length > MAX_PROMPT_CHARS
    || (input.image && (input.modality !== "text"
      || input.image.base64.length > MAX_INPUT_IMAGE_BASE64_CHARS
      || !/^[a-zA-Z0-9+/]+={0,2}$/.test(input.image.base64)
      || !/^image\/(?:png|jpeg|webp|gif)$/.test(input.image.mimeType)))
    || (input.aspectRatio && (input.modality !== "image" || !ASPECT_RATIOS.has(input.aspectRatio)))) {
    throw new CanvasGenerationError("invalid_request", "生成参数无效");
  }
  const bridge = await assertGenerationBridge();
  const value = await authorizedRequest(bridge, "/canvas/generate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    signal: input.signal,
    body: JSON.stringify({
      modality: input.modality,
      model: input.model,
      prompt: input.prompt.trim(),
      ...(input.image ? { image: input.image } : {}),
      ...(input.aspectRatio ? { aspectRatio: input.aspectRatio } : {}),
    }),
  }, input.modality === "image" ? 190_000 : 100_000, MAX_GENERATION_RESPONSE_BYTES);
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new CanvasGenerationError("generation_failed", "本地桥接返回的生成结果格式无效");
  }
  const result = value as Record<string, unknown>;
  if (input.modality === "text" && result.modality === "text" && typeof result.text === "string"
    && result.text && result.text.length <= MAX_TEXT_OUTPUT_CHARS) {
    return { modality: "text", model: input.model, text: result.text };
  }
  if (input.modality === "image" && result.modality === "image" && result.image
    && typeof result.image === "object" && !Array.isArray(result.image)) {
    const image = result.image as Record<string, unknown>;
    if (typeof image.base64 === "string" && image.base64 && image.base64.length <= MAX_IMAGE_BASE64_CHARS
      && typeof image.mimeType === "string" && /^image\/(?:png|jpeg|webp|gif)$/.test(image.mimeType)) {
      return {
        modality: "image",
        model: input.model,
        image: {
          base64: image.base64,
          mimeType: image.mimeType,
          ...(typeof image.revisedPrompt === "string" && image.revisedPrompt
            ? { revisedPrompt: image.revisedPrompt }
            : {}),
        },
      };
    }
  }
  throw new CanvasGenerationError("generation_failed", "本地桥接返回的生成结果格式无效");
}
