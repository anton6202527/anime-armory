# 云端架构：本地作品 + R2 公开 Demo

## 当前产品边界

```text
内部维护者
  └─ scripts/publish_demos_r2.mjs
       └─ Cloudflare R2：anime-armory-demos-public
            ├─ catalog/v1/catalog.json
            └─ demos/v1/<line>/<work-id>/<sha256>.zip

公开 Electron 客户端（匿名）
  └─ 读取 catalog → 点击下载 → 校验 size/SHA-256 → 解压到 ~/AnimeArmory

用户自己的作品
  └─ 只保存在本地工作区，不登录、不上传、不云同步
```

- 桌面端没有 Supabase Auth、账号状态、上传按钮或上传 IPC。
- 用户只会看到官方 Demo 的下载入口。
- R2 Access Key、Secret 和 Cloudflare 登录态只存在于维护者环境，不进入
  Electron renderer、preload、安装包或 Git。
- 安装包、VSIX 和校验和仍通过 `tools/e2a` 发布到 GitHub Release；Demo ZIP
  与 GitHub Release 完全解耦。
- `apps/backend` 中已有的 Supabase/Postgres/私有资产基础层保留给未来 Web、
  团队协作或其他需要登录的业务，但公开桌面端不调用它。

## R2 资源

| 资源 | 可见性 | 用途 |
| --- | --- | --- |
| `anime-armory-demos-public` | 公开只读 | 官方 Demo 清单和不可变 ZIP |
| `anime-armory-private-dev` | 私有 | 预留的认证资产基础层，不供公开桌面端使用 |

开发期公开地址：

```text
https://pub-0bafc63084d743e78dbe9f72fc918988.r2.dev
```

`r2.dev` 适合开发验证。正式面向大量用户前，应给公开 Demo 桶绑定 Cloudflare
自定义域名并开启缓存，然后同时更新：

- `infrastructure/r2/demos.json` 的 `public_base_url`；
- `apps/desktop/src/main/services/demos.ts` 的默认公开地址；
- 重新执行 `npm run demos:publish`。

## 匿名下载安全边界

1. 客户端只读取固定 HTTPS R2 catalog。
2. catalog 中每条记录必须包含合法的作品相对路径、ZIP 对象键、精确字节数和
   64 位 SHA-256；下载地址必须与 catalog 同源。
3. ZIP 使用内容哈希不可变路径，更新 Demo 会产生新对象，不覆盖旧缓存。
4. 下载完成后先校验文件大小，再流式计算 SHA-256；任何不一致都拒绝解压。
5. 解压后的作品必须包含 `_进度.md`，目录名必须与 catalog 一致。
6. 已存在且非空的本地作品目录永远不会被覆盖。
7. 下载临时目录无论成功或失败都会清理。

## 发布 Demo

配置文件：`infrastructure/r2/demos.json`。默认从 `~/AnimeArmory` 读取配置的
六个作品。

```bash
# 只构建、安全扫描、压缩和生成 catalog，不操作云端
npm run demos:build

# 构建并发布到 R2；所有 ZIP 成功后才发布 catalog
npm run demos:publish

# 只构建/发布一条线或一个作品
node scripts/publish_demos_r2.mjs --only comic
node scripts/publish_demos_r2.mjs --publish --only '创作区/画漫画/仙界闭关小能手'
```

发布器会：

- 通过 `tools/release-safety/demo_safety.cjs` 排除密钥、账号配置、缓存和生成垃圾；
- 对漫剧 Demo 使用 `first-episode` profile，控制公开包体积；
- 固定 ZIP 时间戳，生成稳定资产名；
- 使用 `demos/v1/<line>/<work-id>/<sha256>.zip` 不可变对象键；
- 先上传全部 ZIP，最后上传 `catalog/v1/catalog.json`。

290 MiB 以内的对象使用当前 Wrangler OAuth 会话。更大的 ZIP 自动切换到 R2
S3 multipart，此时只在维护者 shell 中设置：

```bash
export R2_ACCOUNT_ID=...
export R2_ACCESS_KEY_ID=...
export R2_SECRET_ACCESS_KEY=...
npm run demos:publish
```

这些变量不能写入仓库或桌面端 `.env`。

## 安装包发布

```bash
bash tools/e2a/scripts/e2a_release.sh          # 本地 DMG
bash tools/e2a/scripts/e2a_release.sh --up     # DMG → GitHub Release
bash tools/e2a/scripts/e2a_release.sh --all    # DMG + EXE + VSIX → GitHub Release
```

旧的 `--demos` / `--demo-assets` 参数不再上传 GitHub，而会提示改用
`npm run demos:publish`。

## 本地验证

```bash
npm install
npm run test:demos
npm run typecheck:desktop
npm run build:desktop
```

远端验证至少检查：catalog 与发布产物一致、六个对象 `Content-Length` 与 catalog
一致、抽取一个对象重新计算 SHA-256，以及空工作区中出现 Demo 下载卡片但不存在
登录/上传入口。

## 迁移到腾讯云

将来国内运营时，只需把不可变 ZIP 和 catalog 复制到腾讯云 COS/CDN，保持 catalog
字段和对象相对路径不变，再切换公开基础域名。用户本地作品不参与迁移；预留的
Supabase 私有业务如届时启用，再独立迁移 Postgres、Auth 身份和私有对象。
