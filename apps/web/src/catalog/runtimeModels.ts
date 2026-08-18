import type { ModelDefinition } from "./types";
import type { CanvasModel } from "../lib/generation";

export const RUNTIME_MODEL_MODALITIES = ["text", "image"] as const;

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
