import type { CreationLine } from "../types";
import type { SkillCategory, SkillCoverGradient, SkillDefinition, SkillMediaType } from "./types";

/**
 * Public product catalog.
 *
 * Keep this list aligned with the six top-level orchestrators in /skills.
 * Their child skills are execution stages and are visualised inside the canvas,
 * rather than advertised as unrelated products on the home page.
 */
type ProductSkillSeed = {
  id: CreationLine;
  skill: CreationLine;
  title: string;
  line: CreationLine;
  category: SkillCategory;
  description: string;
  workflow: readonly string[];
  useCases: readonly string[];
  guide: string;
  mediaType: SkillMediaType;
  cover: { kind: "gradient"; key: SkillCoverGradient };
  accent: string;
};

export const SKILL_CATEGORIES: SkillCategory[] = [
  "故事与文本",
  "剧本与分镜",
  "视觉生成",
  "音频与音乐",
  "商业创意",
  "后期与交付",
  "评审与优化",
];

export const SKILL_COVER_GRADIENTS: Readonly<Record<SkillCoverGradient, string>> = {
  "violet-grid": "linear-gradient(135deg, #241d4f 0%, #6d5dfc 52%, #c7bfff 100%)",
  "indigo-stage": "linear-gradient(145deg, #12172f 0%, #3348a8 55%, #8296ff 100%)",
  "cyan-film": "linear-gradient(140deg, #09242c 0%, #087b8c 52%, #63e1df 100%)",
  "emerald-page": "linear-gradient(145deg, #10251d 0%, #24785d 52%, #8dd7b6 100%)",
  "amber-studio": "linear-gradient(140deg, #2d1d0e 0%, #a7651f 52%, #ffd08a 100%)",
  "rose-sound": "linear-gradient(145deg, #321323 0%, #ad376a 52%, #ffa2c7 100%)",
  blueprint: "linear-gradient(145deg, #101b2b 0%, #275a8f 55%, #74b7ec 100%)",
  "midnight-neon": "linear-gradient(135deg, #12131a 0%, #452666 48%, #de5dff 100%)",
};

const PRODUCT_SKILLS: readonly ProductSkillSeed[] = [
  {
    id: "novel",
    skill: "novel",
    title: "写小说",
    line: "novel",
    category: "故事与文本",
    description: "从灵感、素材或源书出发，完成设定、大纲、正文、编辑与审稿的小说生产线。",
    workflow: ["创作简报与素材", "世界观与人物设定", "卷章大纲与正文", "编辑、审稿与交付"],
    useCases: ["从零写小说", "扩写与续写", "专业编辑", "一致性审查"],
    guide: "写下题材、主角和核心冲突；novel 会先建立设定与大纲，再逐步推进正文。",
    mediaType: "text",
    cover: { kind: "gradient", key: "violet-grid" },
    accent: "#8b7cff",
  },
  {
    id: "n2d",
    skill: "n2d",
    title: "制漫剧",
    line: "n2d",
    category: "剧本与分镜",
    description: "把小说或故事制作成漫剧：分集脚本、配音、一致性出图、视频镜头与最终合成。",
    workflow: ["分集脚本与分镜", "角色声音与配音", "一致性画面与镜头", "视频生成与成片合成"],
    useCases: ["小说漫剧", "AI 短剧", "竖屏连载", "剧情视频"],
    guide: "输入小说、故事或短剧构想；n2d 会从剧本与分镜开始，推进配音、出图、视频和合成。",
    mediaType: "mixed",
    cover: { kind: "gradient", key: "indigo-stage" },
    accent: "#6f8cff",
  },
  {
    id: "comic",
    skill: "comic",
    title: "画漫画",
    line: "comic",
    category: "视觉生成",
    description: "完成页漫或条漫的分格脚本、页面排版、漫画出图、嵌字和长图导出。",
    workflow: ["分话与分格脚本", "角色设定与页面排版", "漫画画格生成", "嵌字、质检与导出"],
    useCases: ["页漫", "条漫", "短篇漫画", "小说漫画化"],
    guide: "描述漫画题材、角色和页漫或条漫形式；comic 会从分格脚本与页面排版开始。",
    mediaType: "image",
    cover: { kind: "gradient", key: "emerald-page" },
    accent: "#41c99b",
  },
  {
    id: "ad",
    skill: "ad",
    title: "拍广告",
    line: "ad",
    category: "商业创意",
    description: "从产品卖点与受众出发，完成广告策略、脚本、画面、配音、视频与投放交付。",
    workflow: ["产品与受众策略", "创意概念与广告脚本", "画面、配音与视频", "合成、评分与投放包"],
    useCases: ["TVC", "信息流广告", "产品 Demo", "电商带货"],
    guide: "说明产品、受众、平台和转化目标；ad 会从广告概念与脚本开始制作。",
    mediaType: "mixed",
    cover: { kind: "gradient", key: "amber-studio" },
    accent: "#f3a54a",
  },
  {
    id: "mv",
    skill: "mv",
    title: "制 MV",
    line: "mv",
    category: "音频与音乐",
    description: "围绕一首歌完成节拍分析、视觉蓝图、卡点分镜、画面视频、歌词字幕与合成。",
    workflow: ["歌曲与节拍地图", "视觉蓝图与镜头规划", "画面、视频与歌词时间轴", "卡点合成与交付"],
    useCases: ["叙事 MV", "卡点 MV", "歌词视频", "竖屏副歌版"],
    guide: "描述歌曲、视觉风格和发布平台；mv 会从节拍分析与视觉脚本开始制作。",
    mediaType: "mixed",
    cover: { kind: "gradient", key: "cyan-film" },
    accent: "#38c9d6",
  },
  {
    id: "song",
    skill: "song",
    title: "写歌",
    line: "song",
    category: "音频与音乐",
    description: "从主题、几个字或曲风想法出发，完成歌词、作曲、演唱、挑版、审歌与发布交付。",
    workflow: ["A&R 简报与歌词", "曲式、旋律与和声", "作曲演唱与多版挑选", "混音审查与发布包"],
    useCases: ["原创歌曲", "改词改曲", "多版挑选", "授权换声"],
    guide: "写下主题、情绪、曲风和想表达的故事；song 会从歌词与作曲方向开始。",
    mediaType: "audio",
    cover: { kind: "gradient", key: "rose-sound" },
    accent: "#ef72aa",
  },
];

export const SKILLS: SkillDefinition[] = PRODUCT_SKILLS.map((skill) => ({
  ...skill,
  creator: `LabuTV · ${skill.title}`,
  views: 0,
  favorites: 0,
  steps: [...skill.workflow],
  useCases: [...skill.useCases],
  featured: true,
}));

export const SKILL_CATALOG = SKILLS;
export const FEATURED_SKILLS = SKILLS;

export function getSkillsByLine(line: CreationLine): SkillDefinition[] {
  return SKILLS.filter((skill) => skill.line === line);
}

export function getSkillById(id: string): SkillDefinition | undefined {
  return SKILLS.find((skill) => skill.id === id);
}
