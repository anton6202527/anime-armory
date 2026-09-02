import assert from "node:assert/strict";
import test from "node:test";

import { authServicePresentation, normalizeAuthSessionEnvelope } from "../src/lib/authState";

test("configured auth remains unavailable when the upstream probe fails", () => {
  const state = normalizeAuthSessionEnvelope({
    configured: true,
    availability: false,
    upstream: {
      available: false,
      status: "unavailable",
      code: "auth_upstream_unavailable",
      message: "无法连接 Supabase 登录服务",
    },
    session: null,
  });

  assert.equal(state.configured, true);
  assert.equal(state.availability, false);
  assert.equal(state.upstream.status, "unavailable");
  assert.equal(state.upstream.code, "auth_upstream_unavailable");
});

test("availability is never inferred from configured alone", () => {
  const state = normalizeAuthSessionEnvelope({ configured: true, session: null });

  assert.equal(state.configured, true);
  assert.equal(state.availability, false);
  assert.equal(state.upstream.status, "unavailable");
});

test("untrusted upstream fields are normalized without losing diagnostics", () => {
  const state = normalizeAuthSessionEnvelope({
    configured: false,
    availability: false,
    upstream: {
      status: "not-a-real-status",
      code: "auth_not_configured",
      message: "登录服务尚未配置",
      requestId: "e9f21895-1145-4bcb-b958-880999107fc3",
    },
  });

  assert.equal(state.upstream.status, "unconfigured");
  assert.equal(state.upstream.code, "auth_not_configured");
  assert.equal(state.upstream.requestId, "e9f21895-1145-4bcb-b958-880999107fc3");
});

test("explicit backend-unavailable status wins when configured is still unknown", () => {
  const presentation = authServicePresentation(false, {
    available: false,
    status: "backend-unavailable",
    message: "无法连接 LabuTV 后端服务",
  });

  assert.equal(presentation.title, "无法连接 LabuTV 后端");
  assert.equal(presentation.detail, "无法连接 LabuTV 后端服务");
});
