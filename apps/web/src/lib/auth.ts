import { apiJson } from "./api";

export interface AuthUser {
  id: string;
  email?: string;
  user_metadata?: Record<string, unknown>;
}

export interface AuthSession {
  user: AuthUser;
  accessToken?: string;
}

export type AuthChangeEvent = "INITIAL_SESSION" | "SIGNED_IN" | "SIGNED_OUT";

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
  user: AuthUser;
  session: AuthSession | null;
  confirmationRequired: boolean;
}

export interface EmailAccessResult {
  action: "signed-in" | "signed-up";
  session: AuthSession | null;
  confirmationRequired: boolean;
}

export interface AuthSnapshot {
  configured: boolean;
  event: AuthChangeEvent | "UNCONFIGURED";
  session: AuthSession | null;
  user: AuthUser | null;
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

function unavailable(message = "该云端用户数据接口尚未迁移到后端 REST API。"):
  never {
  throw new AuthPersistenceError(
    "cloud-not-configured",
    message,
  );
}

interface AuthAccessResponse {
  action: "signed-in" | "signed-up";
  session: AuthSession | null;
  confirmationRequired: boolean;
}

interface AuthSessionResponse {
  configured: boolean;
  session: AuthSession | null;
}

let lastSnapshot: AuthSnapshot = {
  configured: true,
  event: "INITIAL_SESSION",
  session: null,
  user: null,
};
const listeners = new Set<(snapshot: AuthSnapshot) => void>();

function publish(snapshot: AuthSnapshot) {
  lastSnapshot = snapshot;
  for (const listener of listeners) listener(snapshot);
}

function normalizeInput(inputOrEmail: EmailSignUpInput | string, password?: string): EmailSignUpInput {
  const input = typeof inputOrEmail === "string"
    ? { email: inputOrEmail, password: password ?? "" }
    : inputOrEmail;
  const email = input.email.trim().toLocaleLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new AuthPersistenceError("invalid-email", "请输入有效的邮箱地址。");
  }
  if (input.password.length < 6) {
    throw new AuthPersistenceError("invalid-password", "密码至少需要 6 个字符。");
  }
  return { ...input, email };
}

async function access(input: EmailSignUpInput): Promise<EmailAccessResult> {
  const result = await apiJson<AuthAccessResponse>("/v1/auth/access", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: input.email, password: input.password }),
  });
  if (result.session) {
    publish({ configured: true, event: "SIGNED_IN", session: result.session, user: result.session.user });
  }
  return result;
}

export function signUpWithEmail(email: string, password: string): Promise<EmailSignUpResult>;
export function signUpWithEmail(input: EmailSignUpInput): Promise<EmailSignUpResult>;
export async function signUpWithEmail(
  inputOrEmail: EmailSignUpInput | string,
  password?: string,
): Promise<EmailSignUpResult> {
  const result = await access(normalizeInput(inputOrEmail, password));
  const user = result.session?.user;
  if (!user) {
    throw new AuthPersistenceError("auth-operation-failed", "账号已创建，请先完成邮箱验证后再登录。");
  }
  return { user, session: result.session, confirmationRequired: result.confirmationRequired };
}

export function signInWithEmail(email: string, password: string): Promise<AuthSession>;
export function signInWithEmail(input: EmailCredentials): Promise<AuthSession>;
export async function signInWithEmail(
  inputOrEmail: EmailCredentials | string,
  password?: string,
): Promise<AuthSession> {
  const result = await access(normalizeInput(inputOrEmail, password));
  if (!result.session) throw new AuthPersistenceError("auth-operation-failed", "请先完成邮箱验证后再登录。");
  return result.session;
}

export async function signInOrSignUpWithEmail(input: EmailSignUpInput): Promise<EmailAccessResult> {
  return access(normalizeInput(input));
}

export async function signOut(): Promise<void> {
  await apiJson<{ signedOut: true }>("/v1/auth/sign-out", { method: "POST" });
  publish({ configured: true, event: "SIGNED_OUT", session: null, user: null });
}

export async function getCurrentSession(): Promise<AuthSession | null> {
  const result = await apiJson<AuthSessionResponse>("/v1/auth/session");
  return result.session;
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  return (await getCurrentSession())?.user ?? null;
}

export function subscribeToAuthState(listener: (snapshot: AuthSnapshot) => void): () => void {
  let disposed = false;
  listeners.add(listener);
  listener(lastSnapshot);
  void apiJson<AuthSessionResponse>("/v1/auth/session")
    .then(({ configured, session }) => {
      if (!disposed) publish({
        configured,
        event: configured ? "INITIAL_SESSION" : "UNCONFIGURED",
        session,
        user: session?.user ?? null,
      });
    })
    .catch(() => {
      if (!disposed) publish({ configured: false, event: "UNCONFIGURED", session: null, user: null });
    });
  return () => {
    disposed = true;
    listeners.delete(listener);
  };
}

export function subscribeAuth(listener: (user: AuthUser | null) => void): () => void {
  return subscribeToAuthState(({ user }) => listener(user));
}

export async function getMyProfile(): Promise<UserProfile | null> {
  return null;
}

export async function updateMyProfile(
  _patch: Pick<Partial<UserProfile>, "displayName" | "avatarUrl">,
): Promise<UserProfile> {
  return unavailable();
}

export async function getMySettings(): Promise<UserSettings | null> {
  return null;
}

export async function updateMySettings(
  _patch: { theme?: ThemePreference; preferences?: Record<string, unknown> },
): Promise<UserSettings> {
  return unavailable();
}
