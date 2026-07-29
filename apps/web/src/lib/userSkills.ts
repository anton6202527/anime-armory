import { getSupabaseClient } from "./cloud";
import type { CreationLine } from "../types";

export type UserSkillMediaType = "text" | "image" | "video" | "audio" | "mixed";
export type UserSkillVisibility = "private" | "public";

export interface UserSkillRecord {
  id: string;
  ownerId: string;
  slug: string;
  title: string;
  description: string;
  line: CreationLine;
  category: string;
  mediaType: UserSkillMediaType;
  visibility: UserSkillVisibility;
  guide: string;
  steps: string[];
  useCases: string[];
  definition: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface CreateUserSkillInput {
  slug?: string;
  title: string;
  description?: string;
  line: CreationLine;
  category?: string;
  mediaType?: UserSkillMediaType;
  visibility?: UserSkillVisibility;
  guide?: string;
  steps?: string[];
  useCases?: string[];
  definition?: Record<string, unknown>;
}

export type UpdateUserSkillInput = Partial<Omit<CreateUserSkillInput, "slug">> & {
  slug?: string;
};

export type UserSkillPersistenceErrorCode =
  | "cloud-not-configured"
  | "auth-required"
  | "invalid-input"
  | "operation-failed";

export class UserSkillPersistenceError extends Error {
  readonly code: UserSkillPersistenceErrorCode;

