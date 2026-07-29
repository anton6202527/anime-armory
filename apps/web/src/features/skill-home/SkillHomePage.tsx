import {
  ArrowUp,
  Bell,
  Bot,
  Box,
  CircleHelp,
  Clock3,
  Cloud,
  FileCode2,
  Layers3,
  LoaderCircle,
  LogIn,
  LogOut,
  Moon,
  Paperclip,
  Play,
  Plus,
  Search,
  Share2,
  Star,
  Sun,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { BrandIcon } from "../../components/BrandIcon";
import { LineIcon } from "../../components/LineIcon";
import { MODEL_GROUPS } from "../../catalog/models";
import { loadSkillSourceFiles, type SkillSourceFile } from "../../catalog/skillSources";
import { SKILLS } from "../../catalog/skills";
import type { ModelDefinition, ModelModality, SkillCategory, SkillDefinition } from "../../catalog/types";
import { getMySettings, signInOrSignUpWithEmail, signOut, subscribeAuth, updateMySettings, type AuthUser } from "../../lib/auth";
import type { ThemeMode } from "../../lib/theme";
import { createUserSkill, deleteUserSkill, listUserSkills, type UserSkillRecord } from "../../lib/userSkills";
import { createWebWork, saveWork } from "../../lib/work";
import type { CreationLine, PendingAttachment, WebWork } from "../../types";
import { AuthDialog } from "../account/AuthDialog";
import { CreateSkillDialog, type CreateSkillFormValues } from "./CreateSkillDialog";

const MODALITY_LABELS: Record<ModelModality, string> = {
  text: "文字",
  image: "图片",
  video: "视频",
  audio: "音频",
};

const MARKET_CATEGORIES = ["推荐", "写小说", "制漫剧", "画漫画", "拍广告", "制 MV", "写歌"] as const;
const MEDIA_LABELS: Record<SkillDefinition["mediaType"], string> = { text: "文字", image: "图片", video: "视频", audio: "音频", mixed: "全模态" };
const SKILL_CATEGORIES = new Set<SkillCategory>(["故事与文本", "剧本与分镜", "视觉生成", "音频与音乐", "商业创意", "后期与交付", "评审与优化"]);
const LINE_ACCENTS: Record<CreationLine, string> = { novel: "#8b7cff", n2d: "#6f8cff", comic: "#41c99b", ad: "#f3a54a", mv: "#38c9d6", song: "#ef72aa" };

function matchesMarketCategory(skill: SkillDefinition, marketCategory: string) {
  if (marketCategory === "推荐") return !skill.id.startsWith("user:");
  const lineByCategory: Record<string, CreationLine> = {
    写小说: "novel",
    制漫剧: "n2d",
    画漫画: "comic",
    拍广告: "ad",
    "制 MV": "mv",
    写歌: "song",
  };
  return skill.line === lineByCategory[marketCategory];
}

type OpenMenu = "model" | "skill" | "mode" | null;
type SkillTab = "all" | "common" | "favorite" | "mine";

function toAttachment(file: File): PendingAttachment {
  return {
    id: crypto.randomUUID(),
    name: file.name,
    size: file.size,
    type: file.type || "application/octet-stream",
    file,
  };
}

function compactNumber(value: number) {
  if (value >= 10_000) return `${(value / 10_000).toFixed(value >= 100_000 ? 0 : 1)}w`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(value);
}

function modelMark(model: ModelDefinition) {
  return model.provider.slice(0, 1).toUpperCase();
}

function getSkillPreview(skill: SkillDefinition): SkillDefinition["preview"] {
  if (skill.preview) return skill.preview;
  if (skill.cover?.kind === "asset") {
    return { kind: "image", src: skill.cover.src, alt: skill.cover.alt };
  }
  return undefined;
}

function readFavorites() {
  try {
    return new Set<string>(JSON.parse(localStorage.getItem("anime-armory.web.favorite-skills") ?? "[]") as string[]);
  } catch {
    return new Set<string>();
  }
}

function userSkillToDefinition(skill: UserSkillRecord, ownerEmail: string): SkillDefinition {
  return {
    id: `user:${skill.id}`,
    skill: skill.slug,
    title: skill.title,
    line: skill.line,
    category: SKILL_CATEGORIES.has(skill.category as SkillCategory) ? skill.category as SkillCategory : "故事与文本",
    description: skill.description,
    creator: ownerEmail || "我的 Skill",
    views: 0,
    favorites: 0,
    mediaType: skill.mediaType,
    accent: LINE_ACCENTS[skill.line],
    steps: skill.steps,
    useCases: skill.useCases,
    guide: skill.guide,
  };
}

function authIsConfigured() {
  return Boolean(import.meta.env.VITE_SUPABASE_URL?.trim() && import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim());
}

export function SkillHomePage({
  onCreate,
  theme,
  onThemeChange,
}: {
  onCreate: (work: WebWork, attachments: PendingAttachment[]) => void;
  theme: ThemeMode;
  onThemeChange: (theme: ThemeMode) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const promptRef = useRef<HTMLTextAreaElement>(null);
  const [prompt, setPrompt] = useState("");
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [openMenu, setOpenMenu] = useState<OpenMenu>(null);
  const [modality, setModality] = useState<ModelModality>("image");
  const [selectedModels, setSelectedModels] = useState<Record<ModelModality, string>>(() => ({
    text: MODEL_GROUPS.text[0]?.id ?? "",
    image: MODEL_GROUPS.image[0]?.id ?? "",
    video: MODEL_GROUPS.video[0]?.id ?? "",
    audio: MODEL_GROUPS.audio[0]?.id ?? "",
  }));
  const [selectedSkillId, setSelectedSkillId] = useState(SKILLS[0]?.id ?? "");
  const [generationMode, setGenerationMode] = useState<"manual" | "auto">("auto");
  const [skillTab, setSkillTab] = useState<SkillTab>("all");
  const [skillPickerQuery, setSkillPickerQuery] = useState("");
  const [pageTab, setPageTab] = useState<"skills" | "favorite" | "mine">("skills");
  const [category, setCategory] = useState("推荐");
  const [query, setQuery] = useState("");
  const [favorites, setFavorites] = useState<Set<string>>(readFavorites);
  const [detailSkill, setDetailSkill] = useState<SkillDefinition | null>(null);
  const [failedPreviewSkillId, setFailedPreviewSkillId] = useState<string | null>(null);
  const [detailSkillSources, setDetailSkillSources] = useState<SkillSourceFile[]>([]);
  const [activeSourceFileId, setActiveSourceFileId] = useState("");
  const [promoVisible, setPromoVisible] = useState(true);
  const [toast, setToast] = useState("");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [openMineAfterAuth, setOpenMineAfterAuth] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [createSkillOpen, setCreateSkillOpen] = useState(false);
  const [userSkillRecords, setUserSkillRecords] = useState<UserSkillRecord[]>([]);
  const [userSkillsLoading, setUserSkillsLoading] = useState(false);

  const customSkills = useMemo(
    () => userSkillRecords.map((skill) => userSkillToDefinition(skill, authUser?.email ?? "我的 Skill")),
    [authUser?.email, userSkillRecords],
  );
  const allSkills = useMemo(() => [...SKILLS, ...customSkills], [customSkills]);
  const customSkillIds = useMemo(() => new Set(customSkills.map((skill) => skill.id)), [customSkills]);

  const selectedSkill = useMemo(
    () => allSkills.find((skill) => skill.id === selectedSkillId),
    [allSkills, selectedSkillId],
  );
  const selectedModel = useMemo(
    () => MODEL_GROUPS[modality].find((model) => model.id === selectedModels[modality]),
    [modality, selectedModels],
  );
  const detailPreview = useMemo(() => detailSkill ? getSkillPreview(detailSkill) : undefined, [detailSkill]);
  const activeSourceFile = useMemo(
    () => detailSkillSources.find((file) => file.id === activeSourceFileId) ?? detailSkillSources[0],
    [activeSourceFileId, detailSkillSources],
  );
  const ready = Boolean(prompt.trim() || attachments.length) && Boolean(selectedSkill && selectedModel);

  const visibleSkills = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return allSkills.filter((skill) => {
      if (pageTab === "favorite" && !favorites.has(skill.id)) return false;
      if (pageTab === "mine" && !customSkillIds.has(skill.id)) return false;
      if (pageTab === "skills" && !matchesMarketCategory(skill, category)) return false;
      if (!normalizedQuery) return true;
      return `${skill.title} ${skill.description} ${skill.creator}`.toLocaleLowerCase().includes(normalizedQuery);
    });
  }, [allSkills, category, customSkillIds, favorites, pageTab, query]);

  const pickerSkills = useMemo(() => {
    const normalizedQuery = skillPickerQuery.trim().toLocaleLowerCase();
    return allSkills.filter((skill) => {
      if (skillTab === "common" && !skill.featured) return false;
      if (skillTab === "favorite" && !favorites.has(skill.id)) return false;
      if (skillTab === "mine" && !customSkillIds.has(skill.id)) return false;
      return !normalizedQuery || `${skill.title} ${skill.description}`.toLocaleLowerCase().includes(normalizedQuery);
    });
  }, [allSkills, customSkillIds, favorites, skillPickerQuery, skillTab]);

  useEffect(() => subscribeAuth((user) => { setAuthUser(user); setAuthReady(true); }), []);

  useEffect(() => {
    if (!authUser || !openMineAfterAuth) return;
    setPageTab("mine");
    setCategory("推荐");
    setOpenMineAfterAuth(false);
    window.requestAnimationFrame(() => document.querySelector(".skill-market")?.scrollIntoView({ behavior: "smooth" }));
  }, [authUser, openMineAfterAuth]);

  useEffect(() => {
    let cancelled = false;
    if (!authUser) {
      setUserSkillRecords([]);
      return undefined;
    }
    setUserSkillsLoading(true);
    void Promise.all([listUserSkills(), getMySettings()])
      .then(([skills, settings]) => {
        if (cancelled) return;
        setUserSkillRecords(skills);
        if (settings?.theme === "dark" || settings?.theme === "light") onThemeChange(settings.theme);
        const syncedFavorites = settings?.preferences.favoriteSkillIds;
        if (Array.isArray(syncedFavorites) && syncedFavorites.every((value) => typeof value === "string")) setFavorites(new Set(syncedFavorites));
      })
      .catch(() => { if (!cancelled) setToast("个人云数据暂不可用，已保留本机设置"); })
      .finally(() => { if (!cancelled) setUserSkillsLoading(false); });
    return () => { cancelled = true; };
  }, [authUser, onThemeChange]);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (detailSkill) setDetailSkill(null);
      else if (accountOpen) setAccountOpen(false);
      else setOpenMenu(null);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [accountOpen, detailSkill]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(""), 2200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => setFailedPreviewSkillId(null), [detailSkill?.id]);

  useEffect(() => {
    let cancelled = false;
    if (!detailSkill) {
      setDetailSkillSources([]);
      setActiveSourceFileId("");
      return undefined;
    }
    setDetailSkillSources([]);
    setActiveSourceFileId("");
    void loadSkillSourceFiles(detailSkill)
      .then((files) => {
        if (cancelled) return;
        setDetailSkillSources(files);
        setActiveSourceFileId(files[0]?.id ?? "");
      })
      .catch(() => {
        if (cancelled) return;
        const failedFile = {
          id: "skill-source-error",
          name: "读取失败",
          path: "SKILL.md",
          source: "# Skill 源码读取失败\n\n请关闭详情后重试。",
        };
        setDetailSkillSources([failedFile]);
        setActiveSourceFileId(failedFile.id);
      });
    return () => { cancelled = true; };
  }, [detailSkill]);

  function toggleFavorite(skillId: string) {
    setFavorites((current) => {
      const next = new Set(current);
      if (next.has(skillId)) next.delete(skillId);
      else next.add(skillId);
      localStorage.setItem("anime-armory.web.favorite-skills", JSON.stringify([...next]));
      if (authUser) void updateMySettings({ preferences: { favoriteSkillIds: [...next] } }).catch(() => undefined);
      return next;
    });
  }

  function useSkill(skill: SkillDefinition) {
    setSelectedSkillId(skill.id);
    setDetailSkill(null);
    setOpenMenu(null);
    setToast(`已添加「${skill.title}」`);
    window.setTimeout(() => promptRef.current?.focus(), 0);
  }

  function removeSelectedSkill() {
    setSelectedSkillId("");
    setOpenMenu(null);
    window.setTimeout(() => promptRef.current?.focus(), 0);
  }

  function removeSelectedModel() {
    setSelectedModels((current) => ({ ...current, [modality]: "" }));
    setOpenMenu(null);
    window.setTimeout(() => promptRef.current?.focus(), 0);
  }

  function submit() {
    if (!ready || !selectedSkill || !selectedModel) return;
    const customRecord = userSkillRecords.find((skill) => `user:${skill.id}` === selectedSkill.id);
    const work = createWebWork(selectedSkill.line, prompt, attachments, {
      skillId: selectedSkill.id,
      ...(customRecord ? { skillDefinition: { title: selectedSkill.title, description: selectedSkill.description, guide: selectedSkill.guide, steps: selectedSkill.steps, useCases: selectedSkill.useCases } } : {}),
      generationMode,
      model: { modality, modelId: selectedModel.id },
    });
    saveWork(work);
    onCreate(work, attachments);
  }

  function openAuth() {
    setOpenMenu(null);
    setAccountOpen(false);
    setAuthOpen(true);
  }

  function openMine() {
    if (!authUser) {
      setOpenMineAfterAuth(true);
      openAuth();
      return;
    }
    setPageTab("mine");
    setCategory("推荐");
  }

  function selectSkillPickerTab(nextTab: SkillTab) {
    if (nextTab === "mine" && !authUser) {
      setOpenMineAfterAuth(true);
      openAuth();
      return;
    }
    setSkillTab(nextTab);
  }

  function openCreateSkill() {
    setOpenMenu(null);
    if (!authUser) {
      setToast("登录后即可创建并云端保存 Skill");
      setOpenMineAfterAuth(true);
      openAuth();
      return;
    }
    setCreateSkillOpen(true);
  }

  async function handleCreateSkill(values: CreateSkillFormValues) {
    const created = await createUserSkill({ ...values, definition: { source: "web-skill-builder", version: 1 } });
    setUserSkillRecords((items) => [created, ...items]);
    setPageTab("mine");
    setCategory("推荐");
    setSelectedSkillId(`user:${created.id}`);
    setToast(`已创建「${created.title}」`);
  }

  async function removeUserSkill(skill: SkillDefinition) {
    const record = userSkillRecords.find((item) => `user:${item.id}` === skill.id);
    if (!record || !window.confirm(`确定删除「${skill.title}」吗？此操作不可撤销。`)) return;
    await deleteUserSkill(record.id);
    setUserSkillRecords((items) => items.filter((item) => item.id !== record.id));
    setFavorites((items) => { const next = new Set(items); next.delete(skill.id); return next; });
    if (selectedSkillId === skill.id) setSelectedSkillId("");
    setDetailSkill(null);
    setToast("Skill 已删除");
  }

  function changeTheme(nextTheme: ThemeMode) {
    onThemeChange(nextTheme);
    if (authUser) void updateMySettings({ theme: nextTheme }).catch(() => setToast("主题已保存在本机，云端同步失败"));
  }

  return (
    <main className="skill-home" onClick={() => { setOpenMenu(null); setAccountOpen(false); }}>
      {promoVisible && (
        <div className="promo-bar">
          <span className="promo-badge"><Clock3 size={13} /> 新用户限时礼遇</span>
          <span>加入 LabuTV，领取全模态创作体验包</span>
          <button type="button" onClick={() => setPromoVisible(false)} aria-label="关闭活动栏"><X size={16} /></button>
        </div>
      )}

      <header className="site-header">
        <a className="site-logo" href="#top" aria-label="LabuTV 首页">
          <span><BrandIcon /></span><strong>LabuTV</strong>
        </a>
        <nav>
          <div className="account-menu-wrap" onClick={(event) => event.stopPropagation()}>
            {!authReady ? (
              <button className="auth-entry loading" type="button" aria-label="正在读取账号"><LoaderCircle className="spinning" size={17} /></button>
            ) : authUser ? (
              <button
                className={accountOpen ? "avatar-button active" : "avatar-button"}
                type="button"
                aria-label="打开我的菜单"
                aria-expanded={accountOpen}
                onClick={() => { setOpenMenu(null); setAccountOpen((open) => !open); }}
              >
                {(authUser.email?.[0] ?? "创").toLocaleUpperCase()}
              </button>
            ) : (
              <button className="auth-entry" type="button" onClick={openAuth}><LogIn size={16} />登录</button>
            )}

            {accountOpen && authUser && (
              <div className="account-popover">
                <div className="account-card">
                  <span className="account-avatar"><UserRound size={19} /></span>
                  <span><b>{authUser.email?.split("@")[0] || "创作者"}</b><small>{authUser.email}</small></span>
                </div>
                <div className="account-sync"><Cloud size={13} /><span>账号设置与我的 Skill 已云端同步</span></div>
                <div className="account-menu-section">
                  <button className="account-menu-item" type="button" onClick={() => { setPageTab("mine"); setCategory("推荐"); setAccountOpen(false); document.querySelector(".skill-market")?.scrollIntoView({ behavior: "smooth" }); }}><Bot size={16} /><span>我的 Skill</span><b>{userSkillRecords.length}</b></button>
                  <button className="account-menu-item" type="button" onClick={() => { setPageTab("favorite"); setAccountOpen(false); document.querySelector(".skill-market")?.scrollIntoView({ behavior: "smooth" }); }}><Star size={16} /><span>我的收藏</span><b>{favorites.size}</b></button>
                </div>
                <div className="account-theme-row">
                  <span>外观</span>
                  <div className="account-theme-switch" role="group" aria-label="外观主题">
                    <button className={theme === "dark" ? "active" : ""} type="button" onClick={() => changeTheme("dark")}><Moon size={14} />深色</button>
                    <button className={theme === "light" ? "active" : ""} type="button" onClick={() => changeTheme("light")}><Sun size={14} />浅色</button>
                  </div>
                </div>
                <button className="account-signout" type="button" onClick={() => { void signOut().then(() => { setAccountOpen(false); setToast("已退出登录"); }).catch((reason) => setToast(reason instanceof Error ? reason.message : "退出失败")); }}><LogOut size={15} />退出登录</button>
              </div>
            )}
          </div>
        </nav>
      </header>

      <div className="skill-home-content" id="top">
        <section className="skill-hero">
          <div className="hero-copy">
            <h1>一个 Skill，打开一种可能</h1>
          </div>

          <section className="skill-composer" onClick={(event) => event.stopPropagation()}>
            <div className="composer-prompt-row">
              {selectedSkill && (
                <div className="composer-selected-token">
                  <button className="token-main" type="button" title="更换 Skill" onClick={() => setOpenMenu(openMenu === "skill" ? null : "skill")}>
                    <LineIcon line={selectedSkill.line} /><span>{selectedSkill.title}</span>
                  </button>
                  <button className="token-remove" type="button" title="移除 Skill" aria-label={`移除 ${selectedSkill.title}`} onClick={removeSelectedSkill}><X size={12} /></button>
                </div>
              )}
              {selectedModel && (
                <div className="composer-selected-token">
                  <button className="token-main" type="button" title="更换模型" onClick={() => setOpenMenu(openMenu === "model" ? null : "model")}>
                    <Box size={15} /><span>{selectedModel.name}</span>
                  </button>
                  <button className="token-remove" type="button" title="移除模型" aria-label={`移除 ${selectedModel.name}`} onClick={removeSelectedModel}><X size={12} /></button>
                </div>
              )}
              <textarea
                ref={promptRef}
                value={prompt}
                aria-label="创作需求"
                placeholder={selectedSkill ? `使用「${selectedSkill.title}」：${selectedSkill.description}` : "描述你想创作的内容…"}
                onChange={(event) => setPrompt(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Backspace" && !prompt) {
                    event.preventDefault();
                    if (selectedModel) removeSelectedModel();
                    else if (selectedSkill) removeSelectedSkill();
                    return;
                  }
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    submit();
                  }
                }}
              />
            </div>

            <div className="composer-inline-choices" aria-label="创作设置">
              <div className="composer-menu-wrap">
                <button className={openMenu === "model" ? "composer-menu-button icon-only active" : "composer-menu-button icon-only"} type="button" title="选择模型" aria-label="选择模型" aria-expanded={openMenu === "model"} onClick={() => setOpenMenu(openMenu === "model" ? null : "model")}>
                  <Box size={17} />
                </button>
                {openMenu === "model" && (
                  <div className="floating-panel model-picker" role="dialog" aria-label="选择模型">
                    <div className="floating-panel-title"><strong>选择模型</strong><small>按创作任务切换模态</small></div>
                    <div className="segmented-tabs" role="tablist">
                      {(Object.keys(MODALITY_LABELS) as ModelModality[]).map((item) => (
                        <button key={item} className={modality === item ? "active" : ""} type="button" role="tab" aria-selected={modality === item} onClick={() => setModality(item)}>{MODALITY_LABELS[item]}</button>
                      ))}
                    </div>
                    <div className="model-list">
                      {MODEL_GROUPS[modality].map((model) => (
                        <button
                          key={model.id}
                          className={selectedModels[modality] === model.id ? "model-row selected" : "model-row"}
                          type="button"
                          onClick={() => { setSelectedModels((current) => ({ ...current, [modality]: model.id })); setOpenMenu(null); }}
                        >
                          <span className={`model-mark provider-${model.provider.toLocaleLowerCase().replace(/\W+/g, "-")}`}>{modelMark(model)}</span>
                          <span className="model-copy"><b>{model.name}</b><small>{model.description}</small></span>
                          <span className={`availability ${model.availability}`}>{model.availability === "api" ? "API" : model.availability === "preview" ? "预览" : "平台"}</span>
                          <Plus size={16} />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="composer-menu-wrap">
                <button className={openMenu === "skill" ? "composer-menu-button icon-only active" : "composer-menu-button icon-only"} type="button" title="选择 Skill" aria-label="选择 Skill" aria-expanded={openMenu === "skill"} onClick={() => setOpenMenu(openMenu === "skill" ? null : "skill")}>
                  <Bot size={17} />
                </button>
                {openMenu === "skill" && (
                  <div className="floating-panel skill-picker" role="dialog" aria-label="选择 Skill">
                    <div className="skill-picker-heading"><strong>Skill</strong></div>
                    <div className="skill-picker-tabs">
                      {([['all', '全部'], ['common', '常用'], ['favorite', '收藏'], ['mine', '我的']] as const).map(([key, label]) => (
                        <button key={key} className={skillTab === key ? "active" : ""} type="button" onClick={() => selectSkillPickerTab(key)}>{label}</button>
                      ))}
                    </div>
                    <label className="panel-search"><Search size={15} /><input value={skillPickerQuery} onChange={(event) => setSkillPickerQuery(event.target.value)} placeholder="搜索 Skill" /></label>
                    <div className="skill-picker-list">
                      {pickerSkills.map((skill) => (
                        <div className={selectedSkillId === skill.id ? "skill-picker-row selected" : "skill-picker-row"} key={skill.id}>
                          <button type="button" className="skill-picker-main" onClick={() => useSkill(skill)}>
                            <span className="picker-skill-icon"><LineIcon line={skill.line} /></span>
                            <span><b>{skill.title}</b><small>{customSkillIds.has(skill.id) ? "我的 Skill" : `/${skill.skill}`}</small><em>{skill.description}</em></span>
                          </button>
                          <button type="button" className="detail-link" onClick={() => setDetailSkill(skill)}>详情</button>
                        </div>
                      ))}
                      {!pickerSkills.length && <div className="picker-empty">{skillTab === "mine" && !authUser ? "登录后查看我的 Skill" : "没有匹配的 Skill"}</div>}
                    </div>
                  </div>
                )}
              </div>

              <div className="composer-menu-wrap compact">
                <button className={openMenu === "mode" ? "composer-menu-button icon-only active" : "composer-menu-button icon-only"} type="button" title={generationMode === "auto" ? "自动模式" : "手动模式"} aria-label={generationMode === "auto" ? "自动模式" : "手动模式"} aria-expanded={openMenu === "mode"} onClick={() => setOpenMenu(openMenu === "mode" ? null : "mode")}>
                  <Layers3 size={17} />
                </button>
                {openMenu === "mode" && (
                  <div className="floating-panel mode-picker" role="dialog" aria-label="生成模式">
                    <strong>生成模式</strong>
                    <button className={generationMode === "manual" ? "selected" : ""} type="button" onClick={() => { setGenerationMode("manual"); setOpenMenu(null); }}><span><b>手动模式</b><small>Agent 在每次生成前询问</small></span><i /></button>
                    <button className={generationMode === "auto" ? "selected" : ""} type="button" onClick={() => { setGenerationMode("auto"); setOpenMenu(null); }}><span><b>自动模式</b><small>Agent 按工作流连续推进</small></span><i /></button>
                  </div>
                )}
              </div>
            </div>
            {attachments.length > 0 && (
              <div className="composer-attachments">
                {attachments.map((attachment) => (
                  <button key={attachment.id} type="button" onClick={() => setAttachments((items) => items.filter((item) => item.id !== attachment.id))}>
                    <Paperclip size={14} /><span>{attachment.name}</span><X size={13} />
                  </button>
                ))}
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              hidden
              onChange={(event) => {
                const next = Array.from(event.target.files ?? []).map(toAttachment);
                setAttachments((items) => [...items, ...next]);
                event.target.value = "";
              }}
            />
            <div className="skill-composer-toolbar">
              <button className="composer-icon-button" type="button" title="添加文件" aria-label="添加文件" onClick={() => fileInputRef.current?.click()}><Plus size={21} /></button>
              <span className="composer-toolbar-hint">回车开始 · Shift + 回车换行</span>
              <span className="composer-grow" />
              <button className="composer-submit" type="button" disabled={!ready} onClick={submit} aria-label="开始创作"><ArrowUp size={21} /></button>
            </div>
          </section>
        </section>

        <section className="skill-market">
          <div className="market-toolbar">
            <div className="market-tabs">
              <div>
                <button className={pageTab === "skills" ? "active" : ""} type="button" onClick={() => setPageTab("skills")}>Skill</button>
                <button className={pageTab === "favorite" ? "active" : ""} type="button" onClick={() => setPageTab("favorite")}>收藏</button>
                <button className={pageTab === "mine" ? "active" : ""} type="button" onClick={openMine}>我的</button>
              </div>
              {pageTab === "mine" && authUser && <button className="create-skill-button" type="button" onClick={openCreateSkill}><Plus size={15} />创建 Skill</button>}
            </div>

            <div className="market-filters">
              <div className="category-scroll">
                {MARKET_CATEGORIES.map((item) => <button key={item} className={category === item ? "active" : ""} type="button" onClick={() => setCategory(item)}>{item}</button>)}
              </div>
              <label className="market-search"><Search size={16} /><input aria-label="搜索 Skill" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索 Skill" /></label>
            </div>
          </div>

          {pageTab === "mine" && !authUser ? (
            <div className="mine-gate">
              <span><UserRound size={24} /></span>
              <strong>登录后管理你的 Skill</strong>
              <p>输入邮箱和密码，首次登录会自动创建账号。</p>
              <div><button type="button" onClick={openAuth}>登录 / 注册</button></div>
            </div>
          ) : userSkillsLoading && pageTab === "mine" ? (
            <div className="empty-skills"><LoaderCircle className="spinning" size={28} /><strong>正在加载我的 Skill</strong><span>从云端同步你的个人工作流</span></div>
          ) : visibleSkills.length ? (
            <div className="skill-grid">
              {visibleSkills.map((skill, index) => (
                <article className="skill-card" key={skill.id} onClick={() => setDetailSkill(skill)}>
                  <div className="skill-cover" style={{ "--skill-accent": skill.accent } as CSSProperties}>
                    <span className="skill-media-badge"><Play size={11} fill="currentColor" />{MEDIA_LABELS[skill.mediaType]}</span>
                    <span className="cover-orbit orbit-one" /><span className="cover-orbit orbit-two" />
                    <LineIcon line={skill.line} />
                    <small>{String(index + 1).padStart(2, "0")}</small>
                  </div>
                  <div className="skill-card-copy">
                    <div className="skill-card-title"><h3>{skill.title}</h3><span className="verified">◆</span></div>
                    <p>{skill.description}</p>
                    <footer><span>{skill.creator}</span><span className="card-metric"><Play size={12} />{skill.views > 0 ? compactNumber(skill.views) : "已实现"}</span></footer>
                  </div>
                  <div className="skill-card-actions">
                    <button type="button" title={favorites.has(skill.id) ? "取消收藏" : "收藏"} aria-label={favorites.has(skill.id) ? "取消收藏" : "收藏"} className={favorites.has(skill.id) ? "favorite active" : "favorite"} onClick={(event) => { event.stopPropagation(); toggleFavorite(skill.id); }}><Star size={17} fill={favorites.has(skill.id) ? "currentColor" : "none"} /></button>
                    {customSkillIds.has(skill.id) && <button type="button" className="skill-delete-button" title="删除 Skill" aria-label={`删除 ${skill.title}`} onClick={(event) => { event.stopPropagation(); void removeUserSkill(skill).catch((reason) => setToast(reason instanceof Error ? reason.message : "删除失败")); }}><Trash2 size={15} /></button>}
                    <button type="button" className="use-skill-button" onClick={(event) => { event.stopPropagation(); useSkill(skill); }}>使用</button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-skills">
              {pageTab === "mine" ? <Bot size={28} /> : <Search size={28} />}
              <strong>{pageTab === "mine" ? "还没有创建 Skill" : "没有找到匹配的 Skill"}</strong>
              <span>{pageTab === "mine" ? "把你的创作方法封装成可重复使用的工作流" : "换个关键词或分类试试"}</span>
              {pageTab === "mine" && <button type="button" onClick={openCreateSkill}><Plus size={15} />创建第一个 Skill</button>}
            </div>
          )}
        </section>
      </div>

      {detailSkill && (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setDetailSkill(null)}>
          <section className="skill-detail-modal" role="dialog" aria-modal="true" aria-label={detailSkill.title} onMouseDown={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" aria-label="关闭" onClick={() => setDetailSkill(null)}><X size={20} /></button>
            {detailPreview && failedPreviewSkillId !== detailSkill.id ? (
              <div className="skill-detail-preview media-mode" style={{ "--skill-accent": detailSkill.accent } as CSSProperties}>
                {detailPreview.kind === "image" ? (
                  <img src={detailPreview.src} alt={detailPreview.alt} onError={() => setFailedPreviewSkillId(detailSkill.id)} />
                ) : (
                  <video src={detailPreview.src} poster={detailPreview.poster} controls preload="metadata" onError={() => setFailedPreviewSkillId(detailSkill.id)} />
                )}
              </div>
            ) : (
              <div className="skill-detail-preview source-mode">
                <div className="skill-source-tabs" role="tablist" aria-label={`${detailSkill.title}系列 Skill 文件`}>
                  {detailSkillSources.length ? detailSkillSources.map((file) => (
                    <button
                      className={activeSourceFile?.id === file.id ? "active" : ""}
                      type="button"
                      role="tab"
                      aria-selected={activeSourceFile?.id === file.id}
                      title={file.path}
                      key={file.id}
                      onClick={() => setActiveSourceFileId(file.id)}
                    >
                      <FileCode2 size={14} /><span>{file.name}</span>
                    </button>
                  )) : <span className="skill-source-loading"><LoaderCircle className="spinning" size={14} />正在读取 Skill 文件…</span>}
                </div>
                <pre key={activeSourceFile?.id ?? "loading"}><code>{activeSourceFile?.source || "正在读取 Skill 源码…"}</code></pre>
              </div>
            )}
            <div className="skill-detail-copy">
              <span className="detail-eyebrow">{detailSkill.category}</span>
              <h2>{detailSkill.title}</h2>
              <p className="detail-creator">by {detailSkill.creator} · <Play size={12} />{compactNumber(detailSkill.views)} 次使用</p>
              <div className="detail-actions">
                <button type="button" onClick={() => { void navigator.clipboard?.writeText(window.location.href); setToast("页面链接已复制"); }}><Share2 size={15} />分享</button>
                <button className={favorites.has(detailSkill.id) ? "active favorite-detail" : "favorite-detail"} type="button" onClick={() => toggleFavorite(detailSkill.id)}><Star size={15} fill={favorites.has(detailSkill.id) ? "currentColor" : "none"} />收藏</button>
                {customSkillIds.has(detailSkill.id) && <button className="danger" type="button" onClick={() => { void removeUserSkill(detailSkill).catch((reason) => setToast(reason instanceof Error ? reason.message : "删除失败")); }}><Trash2 size={15} />删除</button>}
                <button className="primary" type="button" onClick={() => useSkill(detailSkill)}><Plus size={16} />添加 Skill</button>
              </div>
              <div className="detail-scroll">
                <h3>简介</h3><p>{detailSkill.description}</p>
                <h3>使用场景</h3><ul>{detailSkill.useCases.map((item) => <li key={item}>{item}</li>)}</ul>
                <h3>工作流</h3><ol>{detailSkill.steps.map((item) => <li key={item}>{item}</li>)}</ol>
                <h3>如何使用</h3><p>{detailSkill.guide}</p>
              </div>
            </div>
          </section>
        </div>
      )}

      <AuthDialog
        open={authOpen}
        configured={authIsConfigured()}
        onClose={() => setAuthOpen(false)}
        onContinue={async (email, password) => {
          const result = await signInOrSignUpWithEmail({ email, password, emailRedirectTo: window.location.origin });
          if (result.confirmationRequired) return { message: "首次登录已自动创建账号。验证邮件已发送，请完成邮箱验证后继续。" };
          setToast(result.action === "signed-up" ? "账号已创建并登录" : "登录成功");
          return {};
        }}
      />
      <CreateSkillDialog open={createSkillOpen} ownerEmail={authUser?.email ?? ""} onClose={() => setCreateSkillOpen(false)} onCreate={handleCreateSkill} />
      {toast && <div className="home-toast"><Bell size={15} />{toast}</div>}
      <button className="floating-help" type="button" title="帮助中心" onClick={() => setToast("帮助中心正在整理中")}><CircleHelp size={20} /></button>
    </main>
  );
}
