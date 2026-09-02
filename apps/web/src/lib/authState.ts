export type AuthUpstreamStatus =
  | "checking"
  | "available"
  | "unconfigured"
  | "unhealthy"
  | "timeout"
  | "unavailable"
  | "backend-unavailable";

export interface AuthUpstreamState {
  available: boolean;
  status: AuthUpstreamStatus;
  code?: string;
  message?: string;
  requestId?: string;
}

export interface AuthSessionEnvelope<TSession> {
  configured: boolean;
  availability: boolean;
  upstream: AuthUpstreamState;
  session: TSession | null;
}

export interface AuthServicePresentation {
  title: string;
  detail: string;
}

/** UI copy is derived from the explicit probe result before configuration. */
export function authServicePresentation(
  configured: boolean,
  upstream: Partial<AuthUpstreamState>,
): AuthServicePresentation {
  switch (upstream.status) {
    case "checking":
      return { title: "正在检查登录服务", detail: "正在向 LabuTV 后端确认账号服务状态。" };
    case "backend-unavailable":
      return { title: "无法连接 LabuTV 后端", detail: upstream.message || "请确认本地后端仍在运行，然后重试连接。" };
    case "timeout":
      return { title: "登录服务响应超时", detail: upstream.message || "请检查 Supabase 项目状态与网络连接后重试。" };
    case "unhealthy":
      return { title: "登录服务状态异常", detail: upstream.message || "请检查 Supabase 项目状态与 Publishable Key。" };
    case "unavailable":
      return { title: "登录服务暂时不可用", detail: upstream.message || "请检查 Supabase 项目是否暂停或删除，并确认本机网络可用。" };
    case "unconfigured":
      return { title: "登录服务尚未配置", detail: upstream.message || "请在后端配置 Supabase URL 与 Publishable Key，重启服务后再试。" };
    case "available":
      return { title: "登录服务可用", detail: "可以使用邮箱和密码登录。" };
    default:
      return configured
        ? { title: "登录服务暂时不可用", detail: upstream.message || "请稍后重试连接。" }
        : { title: "登录服务尚未配置", detail: upstream.message || "请在后端完成账号服务配置后重试。" };
  }
}

function record(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function upstreamStatus(value: unknown): AuthUpstreamStatus | null {
  return value === "available"
    || value === "unconfigured"
    || value === "unhealthy"
    || value === "timeout"
    || value === "unavailable"
    ? value
    : null;
}

/**
 * Treat the BFF session envelope as untrusted input. In particular, never
 * infer availability from `configured`: a configured but deleted/paused
 * Supabase project must keep the login form disabled.
 */
export function normalizeAuthSessionEnvelope<TSession>(value: unknown): AuthSessionEnvelope<TSession> {
  const payload = record(value);
  const configured = payload?.configured === true;
  const availability = payload?.availability === true;
  const rawUpstream = record(payload?.upstream);
  const status = upstreamStatus(rawUpstream?.status)
    ?? (availability ? "available" : configured ? "unavailable" : "unconfigured");
  const code = typeof rawUpstream?.code === "string" ? rawUpstream.code : undefined;
  const message = typeof rawUpstream?.message === "string" ? rawUpstream.message : undefined;
  const requestId = typeof rawUpstream?.requestId === "string" ? rawUpstream.requestId : undefined;

  return {
    configured,
    availability,
    upstream: {
      available: availability,
      status,
      ...(code ? { code } : {}),
      ...(message ? { message } : {}),
      ...(requestId ? { requestId } : {}),
    },
    session: (payload?.session ?? null) as TSession | null,
  };
}