  constructor(code: UserSkillPersistenceErrorCode, message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "UserSkillPersistenceError";
    this.code = code;
  }
}

interface UserSkillRow {
  id: string;
  owner_id: string;
  slug: string;
  title: string;
  description: string;
  creation_line: CreationLine;
  category: string;
  media_type: UserSkillMediaType;
  visibility: UserSkillVisibility;
  guide: string;
  steps: string[] | null;
  use_cases: string[] | null;
  definition: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

const SELECT_COLUMNS = [
  "id",
  "owner_id",
  "slug",
  "title",
  "description",
  "creation_line",
  "category",
  "media_type",
  "visibility",
  "guide",
  "steps",
  "use_cases",
  "definition",
  "created_at",
  "updated_at",
].join(", ");

function fromRow(row: UserSkillRow): UserSkillRecord {
  return {
    id: row.id,
    ownerId: row.owner_id,
    slug: row.slug,
    title: row.title,
    description: row.description,
    line: row.creation_line,
    category: row.category,
    mediaType: row.media_type,
    visibility: row.visibility,
    guide: row.guide,
    steps: row.steps ?? [],
    useCases: row.use_cases ?? [],
    definition: row.definition ?? {},
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function requiredText(value: string, label: string) {
  const normalized = value.trim();
  if (!normalized) {
    throw new UserSkillPersistenceError("invalid-input", `${label}不能为空。`);
  }
  return normalized;
}

function normalizeSlug(slug: string | undefined) {
  const normalized = slug
    ?.trim()
    .replace(/^\/+/, "")
    .replace(/\s+/g, "-")
    .replace(/[^a-zA-Z0-9._-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .toLocaleLowerCase();
  return normalized || `custom-${crypto.randomUUID().slice(0, 12)}`;
}

async function requireAuthenticatedClient() {
  const client = await getSupabaseClient();
  if (!client) {
    throw new UserSkillPersistenceError(
      "cloud-not-configured",
      "尚未配置 Supabase，无法保存用户 Skill。",
    );
  }

  const { data: sessionData, error: sessionError } = await client.auth.getSession();
  if (sessionError) {
    throw new UserSkillPersistenceError("operation-failed", sessionError.message, {
      cause: sessionError,
    });
  }
  if (!sessionData.session) {
    throw new UserSkillPersistenceError("auth-required", "请先登录，再创建或管理自己的 Skill。");
  }

  const { data, error } = await client.auth.getUser();
  if (error) {
    throw new UserSkillPersistenceError("operation-failed", error.message, { cause: error });
  }
  if (!data.user) {
    throw new UserSkillPersistenceError("auth-required", "请先登录，再创建或管理自己的 Skill。");
  }
  return { client, user: data.user };
}

async function requireConfiguredClient() {
  const client = await getSupabaseClient();
  if (!client) {
    throw new UserSkillPersistenceError(
      "cloud-not-configured",
      "尚未配置 Supabase，无法读取公开 Skill。",
    );
  }
  return client;
}

function insertValues(ownerId: string, input: CreateUserSkillInput) {
  return {
    owner_id: ownerId,
    slug: normalizeSlug(input.slug),
    title: requiredText(input.title, "Skill 名称"),
    description: input.description?.trim() ?? "",
    creation_line: input.line,
    category: input.category?.trim() || "通用技能",
    media_type: input.mediaType ?? "mixed",
    visibility: input.visibility ?? "private",
    guide: input.guide?.trim() ?? "",
    steps: input.steps ?? [],
    use_cases: input.useCases ?? [],
    definition: input.definition ?? {},
  };
}

function updateValues(input: UpdateUserSkillInput) {
  return {
    ...(input.slug !== undefined ? { slug: normalizeSlug(input.slug) } : {}),
    ...(input.title !== undefined ? { title: requiredText(input.title, "Skill 名称") } : {}),
    ...(input.description !== undefined ? { description: input.description.trim() } : {}),
    ...(input.line !== undefined ? { creation_line: input.line } : {}),
    ...(input.category !== undefined ? { category: requiredText(input.category, "分类") } : {}),
    ...(input.mediaType !== undefined ? { media_type: input.mediaType } : {}),
    ...(input.visibility !== undefined ? { visibility: input.visibility } : {}),
    ...(input.guide !== undefined ? { guide: input.guide.trim() } : {}),
    ...(input.steps !== undefined ? { steps: input.steps } : {}),
    ...(input.useCases !== undefined ? { use_cases: input.useCases } : {}),
    ...(input.definition !== undefined ? { definition: input.definition } : {}),
  };
}

export async function listUserSkills(): Promise<UserSkillRecord[]> {
  const { client, user } = await requireAuthenticatedClient();
  const { data, error } = await client
    .from("user_skills")
    .select(SELECT_COLUMNS)
    .eq("owner_id", user.id)
    .order("updated_at", { ascending: false });

  if (error) {
    throw new UserSkillPersistenceError("operation-failed", error.message, { cause: error });
  }
  return ((data ?? []) as unknown as UserSkillRow[]).map(fromRow);
}

export async function listPublicUserSkills(): Promise<UserSkillRecord[]> {
  const client = await requireConfiguredClient();
  const { data, error } = await client
    .from("user_skills")
    .select(SELECT_COLUMNS)
    .eq("visibility", "public")
    .order("updated_at", { ascending: false });

  if (error) {
    throw new UserSkillPersistenceError("operation-failed", error.message, { cause: error });
  }
  return ((data ?? []) as unknown as UserSkillRow[]).map(fromRow);
}

export async function createUserSkill(input: CreateUserSkillInput): Promise<UserSkillRecord> {
  const { client, user } = await requireAuthenticatedClient();
  const { data, error } = await client
    .from("user_skills")
    .insert(insertValues(user.id, input))
    .select(SELECT_COLUMNS)
    .single();

  if (error) {
    throw new UserSkillPersistenceError("operation-failed", error.message, { cause: error });
  }
  return fromRow(data as unknown as UserSkillRow);
}

export async function updateUserSkill(
  id: string,
  input: UpdateUserSkillInput,
): Promise<UserSkillRecord> {
  const { client, user } = await requireAuthenticatedClient();
  const skillId = requiredText(id, "Skill ID");
  const values = updateValues(input);
  if (Object.keys(values).length === 0) {
    throw new UserSkillPersistenceError("invalid-input", "没有需要更新的 Skill 字段。");
  }

  const { data, error } = await client
    .from("user_skills")
    .update(values)
    .eq("id", skillId)
    .eq("owner_id", user.id)
    .select(SELECT_COLUMNS)
    .single();

  if (error) {
    throw new UserSkillPersistenceError("operation-failed", error.message, { cause: error });
  }
  return fromRow(data as unknown as UserSkillRow);
}

export async function deleteUserSkill(id: string): Promise<void> {
  const { client, user } = await requireAuthenticatedClient();
  const skillId = requiredText(id, "Skill ID");
  const { error } = await client
    .from("user_skills")
    .delete()
    .eq("id", skillId)
    .eq("owner_id", user.id);

  if (error) {
    throw new UserSkillPersistenceError("operation-failed", error.message, { cause: error });
  }
}
