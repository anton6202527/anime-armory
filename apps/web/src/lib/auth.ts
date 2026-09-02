import { apiJson, isApiError } from "./api";
import {
  normalizeAuthSessionEnvelope,
  type AuthSessionEnvelope,
  type AuthUpstreamState,
} from "./authState";

export type { AuthUpstreamState, AuthUpstreamStatus } from "./authState";

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
  availability: boolean;
  upstream: AuthUpstreamState;
  event: AuthChangeEvent | "UNCONFIGURED" | "UNAVAILABLE";
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

type AuthSessionResponse = AuthSessionEnvelope<AuthSession>;

let lastSnapshot: AuthSnapshot = {
  configured: false,
  availability: false,
  upstream: { available: false, status: "checking" },
  event: "INITIAL_SESSION",
  session: null,
  user: null,
};
const listeners = new Set<(snapshot: AuthSnapshot) => void>();
let refreshInFlight: Promise<AuthSnapshot> | null = null;

function publish(snapshot: AuthSnapshot) {
  lastSnapshot = snapshot;
  for (const listener of listeners) listener(snapshot);
}

function unavailableUpstream(error: unknown): AuthUpstreamState {
  if (!isApiError(error)) {
    return { available: false, status: "backend-unavailable", code: "unknown_error", message: "无法确认登录服务状态" };
  }
  const status = error.code === "auth_not_configured"
    ? "unconfigured"
    : error.code === "auth_upstream_timeout" || error.code === "request_timeout"
      ? "timeout"
      : error.code === "auth_upstream_unhealthy"
        ? "unhealthy"
        : error.code === "network_error"
          ? "backend-unavailable"
          : "unavailable";
  return {
    available: false,
    status,
    code: String(error.code),
    message: error.message,
    ...(error.requestId ? { requestId: error.requestId } : {}),
  };
}

function publishUnavailable(error: unknown): AuthSnapshot {
  const upstream = unavailableUpstream(error);
  const snapshot: AuthSnapshot = {
    configured: upstream.status === "unconfigured" ? false : lastSnapshot.configured,
    availability: false,
    upstream,
    event: upstream.status === "unconfigured" ? "UNCONFIGURED" : "UNAVAILABLE",
    session: null,
    user: null,
  };
  publish(snapshot);
  return snapshot;
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
  try {
    const result = await apiJson<AuthAccessResponse>("/v1/auth/access", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: input.email, password: input.password }),
    });
    if (result.session) {
      publish({
        configured: true,
        availability: true,
        upstream: { available: true, status: "available" },
        event: "SIGNED_IN",
        session: result.session,
        user: result.session.user,
      });
    }
    return result;
  } catch (error) {
    if (isApiError(error) && (
      error.code === "auth_not_configured"
      || error.code === "auth_upstream_unavailable"
      || error.code === "auth_upstream_unhealthy"
      || error.code === "auth_upstream_timeout"
      || error.code === "network_error"
      || error.code === "request_timeout"
    )) {
      publishUnavailable(error);
    }
    throw error;
  }
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
  publish({
    configured: true,
    availability: true,
    upstream: { available: true, status: "available" },
    event: "SIGNED_OUT",
    session: null,
    user: null,
  });
}

export async function getCurrentSession(): Promise<AuthSession | null> {
  return (await refreshAuthState()).session;
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  return (await getCurrentSession())?.user ?? null;
}

export function subscribeToAuthState(listener: (snapshot: AuthSnapshot) => void): () => void {
  listeners.add(listener);
  listener(lastSnapshot);
  void refreshAuthState();
  return () => {
    listeners.delete(listener);
  };
}

export function refreshAuthState(): Promise<AuthSnapshot> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = apiJson<unknown>("/v1/auth/session")
    .then((raw) => {
      const { configured, availability, upstream, session } = normalizeAuthSessionEnvelope<AuthSession>(raw);
      const snapshot: AuthSnapshot = {
        configured,
        availability,
        upstream,
        event: !configured ? "UNCONFIGURED" : availability ? "INITIAL_SESSION" : "UNAVAILABLE",
        session,
        user: session?.user ?? null,
      };
      publish(snapshot);
      return snapshot;
    })
    .catch((error) => publishUnavailable(error))
    .finally(() => { refreshInFlight = null; });
  return refreshInFlight;
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
