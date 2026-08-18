import type { CreationLine } from "../types";

/**
 * User Skill persistence is disabled until the backend owns its REST
 * resources and authorization checks. No provider SDK is allowed in Web.
 */

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

function unavailable(): never {
  throw new UserSkillPersistenceError(
    "cloud-not-configured",
    "个人 Skill 正在迁移到后端 REST API，本地模式暂不可用。",
  );
}

export async function listUserSkills(): Promise<UserSkillRecord[]> {
  return [];
}

export async function listPublicUserSkills(): Promise<UserSkillRecord[]> {
  return [];
}

export async function createUserSkill(_input: CreateUserSkillInput): Promise<UserSkillRecord> {
  return unavailable();
}

export async function updateUserSkill(
  _id: string,
  _input: UpdateUserSkillInput,
): Promise<UserSkillRecord> {
  return unavailable();
}

export async function deleteUserSkill(_id: string): Promise<void> {
  return unavailable();
}
