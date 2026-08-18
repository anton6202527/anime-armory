import type { AiGenerationRequest } from "@anime-armory/contracts";
import { apiJson, isApiError } from "./api";

const MAX_PROMPT_CHARS = 24_000;
const MAX_TEXT_OUTPUT_CHARS = 200_000;
const MAX_IMAGE_BASE64_CHARS = 28 * 1024 * 1024;
const MAX_INPUT_IMAGE_BASE64_CHARS = 16 * 1024 * 1024;
const MAX_SMALL_RESPONSE_BYTES = 256 * 1024;
const MAX_GENERATION_RESPONSE_BYTES = 32 * 1024 * 1024;
const MODEL_ID_PATTERN = /^[a-zA-Z0-9._:/-]{1,160}$/;
const ASPECT_RATIOS = new Set(["1:1", "2:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16"]);
const IMAGE_MIME_TYPE_PATTERN = /^image\/(?:png|jpeg|webp|gif)$/;
const BASE64_PATTERN = /^[a-zA-Z0-9+/]+={0,2}$/;

export type CanvasGenerationModality = "text" | "image";

export interface CanvasModel {
  id: string;
  label: string;
  modality: CanvasGenerationModality;
  /** Kept for existing canvas consumers; the REST contract calls this provider `cliproxy`. */
  provider: "cli-proxy-api";
}

