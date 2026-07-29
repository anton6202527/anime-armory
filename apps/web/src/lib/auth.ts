import type { AuthChangeEvent, Session, User } from "@supabase/supabase-js";
import { getSupabaseClient } from "./cloud";

export type AuthUser = User;

export type AuthPersistenceErrorCode =
  | "cloud-not-configured"
  | "auth-required"
  | "invalid-email"
  | "invalid-password"
  | "auth-operation-failed"
  | "profile-operation-failed"
  | "settings-operation-failed";

export class AuthPersistenceError extends Error {
  readonly code: AuthPersistenceErrorCode;

  constructor(code: AuthPersistenceErrorCode, message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "AuthPersistenceError";
    this.code = code;
  }
}

export interface EmailCredentials {
  email: string;
  password: string;
}

export interface EmailSignUpInput extends EmailCredentials {
  displayName?: string;
  emailRedirectTo?: string;
}

export interface EmailSignUpResult {
  user: User;
  session: Session | null;
  confirmationRequired: boolean;
}

export interface EmailAccessResult {
  action: "signed-in" | "signed-up";
  session: Session | null;
  confirmationRequired: boolean;
}

export interface AuthSnapshot {
  configured: boolean;
  event: AuthChangeEvent | "UNCONFIGURED";
  session: Session | null;
  user: User | null;
}

export type ThemePreference = "dark" | "light" | "system";

