# Backend

LabuTV 的 Web 后端是一个独立的 Node.js + TypeScript REST 服务。Web 的 AI / Skill 路径只调用 `/api/v1`；模型密钥、cliproxy 调用、仓库 skill 源文件解析和 skill 执行都留在服务端。

Supabase migrations 与现有 `assets` Edge Function 仍位于 `supabase/`。Web 的旧 Browser client 已停用；邮箱登录由本服务代理到 Supabase Auth，并使用 HttpOnly Cookie 管理会话。云同步相关能力仍需逐项迁入 BFF。

## 本地启动

要求 Node.js 20+，并先确保 `cliproxyapi` 正在本机监听。Homebrew 安装的服务可这样检查或启动：

```bash
brew services list | rg cliproxyapi
brew services start cliproxyapi
curl -i http://127.0.0.1:8317/v1/models
```

最后一个未带鉴权的探针通常返回 `401`，这仍说明 HTTP 服务已启动。后端优先读取进程环境的 `CLI_PROXY_API_URL` / `CLI_PROXY_API_KEY`；macOS 本地默认地址缺少环境 key 时，会安全读取 `/opt/homebrew/etc/cliproxyapi.conf` 的第一枚 `api-keys` 值。密钥不会进入响应或日志，也不要配置任何 `VITE_*` 模型密钥。

从仓库根启动：

```bash
npm run dev --workspace @anime-armory/backend
# 或
npm run dev:backend
```

服务默认只绑定 `127.0.0.1:43118`。检查：

```bash
curl http://127.0.0.1:43118/api/v1/health/live
curl http://127.0.0.1:43118/api/v1/health/ready
curl http://127.0.0.1:43118/api/v1/ai/models
```

复制 [`.env.example`](.env.example) 为 `.env.local` 后填写本机配置；启动入口会自动读取 `.env.local`，该文件和 `.runtime/` 上传区都被 Git 忽略。邮箱登录需要 `SUPABASE_URL` 与 `SUPABASE_PUBLISHABLE_KEY`。远端 cliproxy 地址必须使用 HTTPS，本地 HTTP 只接受 loopback host。CORS 只允许 `BACKEND_ALLOWED_ORIGINS` 明确列出的本地网页 Origin。

## REST API

- `GET /api/v1/health/live`：进程存活检查，不访问上游。
- `GET /api/v1/health/ready`：探测 cliproxy 与 GPT 模型目录；失败返回 `degraded`。
- `GET /api/v1/auth/session`：读取或刷新 HttpOnly Cookie 中的 Supabase 会话。
- `POST /api/v1/auth/access`：邮箱密码登录；账号不存在时自动注册。
- `POST /api/v1/auth/sign-out`：注销上游会话并清除本地认证 Cookie。
- `GET /api/v1/ai/models`：仅返回 cliproxy 暴露的 GPT 文本/图片模型。
- `POST /api/v1/ai/generations`：同步文本或图片生成。文本优先调用 `/v1/responses`，仅在端点明确不支持时回退 `/v1/chat/completions`；图片调用 `/v1/images/generations` 或 `/v1/images/edits`。
- `GET /api/v1/skills`、`GET /api/v1/skills/:id`：服务端 skill registry。
- `GET /api/v1/skills/:id/sources`、`GET /api/v1/skills/:id/source?path=...`：受扩展名、大小与路径 containment 约束的文本源读取。
- `PUT /api/v1/works/:workId/files/:fileId`：UUID 标识的有限大小上传；响应不暴露文件系统路径。
- `POST /api/v1/skill-runs`：用明确 `skillId` 创建内存异步任务。仓库 skill 始终重新读取真实 `SKILL.md`；`user:*` 必须携带完整 `skillDefinition`。
- `GET /api/v1/skill-runs/:id`、`DELETE /api/v1/skill-runs/:id`：读取或取消任务。

所有成功响应使用资源 envelope，例如 `{ "models": [...] }`、`{ "generation": ... }`、`{ "run": ... }`。错误统一为：

```json
{
  "error": {
    "code": "invalid_json",
    "message": "请求 JSON 无效",
    "requestId": "..."
  }
}
```

skill run 当前用内存队列并通过 cliproxy GPT 文本模型返回 text artifact；进程重启后任务不会保留。后续接入持久 job worker 时，REST 契约可保持不变。

## 画布产物语义

后端任务的 `succeeded` 只表示本次 runner 或 provider 正常产出机器结果，不等于当前像素已被真人接受，也不等于最终成品完成。画布生产合同由正式 skill ID `app-script-workbench`、`app-character-turnaround`、`app-first-frame-video` 和 `app-audio-video` 定义；旧 ID 仅供 legacy migration 读取，新任务必须使用正式名称。

生产工作台的目标合同以每个 episode/workflow 实例一个生产状态、每个权威对象一个 canonical 内容 SHA-256、每个交付单元一个完成定义为准。当前内存队列后端尚不持久化逐图/最终回执，也不负责把 Web 工作台推进到 complete；它只能返回机器产物，后续接入时最多写入绑定当前真实字节的 `machine_complete` 证据。逐图验收必须由具名真人查看当前像素，以带时区回执绑定当前 artifact 精确 SHA-256，最终母版另需一份显式真人最终验收；服务端不得合成或代签这些回执。

## 验证

AI provider 在测试中注入 fake，不会真实调用或消耗模型：

```bash
npm run test --workspace @anime-armory/backend
npm run typecheck --workspace @anime-armory/backend
```
