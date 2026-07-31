import type { CreationLine } from "../types";

export type ModelModality = "text" | "image" | "video" | "audio";

export type ModelAvailability = "api" | "preview" | "platform";

export type AudioModelGroup = "voice" | "music";

export interface ModelDefinition {
  id: string;
  name: string;
  provider: string;
  modality: ModelModality;
  description: string;
  availability: ModelAvailability;
  tags: readonly string[];
  modelId?: string;
  /** Provider/model spec accepted by the server-side API-key adapter. */
  providerSpec?: string;
  /** Environment variable names expected by the server. Values are never exposed to Web. */
  apiKeyEnv?: readonly string[];
  audioGroup?: AudioModelGroup;
  recommended?: boolean;
  premium?: boolean;
  points?: number;
}

/** Backwards-compatible name for consumers that render a single model card. */
export type ModelCatalogItem = ModelDefinition;

export type ModelCatalog = Readonly<Record<ModelModality, readonly ModelDefinition[]>>;

export type SkillCategory =
  | "故事与文本"
  | "剧本与分镜"
  | "视觉生成"
  | "音频与音乐"
  | "商业创意"
  | "后期与交付"
  | "评审与优化";

export type SkillCoverGradient =
  | "violet-grid"
  | "indigo-stage"
  | "cyan-film"
  | "emerald-page"
  | "amber-studio"
  | "rose-sound"
  | "blueprint"
  | "midnight-neon";

export type SkillCover =
  | {
      kind: "gradient";
      key: SkillCoverGradient;
    }
  | {
      kind: "asset";
      src: string;
      alt: string;
    };

export type SkillMediaType = "text" | "image" | "video" | "audio" | "mixed";

export type SkillPreviewMedia =
  | { kind: "image"; src: string; alt: string }
  | { kind: "video"; src: string; poster?: string };

export interface SkillDefinition {
  id: string;
  skill: string;
  title: string;
  line: CreationLine;
  category: SkillCategory;
  description: string;
  creator: string;
  views: number;
  favorites: number;
  mediaType: SkillMediaType;
  accent: string;
  steps: string[];
  useCases: string[];
  guide: string;
  cover?: SkillCover;
  preview?: SkillPreviewMedia;
  featured?: boolean;
}

/** Backwards-compatible name for consumers that render a single Skill card. */
export type SkillCatalogItem = SkillDefinition;
