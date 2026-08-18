import {
  ArrowUp,
  Bell,
  Bot,
  Box,
  Check,
  ChevronRight,
  CircleHelp,
  ClipboardPenLine,
  Clock3,
  Cloud,
  FileCode2,
  Hand,
  LoaderCircle,
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
  Wrench,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { BrandIcon } from "../../components/BrandIcon";
import { ComposerAssetPicker } from "../../components/ComposerAssetPicker";
import { LineIcon } from "../../components/LineIcon";
import { RUNTIME_MODEL_MODALITIES, runtimeModelDefinitions } from "../../catalog/runtimeModels";
import {
  listSkillSourceGroups,
  loadSkillSourceFile,
  type SkillSourceFile,
  type SkillSourceGroup,
} from "../../catalog/skillSources";
import { SKILLS } from "../../catalog/skills";
import type { ModelDefinition, ModelModality, SkillCategory, SkillDefinition } from "../../catalog/types";
import { getMySettings, signInOrSignUpWithEmail, signOut, subscribeAuth, updateMySettings, type AuthUser } from "../../lib/auth";
import { isAuthConfigured } from "../../lib/cloud";
import { discoverCanvasModels } from "../../lib/generation";
import type { ThemeMode } from "../../lib/theme";
import { createUserSkill, deleteUserSkill, listUserSkills, type UserSkillRecord } from "../../lib/userSkills";
import { createWebWork, saveWork } from "../../lib/work";
import type { CreationLine, PendingAttachment, WebWork } from "../../types";
import { AuthDialog } from "../account/AuthDialog";
import { MembershipDialog } from "../account/MembershipDialog";
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
const LINE_ACCENTS: Record<CreationLine, string> = { novel: "#8b8d96", n2d: "#8b8d96", comic: "#8b8d96", ad: "#8b8d96", mv: "#8b8d96", song: "#8b8d96" };
const LINE_COVERS: Record<CreationLine, string> = {
  novel: "/skill-covers/novel.jpg",
  n2d: "/skill-covers/n2d.jpg",
  comic: "/skill-covers/comic.jpg",
  ad: "/skill-covers/ad.jpg",
  mv: "/skill-covers/mv.jpg",
  song: "/skill-covers/song.jpg",
};

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

type OpenMenu = "assets" | "model" | "skill" | "mode" | null;
type SkillTab = "common" | "favorite" | "mine";
type SkillLibraryTab = "skills" | "favorite" | "mine";

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

export function SkillHomePage({
  onCreate,
  theme,
  onThemeChange,
}: {
  onCreate: (work: WebWork, attachments: PendingAttachment[]) => void;
  theme: ThemeMode;
  onThemeChange: (theme: ThemeMode) => void;
}) {
  const authConfigured = isAuthConfigured();
  const promptRef = useRef<HTMLTextAreaElement>(null);
  const [prompt, setPrompt] = useState("");
  const [localAssets, setLocalAssets] = useState<PendingAttachment[]>([]);
  const [composerAttachmentIds, setComposerAttachmentIds] = useState<string[]>([]);
  const [openMenu, setOpenMenu] = useState<OpenMenu>(null);
  const [modality, setModality] = useState<ModelModality>("text");
  const [selectedModels, setSelectedModels] = useState<Record<ModelModality, string>>(() => ({
    text: "",
    image: "",
    video: "",
    audio: "",
  }));
  const [runtimeModels, setRuntimeModels] = useState<ModelDefinition[]>([]);
  const [runtimeModelsState, setRuntimeModelsState] = useState<"loading" | "ready" | "unavailable">("loading");
  const [runtimeModelsRefresh, setRuntimeModelsRefresh] = useState(0);
  const [selectedSkillId, setSelectedSkillId] = useState(SKILLS[0]?.id ?? "");
  const [generationMode, setGenerationMode] = useState<"manual" | "auto">("auto");
  const [skillTab, setSkillTab] = useState<SkillTab>("common");
  const [skillPickerQuery, setSkillPickerQuery] = useState("");
  const [pageTab, setPageTab] = useState<SkillLibraryTab>("skills");
  const [category, setCategory] = useState("推荐");
  const [query, setQuery] = useState("");
  const [favorites, setFavorites] = useState<Set<string>>(readFavorites);
  const [detailSkill, setDetailSkill] = useState<SkillDefinition | null>(null);
  const [allSkillsOpen, setAllSkillsOpen] = useState(false);
  const [catalogTab, setCatalogTab] = useState<SkillLibraryTab>("skills");
  const [catalogCategory, setCatalogCategory] = useState("推荐");
  const [catalogQuery, setCatalogQuery] = useState("");
  const [failedPreviewSkillId, setFailedPreviewSkillId] = useState<string | null>(null);
  const [detailSkillSourceGroups, setDetailSkillSourceGroups] = useState<SkillSourceGroup[]>([]);
  const [activeSourceGroupId, setActiveSourceGroupId] = useState("");
  const [activeSourceFileId, setActiveSourceFileId] = useState("");
  const [activeSourceText, setActiveSourceText] = useState("");
  const [sourceLoading, setSourceLoading] = useState(false);
  const [promoVisible, setPromoVisible] = useState(true);
  const [toast, setToast] = useState("");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [membershipOpen, setMembershipOpen] = useState(false);
  const [pageAfterAuth, setPageAfterAuth] = useState<"favorite" | "mine" | null>(null);
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
    () => runtimeModels.find((model) => model.modality === modality && model.id === selectedModels[modality]),
    [modality, runtimeModels, selectedModels],
  );
  const visibleRuntimeModels = useMemo(
    () => runtimeModels.filter((model) => model.modality === modality),
    [modality, runtimeModels],
  );
  const detailPreview = useMemo(() => detailSkill ? getSkillPreview(detailSkill) : undefined, [detailSkill]);
  const activeSourceGroup = useMemo(
    () => detailSkillSourceGroups.find((group) => group.id === activeSourceGroupId) ?? detailSkillSourceGroups[0],
    [activeSourceGroupId, detailSkillSourceGroups],
  );
  const activeSourceFile = useMemo(
    () => activeSourceGroup?.files.find((file) => file.id === activeSourceFileId) ?? activeSourceGroup?.files[0],
    [activeSourceFileId, activeSourceGroup],
  );
  const attachments = useMemo(
    () => localAssets.filter((asset) => composerAttachmentIds.includes(asset.id)),
    [composerAttachmentIds, localAssets],
  );
  const ready = Boolean(prompt.trim() || attachments.length || selectedSkill || selectedModel);

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

  const catalogSkills = useMemo(() => {
    const normalizedQuery = catalogQuery.trim().toLocaleLowerCase();
    return allSkills.filter((skill) => {
      if (catalogTab === "favorite" && !favorites.has(skill.id)) return false;
      if (catalogTab === "mine" && !customSkillIds.has(skill.id)) return false;
      if (catalogTab === "skills" && !matchesMarketCategory(skill, catalogCategory)) return false;
      if (!normalizedQuery) return true;
      return `${skill.title} ${skill.description} ${skill.creator}`.toLocaleLowerCase().includes(normalizedQuery);
    });
  }, [allSkills, catalogCategory, catalogQuery, catalogTab, customSkillIds, favorites]);

  useEffect(() => {
    const controller = new AbortController();
    setRuntimeModelsState("loading");
    setRuntimeModels([]);
    void discoverCanvasModels(controller.signal)
      .then((models) => {
        if (controller.signal.aborted) return;
        const discovered = runtimeModelDefinitions(models);
        setRuntimeModels(discovered);
        setSelectedModels((current) => ({
          text: discovered.some((model) => model.modality === "text" && model.id === current.text)
            ? current.text
            : discovered.find((model) => model.modality === "text")?.id ?? "",
          image: discovered.some((model) => model.modality === "image" && model.id === current.image)
            ? current.image
            : discovered.find((model) => model.modality === "image")?.id ?? "",
          video: "",
          audio: "",
        }));
        setModality((current) => discovered.some((model) => model.modality === current)
          ? current
          : discovered.some((model) => model.modality === "text") ? "text" : "image");
        setRuntimeModelsState("ready");
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        setRuntimeModels([]);
        setSelectedModels({ text: "", image: "", video: "", audio: "" });
        setModality("text");
        setRuntimeModelsState("unavailable");
      });
    return () => controller.abort();
  }, [runtimeModelsRefresh]);

  useEffect(() => subscribeAuth((user) => { setAuthUser(user); setAuthReady(true); }), []);

  useEffect(() => {
    if (!authUser || !pageAfterAuth) return;
    setPageTab(pageAfterAuth);
    setCategory("推荐");
    setPageAfterAuth(null);
    window.requestAnimationFrame(() => document.querySelector(".skill-market")?.scrollIntoView({ behavior: "smooth" }));
  }, [authUser, pageAfterAuth]);

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
      else if (allSkillsOpen) setAllSkillsOpen(false);
      else if (accountOpen) setAccountOpen(false);
      else setOpenMenu(null);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [accountOpen, allSkillsOpen, detailSkill]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(""), 2200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => setFailedPreviewSkillId(null), [detailSkill?.id]);

  useEffect(() => {
    let cancelled = false;
    if (!detailSkill) {
      setDetailSkillSourceGroups([]);
      setActiveSourceGroupId("");
      setActiveSourceFileId("");
      setActiveSourceText("");
      setSourceLoading(false);
      return undefined;
    }
    setDetailSkillSourceGroups([]);
    setActiveSourceGroupId("");
    setActiveSourceFileId("");
    setActiveSourceText("");
    setSourceLoading(true);
    void listSkillSourceGroups(detailSkill)
      .then((groups) => {
        if (cancelled) return;
        const firstGroup = groups[0];
        setDetailSkillSourceGroups(groups);
        setActiveSourceGroupId(firstGroup?.id ?? "");
        setActiveSourceFileId(firstGroup?.files[0]?.id ?? "");
        if (!firstGroup?.files.length) setSourceLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setSourceLoading(false);
        setToast("Skill 源文件暂时无法读取");
      });
    return () => { cancelled = true; };
  }, [detailSkill]);

  useEffect(() => {
    let cancelled = false;
    if (!activeSourceFile) {
      setActiveSourceText("");
      setSourceLoading(false);
      return undefined;
    }
    setSourceLoading(true);
    setActiveSourceText("");
    void loadSkillSourceFile(activeSourceFile)
      .then((source) => { if (!cancelled) setActiveSourceText(source); })
      .catch(() => { if (!cancelled) setActiveSourceText("# 文件读取失败\n\n请切换文件或关闭详情后重试。"); })
      .finally(() => { if (!cancelled) setSourceLoading(false); });
    return () => { cancelled = true; };
  }, [activeSourceFile]);

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

  function requestFavorite(skillId: string) {
    if (!authUser) {
      openAuth();
      return;
    }
    toggleFavorite(skillId);
  }

  function useSkill(skill: SkillDefinition, notify = true) {
    setSelectedSkillId(skill.id);
    setDetailSkill(null);
    setAllSkillsOpen(false);
    setOpenMenu(null);
    if (notify) setToast(`已添加「${skill.title}」`);
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

  function toggleModelMenu() {
    const opening = openMenu !== "model";
    setOpenMenu(opening ? "model" : null);
    if (opening && runtimeModelsState === "unavailable") {
      setRuntimeModelsRefresh((current) => current + 1);
    }
  }

  function uploadComposerAssets(files: File[]) {
    const next = files.map(toAttachment);
    if (!next.length) return [];
    setLocalAssets((items) => [...items, ...next]);
    setComposerAttachmentIds((ids) => [...new Set([...ids, ...next.map((asset) => asset.id)])]);
    return next.map((asset) => asset.id);
  }

  function submit() {
    if (!ready) return;
    const effectiveSkill = selectedSkill ?? allSkills[0] ?? SKILLS[0];
    if (!effectiveSkill) return;
    if (runtimeModelsState !== "ready" || !selectedModel) {
      setToast(runtimeModelsState === "unavailable" ? "后端模型服务不可用，请稍后重试" : "正在读取后端可用模型，请稍候");
      setOpenMenu("model");
      return;
    }
    const effectiveModel = selectedModel;
    const customRecord = userSkillRecords.find((skill) => `user:${skill.id}` === effectiveSkill.id);
    const work = createWebWork(effectiveSkill.line, prompt, attachments, {
      skillId: effectiveSkill.id,
      ...(customRecord ? { skillDefinition: { title: effectiveSkill.title, description: effectiveSkill.description, guide: effectiveSkill.guide, steps: effectiveSkill.steps, useCases: effectiveSkill.useCases } } : {}),
      generationMode,
      model: {
        modality: effectiveModel.modality,
        modelId: effectiveModel.modelId ?? effectiveModel.id,
        ...(effectiveModel.providerSpec ? { providerSpec: effectiveModel.providerSpec } : {}),
      },
    });
    saveWork(work);
    onCreate(work, attachments);
  }

  function openAuth() {
    setOpenMenu(null);
    setAccountOpen(false);
    if (!authConfigured) {
      setToast("账号能力正在迁移到后端 REST API，本地模式暂不可用");
      return;
    }
    setAuthOpen(true);
  }

  function openMine() {
    if (!authUser) {
      setPageAfterAuth("mine");
      openAuth();
      return;
    }
    setPageTab("mine");
    setCategory("推荐");
  }

  function openFavorites() {
    if (!authUser) {
      setPageAfterAuth("favorite");
      openAuth();
      return;
    }
    setPageTab("favorite");
    setCategory("推荐");
  }

  function selectSkillPickerTab(nextTab: SkillTab) {
    if ((nextTab === "mine" || nextTab === "favorite") && !authUser) {
      setPageAfterAuth(nextTab);
      openAuth();
      return;
    }
    setSkillTab(nextTab);
  }

  function openAllSkills() {
    setOpenMenu(null);
    setCatalogTab("skills");
    setCatalogCategory("推荐");
    setCatalogQuery("");
    setAllSkillsOpen(true);
  }

  function selectCatalogTab(nextTab: SkillLibraryTab) {
    if ((nextTab === "favorite" || nextTab === "mine") && !authUser) {
      setAllSkillsOpen(false);
      setPageAfterAuth(nextTab);
      openAuth();
      return;
    }
    setCatalogTab(nextTab);
    setCatalogQuery("");
  }

  function openCreateSkill() {
    setOpenMenu(null);
    if (!authUser) {
      setToast("登录后即可创建并云端保存 Skill");
      setPageAfterAuth("mine");
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
          <div
            className="account-menu-wrap"
            onClick={(event) => event.stopPropagation()}
            onMouseEnter={() => { if (authUser) setAccountOpen(true); }}
            onMouseLeave={() => { if (authUser) setAccountOpen(false); }}
          >
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
              <button className="auth-entry" type="button" disabled={!authConfigured} onClick={openAuth}>{authConfigured ? "注册/登录" : "账号待接入"}</button>
            )}

            {accountOpen && authUser && (
              <div className="account-popover">
                <div className="account-card">
                  <span className="account-avatar"><UserRound size={19} /></span>
                  <span>
                    <b>{String(authUser.user_metadata?.display_name || authUser.email?.split("@")[0] || "创作者")}</b>
                    <small>{authUser.email}</small>
                    <em>ID {authUser.id.slice(0, 8)}</em>
                  </span>
                </div>

                <div className="account-plan-card">
                  <span><b>免费用户</b><small>基础创作账户</small></span>
                  <button type="button" onClick={() => { setAccountOpen(false); setMembershipOpen(true); }}>开通会员</button>
                </div>

                <div className="account-stats-card">
                  <div className="account-stats-heading"><b>个人空间</b><span><Cloud size={12} />已云端同步</span></div>
                  <div>
                    <button type="button" onClick={() => { setPageTab("favorite"); setAccountOpen(false); document.querySelector(".skill-market")?.scrollIntoView({ behavior: "smooth" }); }}><strong>{favorites.size}</strong><span>收藏 Skill</span></button>
                    <button type="button" onClick={() => { setPageTab("mine"); setCategory("推荐"); setAccountOpen(false); document.querySelector(".skill-market")?.scrollIntoView({ behavior: "smooth" }); }}><strong>{userSkillRecords.length}</strong><span>我的 Skill</span></button>
                  </div>
                </div>

                <div className="account-menu-section">
                  <button className="account-menu-item" type="button" onClick={() => { setPageTab("mine"); setCategory("推荐"); setAccountOpen(false); document.querySelector(".skill-market")?.scrollIntoView({ behavior: "smooth" }); }}><Bot size={17} /><span>我的 Skill</span><b>{userSkillRecords.length}</b></button>
                  <button className="account-menu-item" type="button" onClick={() => { setPageTab("favorite"); setAccountOpen(false); document.querySelector(".skill-market")?.scrollIntoView({ behavior: "smooth" }); }}><Star size={17} /><span>我的收藏</span><b>{favorites.size}</b></button>
                  <div className="account-theme-row">
                    <span><Moon size={17} />模式切换</span>
                    <div className="account-theme-switch" role="group" aria-label="外观主题">
                      <button className={theme === "light" ? "active" : ""} type="button" aria-label="浅色模式" title="浅色模式" onClick={() => changeTheme("light")}><Sun size={14} /></button>
                      <button className={theme === "dark" ? "active" : ""} type="button" aria-label="深色模式" title="深色模式" onClick={() => changeTheme("dark")}><Moon size={14} /></button>
                    </div>
                  </div>
                  <button className="account-menu-item" type="button" onClick={() => setToast("账号设置与 Skill 已同步到云端")}><Cloud size={17} /><span>账号与同步</span></button>
                  <button className="account-signout" type="button" onClick={() => { void signOut().then(() => { setAccountOpen(false); setToast("已退出登录"); }).catch((reason) => setToast(reason instanceof Error ? reason.message : "退出失败")); }}><LogOut size={17} />退出登录</button>
                </div>
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
                  <button className="token-main" type="button" title="更换模型" onClick={toggleModelMenu}>
                    <Box size={15} /><span>{selectedModel.name}</span>
                  </button>
                  <button className="token-remove" type="button" title="移除模型" aria-label={`移除 ${selectedModel.name}`} onClick={removeSelectedModel}><X size={12} /></button>
                </div>
              )}
              <textarea
                ref={promptRef}
                value={prompt}
                aria-label="创作需求"
                placeholder={prompt || selectedSkill || selectedModel ? "" : "请输入你的创作灵感，或从下方挑选一个 Skill 开始"}
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
              <div className="composer-menu-wrap model-menu-wrap">
                <button className={openMenu === "model" ? "composer-menu-button icon-only active" : "composer-menu-button icon-only"} type="button" title="选择模型" aria-label="选择模型" aria-expanded={openMenu === "model"} onClick={toggleModelMenu}>
                  <Box size={18} strokeWidth={1.6} />
                </button>
                {openMenu === "model" && (
                  <div className="floating-panel model-picker" role="dialog" aria-label="选择模型">
                    <div className="floating-panel-title"><strong>选择模型</strong></div>
                    <div className="segmented-tabs" role="tablist">
                      {RUNTIME_MODEL_MODALITIES.map((item) => (
                        <button key={item} className={modality === item ? "active" : ""} type="button" role="tab" aria-selected={modality === item} onClick={() => setModality(item)}>{MODALITY_LABELS[item]}</button>
                      ))}
                    </div>
                    <div className="model-section-label">{MODALITY_LABELS[modality]}</div>
                    <div className={`model-runtime-status state-${runtimeModelsState}`}>
                      <i />
                      {runtimeModelsState === "loading"
                        ? "正在读取后端开放模型…"
                        : runtimeModelsState === "unavailable"
                          ? "后端模型服务不可用，当前没有可选模型"
                          : visibleRuntimeModels.length
                            ? `后端已开放 ${visibleRuntimeModels.length} 个可调用模型`
                            : `后端当前未开放${MODALITY_LABELS[modality]}模型`}
                    </div>
                    <p className="model-runtime-note">Skill 编排当前使用 GPT 文本/视觉；图片模型仅用于画布直接生图。</p>
                    <div className="model-list">
                      {visibleRuntimeModels.map((model) => (
                        <div key={model.id} className="model-row">
                          <button className="model-row-main" type="button" onClick={() => { setSelectedModels((current) => ({ ...current, [model.modality]: model.id })); setModality(model.modality); setOpenMenu(null); }}>
                            <span className={`model-mark provider-${model.provider.toLocaleLowerCase().replace(/\W+/g, "-")}`}>{modelMark(model)}</span>
                            <span className="model-copy">
                              <span className="model-name">
                                <b>{model.name}</b>
                              </span>
                              <small>{model.description}</small>
                            </span>
                            <Plus size={16} />
                          </button>
                        </div>
                      ))}
                      {runtimeModelsState === "ready" && !visibleRuntimeModels.length && (
                        <p className="model-runtime-empty">暂无可用{MODALITY_LABELS[modality]}模型。</p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div className="composer-menu-wrap skill-menu-wrap">
                <button className={openMenu === "skill" ? "composer-menu-button icon-only active" : "composer-menu-button icon-only"} type="button" title="选择 Skill" aria-label="选择 Skill" aria-expanded={openMenu === "skill"} onClick={() => setOpenMenu(openMenu === "skill" ? null : "skill")}>
                  <ClipboardPenLine size={18} strokeWidth={1.6} />
                </button>
                {openMenu === "skill" && (
                  <div className="floating-panel skill-picker" role="dialog" aria-label="选择 Skill">
                    <div className="skill-picker-heading">
                      <strong>Skill</strong>
                      <div className="skill-picker-heading-actions">
                        <button type="button" onClick={openCreateSkill}><Plus size={14} />创建</button>
                        <button type="button" onClick={openAllSkills}>全部</button>
                      </div>
                    </div>
                    <div className="skill-picker-toolbar">
                      <div className="skill-picker-tabs">
                        {([['common', '通用'], ['favorite', '收藏'], ['mine', '我的']] as const).map(([key, label]) => (
                          <button key={key} className={skillTab === key ? "active" : ""} type="button" onClick={() => selectSkillPickerTab(key)}>{label}</button>
                        ))}
                      </div>
                      <label className="panel-search"><Search size={15} /><input value={skillPickerQuery} onChange={(event) => setSkillPickerQuery(event.target.value)} placeholder="搜索 Skill" /></label>
                    </div>
                    <div className="skill-picker-list">
                      {pickerSkills.map((skill) => (
                        <div className="skill-picker-row" key={skill.id}>
                          <button type="button" className="skill-picker-main" onClick={() => useSkill(skill)}>
                            <span className="picker-skill-icon"><Wrench size={15} /></span>
                            <span className="skill-picker-copy">
                              <span className="skill-picker-name"><b>{skill.title}</b><small>{customSkillIds.has(skill.id) ? "我的 Skill" : `/${skill.skill}`}</small></span>
                              <em>{skill.description}</em>
                            </span>
                          </button>
                          <button type="button" className="skill-picker-detail" onClick={() => { setOpenMenu(null); setDetailSkill(skill); }}>详情</button>
                        </div>
                      ))}
                      {!pickerSkills.length && <div className="picker-empty">{skillTab === "mine" && !authUser ? "登录后查看我的 Skill" : "没有匹配的 Skill"}</div>}
                      {skillTab === "common" && !skillPickerQuery.trim() && (
                        <button className="skill-picker-view-all" type="button" onClick={openAllSkills}>没找到合适的？查看全部 Skill <ChevronRight size={14} /></button>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div className="composer-menu-wrap compact mode-menu-wrap">
                <button className={openMenu === "mode" ? "composer-menu-button icon-only active" : "composer-menu-button icon-only"} type="button" title={generationMode === "auto" ? "自动模式" : "手动模式"} aria-label={generationMode === "auto" ? "自动模式" : "手动模式"} aria-expanded={openMenu === "mode"} onClick={() => setOpenMenu(openMenu === "mode" ? null : "mode")}>
                  <Hand size={18} strokeWidth={1.6} />
                </button>
                {openMenu === "mode" && (
                  <div className="floating-panel mode-picker" role="dialog" aria-label="生成模式">
                    <strong>生成模式</strong>
                    <button className={generationMode === "manual" ? "selected" : ""} type="button" onClick={() => { setGenerationMode("manual"); setOpenMenu(null); }}><span className="mode-option-copy"><b>手动模式</b><small>Agent 在每次生成前询问</small></span><span className="mode-selection-mark" aria-hidden="true">{generationMode === "manual" && <Check size={15} />}</span></button>
                    <button className={generationMode === "auto" ? "selected" : ""} type="button" onClick={() => { setGenerationMode("auto"); setOpenMenu(null); }}><span className="mode-option-copy"><b>自动模式</b><small>Agent 按工作流连续推进</small></span><span className="mode-selection-mark" aria-hidden="true">{generationMode === "auto" && <Check size={15} />}</span></button>
                  </div>
                )}
              </div>
            </div>
            {attachments.length > 0 && (
              <div className="composer-attachments">
                {attachments.map((attachment) => (
                  <button key={attachment.id} type="button" onClick={() => setComposerAttachmentIds((ids) => ids.filter((id) => id !== attachment.id))}>
                    <Paperclip size={14} /><span>{attachment.name}</span><X size={13} />
                  </button>
                ))}
              </div>
            )}
            <div className="skill-composer-toolbar">
              <ComposerAssetPicker
                assets={localAssets}
                selectedIds={composerAttachmentIds}
                menuOpen={openMenu === "assets"}
                onMenuOpenChange={(open) => setOpenMenu(open ? "assets" : null)}
                onUpload={uploadComposerAssets}
                onSelectionChange={setComposerAttachmentIds}
              />
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
                <button className={pageTab === "favorite" ? "active" : ""} type="button" onClick={openFavorites}>收藏</button>
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
              <strong>{authConfigured ? "登录后管理你的 Skill" : "账号 REST 能力待接入"}</strong>
              <p>{authConfigured ? "输入邮箱和密码，首次登录会自动创建账号。" : "本地模式已禁止浏览器直连账号服务；后端资源落地后恢复。"}</p>
              <div><button type="button" disabled={!authConfigured} onClick={openAuth}>{authConfigured ? "登录" : "暂不可用"}</button></div>
            </div>
          ) : userSkillsLoading && pageTab === "mine" ? (
            <div className="empty-skills"><LoaderCircle className="spinning" size={28} /><strong>正在加载我的 Skill</strong><span>从云端同步你的个人工作流</span></div>
          ) : visibleSkills.length ? (
            <div className="skill-grid">
              {visibleSkills.map((skill) => (
                <article className="skill-card" key={skill.id} onClick={() => setDetailSkill(skill)}>
                  <div className={`skill-cover skill-cover-${skill.line}`}>
                    <img src={LINE_COVERS[skill.line]} alt="" loading="lazy" draggable={false} />
                    <span className="skill-media-badge">{MEDIA_LABELS[skill.mediaType]}</span>
                  </div>
                  <div className="skill-card-copy">
                    <div className="skill-card-title"><h3>{skill.title}</h3></div>
                    <p>{skill.description}</p>
                    <footer><span className="card-metric"><Star size={11} fill="currentColor" />{compactNumber(skill.favorites + (favorites.has(skill.id) ? 1 : 0))}</span></footer>
                  </div>
                  <div className="skill-card-actions">
                    <button type="button" title={favorites.has(skill.id) ? "取消收藏" : "收藏"} aria-label={favorites.has(skill.id) ? "取消收藏" : "收藏"} className={favorites.has(skill.id) ? "favorite active" : "favorite"} onClick={(event) => { event.stopPropagation(); requestFavorite(skill.id); }}><Star size={17} fill={favorites.has(skill.id) ? "currentColor" : "none"} /></button>
                    {customSkillIds.has(skill.id) && <button type="button" className="skill-delete-button" title="删除 Skill" aria-label={`删除 ${skill.title}`} onClick={(event) => { event.stopPropagation(); void removeUserSkill(skill).catch((reason) => setToast(reason instanceof Error ? reason.message : "删除失败")); }}><Trash2 size={15} /></button>}
                    <button type="button" className="use-skill-button" onClick={(event) => { event.stopPropagation(); useSkill(skill, false); }}>使用</button>
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

      {allSkillsOpen && (
        <div className="modal-backdrop skill-catalog-backdrop" role="presentation" onMouseDown={() => setAllSkillsOpen(false)}>
          <section className="skill-catalog-modal" role="dialog" aria-modal="true" aria-label="全部 Skill" onMouseDown={(event) => event.stopPropagation()}>
            <button className="skill-catalog-close" type="button" aria-label="关闭全部 Skill" onClick={() => setAllSkillsOpen(false)}><X size={14} /></button>
            <div className="skill-catalog-scroll">
              <header className="skill-catalog-header">
                <nav className="skill-catalog-tabs" aria-label="Skill 分类">
                  {([['skills', 'Skill'], ['favorite', '收藏'], ['mine', '我的']] as const).map(([key, label]) => (
                    <button key={key} className={catalogTab === key ? "active" : ""} type="button" onClick={() => selectCatalogTab(key)}>{label}</button>
                  ))}
                </nav>
                {catalogTab === "skills" && (
                  <div className="skill-catalog-toolbar">
                    <div className="skill-catalog-categories">
                      {MARKET_CATEGORIES.map((item) => <button key={item} className={catalogCategory === item ? "active" : ""} type="button" onClick={() => setCatalogCategory(item)}>{item}</button>)}
                    </div>
                    <label className="skill-catalog-search"><Search size={14} /><input value={catalogQuery} onChange={(event) => setCatalogQuery(event.target.value)} placeholder="搜索 Skill" /></label>
                  </div>
                )}
              </header>
              {userSkillsLoading && catalogTab === "mine" ? (
                <div className="skill-catalog-empty"><LoaderCircle className="spinning" size={26} /><strong>正在加载我的 Skill</strong></div>
              ) : catalogSkills.length ? (
                <div className="skill-catalog-grid">
                  {catalogSkills.map((skill) => (
                    <article className="skill-catalog-card" key={skill.id} onClick={() => setDetailSkill(skill)}>
                      <div className={`skill-catalog-cover skill-cover-${skill.line}`}>
                        <img src={LINE_COVERS[skill.line]} alt="" loading="lazy" draggable={false} />
                        <span>{MEDIA_LABELS[skill.mediaType]}</span>
                      </div>
                      <div className="skill-catalog-copy">
                        <h3>{skill.title}</h3>
                        <p>{skill.description}</p>
                        <footer><span>{skill.creator}</span><i aria-hidden="true" /><span><UserRound size={12} />{compactNumber(skill.views)}</span></footer>
                      </div>
                      <div className="skill-catalog-actions">
                        <button type="button" title={favorites.has(skill.id) ? "取消收藏" : "收藏"} aria-label={favorites.has(skill.id) ? "取消收藏" : "收藏"} className={favorites.has(skill.id) ? "active" : ""} onClick={(event) => { event.stopPropagation(); requestFavorite(skill.id); }}><Star size={14} fill={favorites.has(skill.id) ? "currentColor" : "none"} /></button>
                        <button type="button" className="use" onClick={(event) => { event.stopPropagation(); useSkill(skill, false); }}>使用</button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="skill-catalog-empty"><Search size={28} /><strong>没有找到相关 Skill</strong><span>换个分类或关键词试试</span></div>
              )}
            </div>
          </section>
        </div>
      )}

      {detailSkill && (
        <div className="modal-backdrop skill-detail-backdrop" role="presentation" onMouseDown={() => setDetailSkill(null)}>
          <section className="skill-detail-modal" role="dialog" aria-modal="true" aria-label={detailSkill.title} onMouseDown={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" aria-label="关闭" onClick={() => setDetailSkill(null)}><X size={12} /></button>
            <header className="libtv-detail-header">
              <div className="libtv-detail-heading">
                <h2>{detailSkill.title}</h2>
                <div className="libtv-detail-meta">
                  <span className="detail-author-avatar">{detailSkill.creator.slice(0, 1).toUpperCase()}</span>
                  <span>{detailSkill.creator}</span><i aria-hidden="true" />
                  <span>{detailSkill.category}</span><i aria-hidden="true" />
                  <span><UserRound size={13} />{compactNumber(detailSkill.views)}</span><i aria-hidden="true" />
                  <span><Star size={13} />{compactNumber(detailSkill.favorites + (favorites.has(detailSkill.id) ? 1 : 0))}</span>
                </div>
              </div>
              <div className="libtv-detail-actions">
                <button type="button" aria-label="分享" title="分享" onClick={() => { void navigator.clipboard?.writeText(window.location.href); setToast("页面链接已复制"); }}><Share2 size={16} /></button>
                <button className={favorites.has(detailSkill.id) ? "active" : ""} type="button" aria-label={favorites.has(detailSkill.id) ? "取消收藏" : "收藏"} title={favorites.has(detailSkill.id) ? "取消收藏" : "收藏"} onClick={() => requestFavorite(detailSkill.id)}><Star size={16} fill={favorites.has(detailSkill.id) ? "currentColor" : "none"} /></button>
                {customSkillIds.has(detailSkill.id) && <button className="danger" type="button" aria-label="删除" title="删除" onClick={() => { void removeUserSkill(detailSkill).catch((reason) => setToast(reason instanceof Error ? reason.message : "删除失败")); }}><Trash2 size={15} /></button>}
                <button className="primary" type="button" onClick={() => useSkill(detailSkill)}>添加 Skill</button>
              </div>
            </header>
            <div className="libtv-detail-body">
              {detailPreview && failedPreviewSkillId !== detailSkill.id && (
                <section className="libtv-detail-case">
                  <h3>精选案例</h3>
                  <div>
                    {detailPreview.kind === "image" ? (
                      <img src={detailPreview.src} alt={detailPreview.alt} onError={() => setFailedPreviewSkillId(detailSkill.id)} />
                    ) : (
                      <video src={detailPreview.src} poster={detailPreview.poster} controls preload="metadata" onError={() => setFailedPreviewSkillId(detailSkill.id)} />
                    )}
                  </div>
                </section>
              )}
              <section className="libtv-detail-info">
                <h3>简介</h3>
                <dl>
                  <div><dt>介绍</dt><dd>{detailSkill.description}</dd></div>
                  <div><dt>使用场景</dt><dd>{detailSkill.useCases.join("、")}</dd></div>
                  <div><dt>工作流</dt><dd>{detailSkill.steps.join(" → ")}</dd></div>
                  <div><dt>如何使用</dt><dd>{detailSkill.guide}</dd></div>
                  <div><dt>输出内容</dt><dd>{MEDIA_LABELS[detailSkill.mediaType]}</dd></div>
                </dl>
              </section>
              <section className="libtv-detail-source">
                <h3>Skill</h3>
                {detailSkillSourceGroups.length ? (
                  <div className="libtv-source-browser">
                    <div className="skill-source-tabs" role="tablist" aria-label={`${detailSkill.title}系列 Skill`}>
                      {detailSkillSourceGroups.map((group) => (
                        <button
                          className={activeSourceGroup?.id === group.id ? "active" : ""}
                          type="button"
                          role="tab"
                          aria-selected={activeSourceGroup?.id === group.id}
                          title={`${group.path} · ${group.files.length} 个文件`}
                          key={group.id}
                          onClick={() => {
                            setActiveSourceGroupId(group.id);
                            setActiveSourceFileId(group.files[0]?.id ?? "");
                          }}
                        >
                          <FileCode2 size={14} /><span>{group.name}</span>
                        </button>
                      ))}
                    </div>
                    <div className="skill-source-workspace">
                      <aside className="skill-source-files" aria-label={`${activeSourceGroup?.name ?? "Skill"}文件列表`}>
                        <header><span>{activeSourceGroup?.name ?? "Skill"}</span><small>{activeSourceGroup?.files.length ?? 0}</small></header>
                        <div>
                          {activeSourceGroup?.files.map((file) => {
                            const parentPath = file.relativePath.includes("/") ? file.relativePath.slice(0, file.relativePath.lastIndexOf("/")) : "";
                            return (
                              <button className={activeSourceFile?.id === file.id ? "active" : ""} type="button" title={file.path} key={file.id} onClick={() => setActiveSourceFileId(file.id)}>
                                <FileCode2 size={13} /><span><b>{file.name}</b>{parentPath && <small>{parentPath}</small>}</span>
                              </button>
                            );
                          })}
                        </div>
                      </aside>
                      <pre key={activeSourceFile?.id ?? "loading"}><code>{sourceLoading ? "正在读取文件…" : activeSourceText || "请选择一个文件"}</code></pre>
                    </div>
                  </div>
                ) : (
                  <div className="libtv-workflow-preview">{detailSkill.steps.map((step, index) => <span key={step}><b>{index + 1}</b>{step}</span>)}</div>
                )}
              </section>
            </div>
          </section>
        </div>
      )}

      <AuthDialog
        open={authOpen}
        configured={authConfigured}
        onClose={() => setAuthOpen(false)}
        onContinue={async (email, password) => {
          const result = await signInOrSignUpWithEmail({ email, password, emailRedirectTo: window.location.origin });
          if (!result.session) throw new Error("登录服务配置尚未生效，请稍后重试。");
          setToast("登录成功");
          return {};
        }}
      />
      <MembershipDialog
        open={membershipOpen}
        onClose={() => setMembershipOpen(false)}
        onPurchase={(label) => { setMembershipOpen(false); setToast(`已选择${label}，支付服务接入后即可购买`); }}
      />
      <CreateSkillDialog open={createSkillOpen} ownerEmail={authUser?.email ?? ""} onClose={() => setCreateSkillOpen(false)} onCreate={handleCreateSkill} />
      {toast && <div className="home-toast"><Bell size={15} />{toast}</div>}
      <button className="floating-help" type="button" title="帮助中心" onClick={() => setToast("帮助中心正在整理中")}><CircleHelp size={20} /></button>
    </main>
  );
}