export interface CanvasGenerationInput {
  modality: CanvasGenerationModality;
  model: string;
  prompt: string;
  aspectRatio?: string;
  quality?: "standard" | "high";
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

function record(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function unwrapData(value: unknown, property?: string): unknown {
  const outer = record(value);
  if (!outer) return value;
  if (property && outer[property] !== undefined) return outer[property];
  const data = record(outer.data);
  if (property && data?.[property] !== undefined) return data[property];
  return outer.data ?? value;
}

function isGptTextModelId(modelId: string): boolean {
  return /(?:^|[/:._-])gpt(?:$|[/:._-])/i.test(modelId);
}

function generationError(error: unknown): CanvasGenerationError {
  if (error instanceof CanvasGenerationError) return error;
  if (!isApiError(error)) {
    return new CanvasGenerationError("generation_failed", error instanceof Error ? error.message : "生成请求失败");
  }

  const serverCode = error.code;
  const normalizedCode = serverCode.toLocaleLowerCase();
  let code: CanvasGenerationErrorCode = "generation_failed";
  if (serverCode === "request_cancelled") code = "generation_failed";
  else if (serverCode === "network_error" || serverCode === "request_timeout") code = "bridge_unavailable";
  else if (error.status === 404 && normalizedCode.startsWith("http_")) code = "bridge_unsupported";
  else if (error.status === 400 || normalizedCode.includes("invalid_request") || normalizedCode.includes("validation")) {
    code = "invalid_request";
  } else if (normalizedCode.includes("model") && (
    normalizedCode.includes("unavailable")
    || normalizedCode.includes("unsupported")
    || normalizedCode.includes("not_found")
  )) {
    code = "model_unavailable";
  } else if ([
    "cliproxy_not_configured",
    "cliproxy_invalid_config",
    "cliproxy_auth_failed",
    "cliproxy_unavailable",
    "cliproxy_endpoint_unsupported",
    "cli_proxy_not_configured",
    "cli_proxy_invalid_config",
    "cli_proxy_auth_failed",
    "cli_proxy_unavailable",
    "cli_proxy_endpoint_unsupported",
    "provider_unavailable",
    "provider_auth_failed",
  ].includes(normalizedCode)) {
    code = "proxy_unavailable";
  }
  const message = serverCode === "request_cancelled" ? "生成已取消" : error.message;
  return new CanvasGenerationError(code, message, error.status || undefined, serverCode);
}

function validBackendModel(value: unknown): value is Record<string, unknown> & {
  id: string;
  label: string;
  modality: CanvasGenerationModality;
} {
  const model = record(value);
  return Boolean(
    model
    && typeof model.id === "string"
    && MODEL_ID_PATTERN.test(model.id)
    && typeof model.label === "string"
    && model.label.trim()
    && (model.modality === "text" || model.modality === "image")
    && (model.modality === "image" || isGptTextModelId(model.id))
    && (model.provider === "cliproxy" || model.provider === "cli-proxy-api"),
  );
}

export function isCanvasGenerationError(error: unknown): error is CanvasGenerationError {
  return error instanceof CanvasGenerationError;
}

export async function discoverCanvasModels(signal?: AbortSignal): Promise<CanvasModel[]> {
  try {
    const value = await apiJson<unknown>("/v1/ai/models", {
      method: "GET",
      signal,
      timeoutMs: 10_000,
      maxResponseBytes: MAX_SMALL_RESPONSE_BYTES,
    });
    const models = unwrapData(value, "models");
    if (!Array.isArray(models)) {
      throw new CanvasGenerationError("generation_failed", "后端返回的模型列表格式无效");
    }
    return models.filter(validBackendModel).map((model) => ({
      id: model.id,
      label: model.label.trim(),
      modality: model.modality,
      provider: "cli-proxy-api",
    }));
  } catch (error) {
    throw generationError(error);
  }
}

export async function generateCanvasContent(input: CanvasGenerationInput): Promise<CanvasGenerationResult> {
  const prompt = input.prompt.trim();
  if ((input.modality !== "text" && input.modality !== "image")
    || !MODEL_ID_PATTERN.test(input.model)
    || !prompt
    || prompt.length > MAX_PROMPT_CHARS
    || (input.image && (input.image.base64.length > MAX_INPUT_IMAGE_BASE64_CHARS
      || !BASE64_PATTERN.test(input.image.base64)
      || !IMAGE_MIME_TYPE_PATTERN.test(input.image.mimeType)
      || (input.modality === "image" && input.image.mimeType === "image/gif")))
    || (input.aspectRatio && (input.modality !== "image" || !ASPECT_RATIOS.has(input.aspectRatio)))
    || (input.quality && (input.modality !== "image" || (input.quality !== "standard" && input.quality !== "high")))) {
    throw new CanvasGenerationError("invalid_request", "生成参数无效");
  }

  try {
    const request = {
      modality: input.modality,
      model: input.model,
      prompt,
      ...(input.image ? {
        image: {
          base64: input.image.base64,
          mimeType: input.image.mimeType as NonNullable<AiGenerationRequest["image"]>["mimeType"],
        },
      } : {}),
      ...(input.aspectRatio ? {
        aspectRatio: input.aspectRatio as NonNullable<AiGenerationRequest["aspectRatio"]>,
      } : {}),
      ...(input.quality ? { quality: input.quality } : {}),
    } satisfies AiGenerationRequest;
    const value = await apiJson<unknown>("/v1/ai/generations", {
      method: "POST",
      headers: { "content-type": "application/json" },
      signal: input.signal,
      timeoutMs: input.modality === "image" ? 190_000 : 100_000,
      maxResponseBytes: MAX_GENERATION_RESPONSE_BYTES,
      body: JSON.stringify(request),
    });
    const result = record(unwrapData(value, "generation"));
    const resultModel = typeof result?.model === "string" && MODEL_ID_PATTERN.test(result.model)
      ? result.model
      : input.model;
    if (input.modality === "text" && result?.modality === "text" && typeof result.text === "string"
      && result.text && result.text.length <= MAX_TEXT_OUTPUT_CHARS) {
      return { modality: "text", model: resultModel, text: result.text };
    }
    const image = record(result?.image);
    if (input.modality === "image" && result?.modality === "image" && image
      && typeof image.base64 === "string" && image.base64 && image.base64.length <= MAX_IMAGE_BASE64_CHARS
      && typeof image.mimeType === "string" && IMAGE_MIME_TYPE_PATTERN.test(image.mimeType)) {
      return {
        modality: "image",
        model: resultModel,
        image: {
          base64: image.base64,
          mimeType: image.mimeType,
          ...(typeof image.revisedPrompt === "string" && image.revisedPrompt
            ? { revisedPrompt: image.revisedPrompt }
            : {}),
        },
      };
    }
    throw new CanvasGenerationError("generation_failed", "后端返回的生成结果格式无效");
  } catch (error) {
    throw generationError(error);
  }
}
