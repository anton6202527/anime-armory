import { ArrowRight, Eye, EyeOff, LoaderCircle, LockKeyhole, Mail, RefreshCw, ShieldCheck, X } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { isApiError } from "../../lib/api";
import type { AuthUpstreamState } from "../../lib/auth";
import { authServicePresentation } from "../../lib/authState";

interface AuthDialogProps {
  open: boolean;
  configured: boolean;
  availability: boolean;
  upstream: AuthUpstreamState;
  onClose: () => void;
  onContinue: (email: string, password: string) => Promise<{ message?: string }>;
  onRetry: () => Promise<unknown>;
}

interface AuthFeedback {
  message: string;
  code?: string;
  requestId?: string;
}

function feedback(reason: unknown): AuthFeedback {
  if (!isApiError(reason)) return { message: reason instanceof Error ? reason.message : String(reason) };
  return {
    message: reason.message,
    code: String(reason.code),
    ...(reason.requestId ? { requestId: reason.requestId } : {}),
  };
}

export function AuthDialog({ open, configured, availability, upstream, onClose, onContinue, onRetry }: AuthDialogProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState<AuthFeedback | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!open) return;
    setError(null);
    setMessage("");
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape" && !submitting) onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open, submitting]);

  if (!open) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage("");
    const cleanEmail = email.trim().toLocaleLowerCase();
    if (!cleanEmail || !cleanEmail.includes("@")) {
      setError({ message: "请输入有效的邮箱地址" });
      return;
    }
    if (password.length < 6) {
      setError({ message: "密码至少需要 6 位" });
      return;
    }
    setSubmitting(true);
    try {
      const result = await onContinue(cleanEmail, password);
      if (result.message) setMessage(result.message);
      else onClose();
    } catch (reason) {
      setError(feedback(reason));
    } finally {
      setSubmitting(false);
    }
  }

  async function retry() {
    setRetrying(true);
    setError(null);
    try {
      await onRetry();
    } catch (reason) {
      setError(feedback(reason));
    } finally {
      setRetrying(false);
    }
  }

  const service = authServicePresentation(configured, upstream);
  const serviceUnavailable = !availability;
  const diagnosticCode = upstream.code;
  const diagnosticRequestId = upstream.requestId;

  return (
    <div className="account-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !submitting) onClose(); }}>
      <section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-dialog-title">
        <button className="dialog-close" type="button" onClick={onClose} aria-label="关闭登录窗口"><X size={18} /></button>
        <div className="auth-dialog-brand"><span><ShieldCheck size={21} /></span><b>LabuTV 账号</b></div>
        <h2 id="auth-dialog-title">登录</h2>
        <p>输入邮箱和密码，首次登录会自动创建账号。</p>

        {serviceUnavailable ? (
          <div className="auth-config-note" role={upstream.status === "checking" ? "status" : "alert"}>
            {retrying || upstream.status === "checking" ? <LoaderCircle className="spinning" size={18} /> : <LockKeyhole size={18} />}
            <span>
              <b>{service.title}</b>
              <small>{service.detail}</small>
              {(diagnosticCode || diagnosticRequestId) && (
                <small className="auth-diagnostics">
                  {diagnosticCode && <code>{diagnosticCode}</code>}
                  {diagnosticRequestId && <code>请求 {diagnosticRequestId}</code>}
                </small>
              )}
              {upstream.status !== "checking" && (
                <button className="auth-retry" type="button" disabled={retrying} onClick={() => void retry()}>
                  {retrying ? <LoaderCircle className="spinning" size={14} /> : <RefreshCw size={14} />}重试连接
                </button>
              )}
            </span>
          </div>
        ) : (
          <form onSubmit={(event) => void submit(event)}>
            <label><span>邮箱</span><div><Mail size={16} /><input autoFocus type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" autoComplete="email" /></div></label>
            <label><span>密码</span><div><LockKeyhole size={16} /><input type={passwordVisible ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="至少 6 位" autoComplete="current-password" /><button type="button" onClick={() => setPasswordVisible((visible) => !visible)} aria-label={passwordVisible ? "隐藏密码" : "显示密码"}>{passwordVisible ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label>
            {error && (
              <div className="auth-feedback error" role="alert">
                <span>{error.message}</span>
                {(error.code || error.requestId) && (
                  <small className="auth-diagnostics">
                    {error.code && <code>{error.code}</code>}
                    {error.requestId && <code>请求 {error.requestId}</code>}
                  </small>
                )}
              </div>
            )}
            {message && <div className="auth-feedback success" role="status">{message}</div>}
            <button className="auth-submit" type="submit" disabled={submitting}>{submitting ? <LoaderCircle className="spinning" size={17} /> : <>登录<ArrowRight size={16} /></>}</button>
          </form>
        )}
        <small className="auth-policy">继续即表示你同意仅将邮箱用于账户、作品与 Skill 同步。</small>
      </section>
    </div>
  );
}
