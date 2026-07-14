# 云端架构：Supabase + Cloudflare R2

## 当前决策

开发期采用“本地优先、云能力可选”的结构：

```text
Electron（当前）/ Web（以后）
        │ Supabase 登录令牌
        ▼
Supabase Auth + Postgres + Edge Function
        │ 临时签名 URL（短时有效）
        ▼
Cloudflare R2 私有桶
```

- Git 只保存源码、工作流和小型样例，不保存视频、音频、图片包、模型或构建产物。
- Supabase 保存账号、项目权限、资产索引、任务状态；不保存大型二进制内容。
- R2 桶保持私有。客户端登录后向 `assets` Edge Function 申请临时上传/下载 URL。
- 数据库不保存永久 CDN URL，只保存 `provider + bucket + key + etag/version`。以后切换腾讯云 COS 时，客户端协议不需要改变。
- 现有 Electron 本地工作流保持默认行为；没有云配置、没有登录时仍可离线使用。
- Electron 正式包通过 main/preload 的受限 IPC transport 发起云请求；renderer 不直接联网，也不为 `file://` 的 `null` Origin 放宽 CSP/CORS。
- Web 端本阶段只保留 `apps/web` 工作区边界，不创建页面；后续复用 `packages/contracts` 和 `packages/cloud-client`。

## 代码边界

| 目录 | 职责 |
| --- | --- |
| `apps/desktop` | 当前 Electron 客户端；保持本地优先，云能力按登录状态启用 |
| `apps/backend` | Supabase 后端应用工作区；包含数据库迁移、RLS 与 Edge Functions |
| `apps/web` | 未来 Web 客户端的空工作区；当前不实现页面或运行时 |
| `packages/contracts` | 跨桌面端、Web、Edge Function 的资产 API 契约和输入校验 |
| `packages/object-store` | 对象存储接口及 R2 实现；未来增加 COS 实现 |
| `packages/data-access` | Supabase 资产元数据仓储 |
| `packages/cloud-client` | 登录态客户端、单文件/分片上传、下载授权 |
| `apps/backend/supabase/migrations` | 可审计、可迁移的 Postgres 表结构与 RLS 策略 |
| `apps/backend/supabase/functions/assets` | 私有资产签名、权限校验、上传完成校验 |
| `infrastructure/r2` | R2 CORS 配置样例 |

## 数据模型

- `accounts`：应用内部稳定账号 ID。
- `account_identities`：把 Supabase Auth 用户映射到内部账号；迁往腾讯云时可增加新的身份提供方而不改业务外键。
- `projects` / `project_members`：项目和 `owner/editor/viewer` 权限。
- `assets`：对象存储引用、文件元数据和状态。
- `asset_uploads`：单文件或 multipart 上传会话。
- `jobs`：以后后端任务队列/执行状态的基础表，不承载大型产物。

`assets` 和 `asset_uploads` 不允许普通客户端直接写入。Edge Function 先用调用者令牌和 RLS 做项目授权，再用仅存在于服务端的 secret key 写入；上传完成后还会向 R2 查询对象大小、类型和内部资产标识，验证通过才标记 `ready`。

## 上传流程

1. 客户端必须先通过 Supabase Auth 登录。
2. 客户端把项目 ID、文件名、MIME 类型和大小发给 `assets` Function。
3. 小文件获得一次性 `PUT` 签名；大文件创建 multipart 会话并按需批量申请分片签名。
4. 文件从客户端直接进入 R2 的 `_uploads/` 临时键，不经过 Supabase 数据库，也不经过 Edge Function 内存；单文件签名会绑定声明的字节数。
5. 客户端提交 ETag 列表；服务端完成 multipart，并用 `HeadObject` 校验大小、类型和内部资产标识。
6. 校验通过后，服务端把临时对象复制到不可变正式键并删除临时对象。旧上传签名即使仍在有效期内，也不能覆盖已完成资产。
7. 下载前再次检查项目成员身份，只返回短时有效的 `GET` 签名。

