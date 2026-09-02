import type { ModelDefinition } from "./types";
import type { CanvasModel } from "../lib/generation";

export const RUNTIME_MODEL_MODALITIES = ["text", "image"] as const;

export interface LocalCodexModelDescriptor {
  id: string;
  name: string;
  description: string;
}

export function localCodexModelDefinitions(models: readonly LocalCodexModelDescriptor[]): ModelDefinition[] {
  return models.map((model) => ({
    id: model.id,
    modelId: model.id,
    name: model.name || model.id,
    provider: "OpenAI Codex（本机）",
    modality: "text",
    description: model.description || "当前 ChatGPT 账号可通过本机 Codex CLI 调用。",
    availability: "platform",
    tags: ["本机 Codex", "ChatGPT 订阅", "运行时发现"],
    recommended: true,
  } satisfies ModelDefinition));
}

export function runtimeModelDefinitions(models: readonly CanvasModel[]): ModelDefinition[] {
  const seen = new Set<string>();
  return models.flatMap((model) => {
    const key = `${model.modality}:${model.id}`;
    if (seen.has(key)) return [];
    seen.add(key);
    return [{
      id: model.id,
      modelId: model.id,
      name: model.label || model.id,
      provider: "cliproxy",
      modality: model.modality,
      description: model.modality === "image"
        ? "后端 discovery 已确认可调用；用于画布直接生图。"
        : "后端 discovery 已确认可调用；用于 GPT 文本与 Skill 编排。",
      availability: "api",
      tags: ["后端已连接", "可调用"],
      recommended: true,
    } satisfies ModelDefinition];
  });
}