export interface UserProfile {
  ownerId: string;
  displayName: string | null;
  avatarUrl: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface UserSettings {
  ownerId: string;
  theme: ThemePreference;
  preferences: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

interface UserProfileRow {
  owner_id: string;
  display_name: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

interface UserSettingsRow {
  owner_id: string;
  theme: ThemePreference;
  preferences: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

function normalizeEmail(email: string) {
  const normalized = email.trim().toLocaleLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized)) {
    throw new AuthPersistenceError("invalid-email", "请输入有效的邮箱地址。");
  }
  return normalized;
}

function validatePassword(password: string) {
  if (password.length < 6) {
    throw new AuthPersistenceError("invalid-password", "密码至少需要 6 个字符。");
  }
  return password;
}

async function requireClient() {
  const client = await getSupabaseClient();
  if (!client) {
    throw new AuthPersistenceError(
      "cloud-not-configured",
      "尚未配置 Supabase，邮箱登录和云端用户数据暂不可用。",
    );
  }
  return client;
}

async function requireAuthenticatedClient() {
  const client = await requireClient();
  const { data: sessionData, error: sessionError } = await client.auth.getSession();
  if (sessionError) {
    throw new AuthPersistenceError("auth-operation-failed", sessionError.message, {
      cause: sessionError,
    });
  }
  if (!sessionData.session) {
    throw new AuthPersistenceError("auth-required", "请先使用邮箱登录。");
  }

  const { data, error } = await client.auth.getUser();
  if (error) {
    throw new AuthPersistenceError("auth-operation-failed", error.message, { cause: error });
  }
  if (!data.user) {
    throw new AuthPersistenceError("auth-required", "请先使用邮箱登录。");
  }
  return { client, user: data.user };
}

function profileFromRow(row: UserProfileRow): UserProfile {
  return {
    ownerId: row.owner_id,
    displayName: row.display_name,
    avatarUrl: row.avatar_url,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function settingsFromRow(row: UserSettingsRow): UserSettings {
  return {
    ownerId: row.owner_id,
    theme: row.theme,
    preferences: row.preferences ?? {},
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export function signUpWithEmail(email: string, password: string): Promise<EmailSignUpResult>;
export function signUpWithEmail(input: EmailSignUpInput): Promise<EmailSignUpResult>;
export async function signUpWithEmail(
  inputOrEmail: EmailSignUpInput | string,
  password?: string,
): Promise<EmailSignUpResult> {
  const input = typeof inputOrEmail === "string"
    ? { email: inputOrEmail, password: password ?? "" }
    : inputOrEmail;
  const client = await requireClient();
  const displayName = input.displayName?.trim();
  const { data, error } = await client.auth.signUp({
    email: normalizeEmail(input.email),
    password: validatePassword(input.password),
    options: {
      ...(displayName ? { data: { display_name: displayName } } : {}),
      ...(input.emailRedirectTo ? { emailRedirectTo: input.emailRedirectTo } : {}),
    },
  });

  if (error) {
    throw new AuthPersistenceError("auth-operation-failed", error.message, { cause: error });
  }
  if (!data.user) {
    throw new AuthPersistenceError("auth-operation-failed", "注册成功，但没有返回用户信息。");
  }

  return {
    user: data.user,
    session: data.session,
    confirmationRequired: data.session === null,
  };
}

export function signInWithEmail(email: string, password: string): Promise<Session>;
export function signInWithEmail(input: EmailCredentials): Promise<Session>;
export async function signInWithEmail(
  inputOrEmail: EmailCredentials | string,
  password?: string,
): Promise<Session> {
  const input = typeof inputOrEmail === "string"
    ? { email: inputOrEmail, password: password ?? "" }
    : inputOrEmail;
  const client = await requireClient();
  const { data, error } = await client.auth.signInWithPassword({
    email: normalizeEmail(input.email),
    password: validatePassword(input.password),
  });

  if (error) {
    throw new AuthPersistenceError("auth-operation-failed", error.message, { cause: error });
  }
  if (!data.session) {
    throw new AuthPersistenceError("auth-operation-failed", "登录成功，但没有返回有效会话。");
  }
  return data.session;
}

/**
 * A single email entry point for the public Web UI. Existing accounts sign in;
 * an unknown email is registered automatically. We only fall back to sign-up
 * for Supabase's invalid-credentials response so network, rate-limit and
 * unconfirmed-email errors never create an account by accident.
 */
export async function signInOrSignUpWithEmail(input: EmailSignUpInput): Promise<EmailAccessResult> {
  const client = await requireClient();
  const email = normalizeEmail(input.email);
  const password = validatePassword(input.password);
  const { data: signInData, error: signInError } = await client.auth.signInWithPassword({ email, password });

  if (!signInError && signInData.session) {
    return { action: "signed-in", session: signInData.session, confirmationRequired: false };
  }

  const signInCode = signInError?.code ?? "";
  const mayBeNewAccount = signInCode === "invalid_credentials"
    || /invalid login credentials/i.test(signInError?.message ?? "");
  if (!mayBeNewAccount) {
    throw new AuthPersistenceError(
      "auth-operation-failed",
      signInError?.message ?? "登录失败，请稍后重试。",
      signInError ? { cause: signInError } : undefined,
    );
  }

  const displayName = input.displayName?.trim();
  const { data: signUpData, error: signUpError } = await client.auth.signUp({
    email,
    password,
    options: {
      ...(displayName ? { data: { display_name: displayName } } : {}),
      ...(input.emailRedirectTo ? { emailRedirectTo: input.emailRedirectTo } : {}),
    },
  });

  if (signUpError) {
    const accountExists = signUpError.code === "user_already_exists"
      || /already (?:been )?registered|user already exists/i.test(signUpError.message);
    throw new AuthPersistenceError(
      "auth-operation-failed",
      accountExists ? "该邮箱已注册，请检查密码后重试。" : signUpError.message,
      { cause: signUpError },
    );
  }
  if (!signUpData.user) {
    throw new AuthPersistenceError("auth-operation-failed", "账号创建成功，但没有返回用户信息。");
  }

  // With email enumeration protection enabled, Supabase may return an
  // obfuscated user with no identities for an already-registered address.
  if (!signUpData.session && (signUpData.user.identities?.length ?? 0) === 0) {
    throw new AuthPersistenceError("auth-operation-failed", "该邮箱已注册，请检查密码后重试。");
  }

  return {
    action: "signed-up",
    session: signUpData.session,
    confirmationRequired: signUpData.session === null,
  };
}

export async function signOut(): Promise<void> {
  const client = await requireClient();
  const { error } = await client.auth.signOut();
  if (error) {
    throw new AuthPersistenceError("auth-operation-failed", error.message, { cause: error });
  }
}

export async function getCurrentSession(): Promise<Session | null> {
  const client = await getSupabaseClient();
  if (!client) return null;
  const { data, error } = await client.auth.getSession();
  if (error) {
    throw new AuthPersistenceError("auth-operation-failed", error.message, { cause: error });
  }
  return data.session;
}

export async function getCurrentUser(): Promise<User | null> {
  const client = await getSupabaseClient();
  if (!client) return null;
  const { data: sessionData, error: sessionError } = await client.auth.getSession();
  if (sessionError) {
    throw new AuthPersistenceError("auth-operation-failed", sessionError.message, {
      cause: sessionError,
    });
  }
  if (!sessionData.session) return null;

  const { data, error } = await client.auth.getUser();
  if (error) {
    throw new AuthPersistenceError("auth-operation-failed", error.message, { cause: error });
  }
  return data.user;
}

/**
 * Subscribe to Supabase auth changes. The returned cleanup function is safe to
 * call before the asynchronous client has finished loading.
 */
export function subscribeToAuthState(listener: (snapshot: AuthSnapshot) => void): () => void {
  let disposed = false;
  let unsubscribe: (() => void) | undefined;

  void getSupabaseClient().then((client) => {
    if (disposed) return;
    if (!client) {
      listener({ configured: false, event: "UNCONFIGURED", session: null, user: null });
      return;
    }

    const { data } = client.auth.onAuthStateChange((event, session) => {
      if (!disposed) {
        listener({ configured: true, event, session, user: session?.user ?? null });
      }
    });
    unsubscribe = () => data.subscription.unsubscribe();
  });

  return () => {
    disposed = true;
    unsubscribe?.();
  };
}

/** Compact UI-facing auth subscription. */
export function subscribeAuth(listener: (user: AuthUser | null) => void): () => void {
  return subscribeToAuthState(({ user }) => listener(user));
}

export async function getMyProfile(): Promise<UserProfile | null> {
  const { client, user } = await requireAuthenticatedClient();
  const { data, error } = await client
    .from("user_profiles")
    .select("owner_id, display_name, avatar_url, created_at, updated_at")
    .eq("owner_id", user.id)
    .maybeSingle();

  if (error) {
    throw new AuthPersistenceError("profile-operation-failed", error.message, { cause: error });
  }
  return data ? profileFromRow(data as UserProfileRow) : null;
}

export async function updateMyProfile(
  patch: Pick<Partial<UserProfile>, "displayName" | "avatarUrl">,
): Promise<UserProfile> {
  const { client, user } = await requireAuthenticatedClient();
  const values = {
    owner_id: user.id,
    ...(patch.displayName !== undefined ? { display_name: patch.displayName?.trim() || null } : {}),
    ...(patch.avatarUrl !== undefined ? { avatar_url: patch.avatarUrl?.trim() || null } : {}),
  };
  const { data, error } = await client
    .from("user_profiles")
    .upsert(values, { onConflict: "owner_id" })
    .select("owner_id, display_name, avatar_url, created_at, updated_at")
    .single();

  if (error) {
    throw new AuthPersistenceError("profile-operation-failed", error.message, { cause: error });
  }
  return profileFromRow(data as UserProfileRow);
}

export async function getMySettings(): Promise<UserSettings | null> {
  const { client, user } = await requireAuthenticatedClient();
  const { data, error } = await client
    .from("user_settings")
    .select("owner_id, theme, preferences, created_at, updated_at")
    .eq("owner_id", user.id)
    .maybeSingle();

  if (error) {
    throw new AuthPersistenceError("settings-operation-failed", error.message, { cause: error });
  }
  return data ? settingsFromRow(data as UserSettingsRow) : null;
}

export async function updateMySettings(
  patch: { theme?: ThemePreference; preferences?: Record<string, unknown> },
): Promise<UserSettings> {
  const { client, user } = await requireAuthenticatedClient();
  const values = {
    owner_id: user.id,
    ...(patch.theme !== undefined ? { theme: patch.theme } : {}),
    ...(patch.preferences !== undefined ? { preferences: patch.preferences } : {}),
  };
  const { data, error } = await client
    .from("user_settings")
    .upsert(values, { onConflict: "owner_id" })
    .select("owner_id, theme, preferences, created_at, updated_at")
    .single();

  if (error) {
    throw new AuthPersistenceError("settings-operation-failed", error.message, { cause: error });
  }
  return settingsFromRow(data as UserSettingsRow);
}