默认值：100 MiB 以内单次上传，超过后使用 32 MiB 分片；单资产上限 50 GiB；开发账号已预留资产总量上限 20 GiB、最多 5 个并行上传；签名 15 分钟失效；上传会话 24 小时失效。可通过 `.env.example` 中的变量调整。

## 本地验证

```bash
npm install
npm run check:cloud
npm run typecheck:desktop
```

如已启动 Docker Desktop，可继续运行：

```bash
npm run supabase -- start
npm run supabase -- db reset
npm run supabase -- functions serve assets --env-file .env.local
```

`.env.local` 只能保存在本机，不能提交到 Git。

## 首次远程部署（需要登录授权）

下面步骤会操作你的 Supabase 和 Cloudflare 账号，执行前必须由项目所有者登录并确认目标项目。

### 1. Cloudflare R2

```bash
npx wrangler login
npx wrangler r2 bucket create anime-armory-private-dev --location apac
npx wrangler r2 bucket cors set anime-armory-private-dev \
  --file infrastructure/r2/cors.wrangler.development.json
npx wrangler r2 bucket lifecycle add anime-armory-private-dev \
  cleanup-staged-uploads _uploads/ \
  --expire-days 2 --abort-multipart-days 1 --force
npx wrangler r2 bucket cors list anime-armory-private-dev
```

然后在 Cloudflare Dashboard 为该桶创建仅限 Object Read & Write 的 R2 S3 API Token，取得：

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET=anime-armory-private-dev`

不要开启 public bucket，也不要把这些值放进 Electron renderer、Web 构建变量或 Git。

### 2. Supabase

在 Supabase 创建开发项目时，选靠近主要开发/测试用户的区域。然后执行：

```bash
npm run supabase -- login
npm run supabase -- link --project-ref YOUR_PROJECT_REF
npm run supabase -- db push
npm run supabase -- secrets set \
  R2_ACCOUNT_ID=... \
  R2_ACCESS_KEY_ID=... \
  R2_SECRET_ACCESS_KEY=... \
  R2_BUCKET=anime-armory-private-dev \
  ASSET_API_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
npm run supabase -- functions deploy assets
```

Supabase 会自动为 Edge Function 提供数据库 URL、publishable key 和 secret key；不需要把数据库管理密钥写入仓库。
开发项目关闭公开注册，仅通过管理员邀请或测试账号进入；准备开放注册前，先补充验证码、滥用防护和正式配额策略。

### 3. 客户端公开配置

客户端只需要可公开的：

```dotenv
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
ASSET_API_URL=https://YOUR_PROJECT_REF.supabase.co/functions/v1/assets
```

## 上线前补充项

- Web 域名确定后，同时更新 Edge Function allowlist 和 R2 CORS；生产配置不要沿用开发域名。
- 增加过期 multipart 会话清理任务、资产软删除/延迟物理删除任务和用量告警。
- 对用户提交的 `sha256` 目前只作为声明值保存；需要强完整性保证时，在后台校验后再标记可信。
- 大流量公开预览与私有原片分桶，公开派生资源再考虑自定义域名和缓存策略。
- 定期做 Postgres 导出，并保存 R2 对象清单；免费套餐不应被当作唯一备份。

## 迁移到腾讯云

1. 用标准 PostgreSQL 导出/导入迁移业务数据，保留内部 `accounts.id`。
2. 把 Supabase Auth 身份映射到新的身份提供方，向 `account_identities` 增加记录。
3. 批量复制 R2 对象到 COS，校验大小/哈希后更新 `storage_provider`、`bucket`、`key`。
4. 新增 COS `ObjectStore` 适配器，继续使用同一套签名上传 API。
5. 双写或增量同步通过后切流，再冻结旧桶；不要一次性改客户端文件 URL。
