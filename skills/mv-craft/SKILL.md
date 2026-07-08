---
name: mv-craft
description: Shared machine contracts and deterministic helpers for the mv-* skill family — MV project _meta/_设置/_进度 fields, user choice points including `歌曲输入时序` (先传音乐 vs 后配歌曲), clip/timeline manifest conventions, identity/asset registries, video job manifest conventions, model candidate freshness, and AI visual usage disclosure. Other mv-* skills reference these by file path; users can also invoke directly for MV pipeline contract, manifest, registry, or AI usage disclosure questions. Triggers mv contract, mv-craft, MV合约, 歌曲输入时序, timeline_manifest, clip_plan, video_jobs, identity_registry, AI视觉使用披露, MV合规留痕.
---

# mv-craft — 制MV线共享契约

`mv-craft` 是 `mv-*` 家族的机器单一真值源，不生成画面、不出视频。它只沉淀字段、选择点、阶段表、manifest 约定和合规留痕脚本，避免 `mv-image` / `mv-video` / `mv-compose` 各自解释同一件事。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`MV用途`、`歌曲输入时序`、`MV视觉风格`、`MV规划粒度`、`卡点策略`、`生图AI`、`MV一致性增强`、`生视频模型`、`生视频渠道`、`演唱口型` 等。

## 包含内容

| 主题 | 参考 / 脚本 | 何时用 |
|---|---|---|
| 机器契约 | `references/contract.md` + `scripts/contract.py` | 初始化项目、写 `_设置.md` / `_meta.json`、按 `歌曲输入时序` 决定阶段顺序、生成 clip/timeline/video job manifest 时 |
| 身份/资产注册 | `scripts/identity_registry.py` | 从角色卡、场景卡、视觉蓝图和 clip_plan 生成 `设定/identity_registry.json`、`设定/asset_registry.json`、`分镜/reference_plan.json` |
| 参考资产需求 | `scripts/identity_registry.py` | 同步生成 `设定/reference_requirements.json/.md`，列主角/成年态/手部/剑/场景/VFX 的缺口 |
| 正式版 readiness | `scripts/formal_readiness.py` | 判断当前项目能否当正式整首 MV 处理；demo/短歌/镜头不足/参考图未齐会落 blocker，并生成正式版升级计划 |
| 传统制片包 | `scripts/production_pack.py` | 由 clip_plan 生成 `分镜/animatic_manifest.json`、`制片/shot_list.json`、setup schedule、take log、picture lock/color pass 清单 |
| 候选新鲜度 | `../mv/_lib/freshness.py` + `../mv/_lib/refresh.py` | 模型/渠道/生图后端候选过期检查、刷新快照和 provenance |
| 阶段 gate | `scripts/gate.py` | `mv-plan` / `mv-video` / `mv-lyric-sync` / `mv-compose` 等正式阶段开跑前做确定性前置检查 |
| 进度回写 | `scripts/progress_set.py` + `scripts/mv_utils.py` | 阶段脚本完成后回写 `_进度.md`，并同步 `_meta.has_song/has_lyrics` |
| AI 视觉使用披露 | `scripts/ai_usage.py` | 发布、交平台前记录输入歌、AI 生图/视频等使用情况（仅项目留痕；AI 标识/披露/水印不由本流水线处理，移到工具之外按平台/地区法规自行处理） |

## 共享脚本

```bash
python3 skills/mv-craft/scripts/gate.py "<制MV作品根>" plan
python3 skills/mv-craft/scripts/progress_set.py "<制MV作品根>" plan
python3 skills/mv-craft/scripts/identity_registry.py "<制MV作品根>"
python3 skills/mv-craft/scripts/formal_readiness.py "<制MV作品根>" --no-fail
python3 skills/mv-craft/scripts/production_pack.py "<制MV作品根>"
python3 skills/mv/_lib/freshness.py

python3 skills/mv-craft/scripts/ai_usage.py "<制MV作品根>" \
  --visual-mode AI-generated \
  --video-mode AI-generated \
  --publish-target 抖音
```

输出：
- `合规/ai_usage.json`
- `合规/AI使用说明.md`
- `设定/identity_registry.json`
- `设定/asset_registry.json`
- `设定/reference_requirements.json`
- `分镜/reference_plan.json`
- `分镜/animatic_manifest.json`
- `制片/shot_list.json`
- `制片/setup_schedule.md`
- `制片/take_log.csv`
- `制片/picture_lock_color_checklist.md`
- `生产数据/formal_readiness/formal_readiness.json`
- `生产数据/formal_readiness/formal_upgrade_plan.md`
- `skills/mv/references/candidate_snapshots/*.json`

## 设计原则

> 跨线通用原则（选择点不写死 C1/C2、阶段回写 B5、脚本不伪装云端自动化 B4、合规闸门 D1…）见 [`docs/skill-design-principles.md`](../../docs/skill-design-principles.md)，此处只列 mv 线特有原则。mv 的选择点目录：`skills/mv-craft/references/选择点与偏好.md`。

- **manifest 是源头**：clip 时长、转场、尾帧、prompt、已登记视频都落 manifest；`mv-compose` 不再凭文件名猜时间线。
- **registry 锁一致性**：主角、变体、道具、场景、VFX 用本线自持的身份/资产 ID 和 reference plan 传递；不得引用别线实现，也不得只靠聊天记录记住主角长相。
- **脚本先过 gate（本线前置条件）**：正式产物阶段默认调用 `scripts/gate.py`，缺最终 `歌/song.*`、歌词、beatgrid、正式视觉蓝图、首帧或已选视频时先停下。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 直接手工改写 manifest.json 内容 | manifest 文件是各 stage 传递数据的机器契约，手动修改极易破坏其字段规范，应通过对应的阶段脚本重新生成 |
| 只靠 prompt 锁主角，不落 registry | 跑 `identity_registry.py` 生成身份/资产/参考计划，再让 mv-image/mv-video 消费这些 ID |
| demo 被误当正式版 | 跑 `formal_readiness.py`；有 blocker 时只能当 demo/reference，不能发布为正式 MV |
| 只有 clip_plan，没有制片组织 | 跑 `production_pack.py` 生成 shot list、setup schedule、take log 和 picture lock/color pass 清单 |
| 发布前遗漏 ai_usage 留痕 | 作品在脱离管线并发布前，必须在合规/目录下调用披露脚本并填写具体授权模式，否则质检将失败 |
| 偏好设定硬编码 | 管线中的卡点策略/粒度等不可写死，须经由此处统一定义的方式并从 `_设置.md` 读取 |
| 绕过 gate 手工跑下游 | 先跑对应 stage gate；如果确实要临时兜底，必须显式传该阶段的 fallback 参数并在交付说明里标注 |
