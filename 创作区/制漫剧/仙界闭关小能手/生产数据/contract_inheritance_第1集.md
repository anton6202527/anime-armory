# 契约继承 Diff · 第1集（出图 → 出视频）

- 出图侧：`出图/第1集/prompt/00_总览.md`
- 视频侧：`出视频/第1集/prompt/00_总览.md`
- 判定：**warn**（block=修复后才可出视频；warn=确认是否有意改写；规则：视频侧可细化为超集，不许改写/丢失）

| 字段 | 判定 | 说明 |
|---|---|---|
| 色调基线 | ✅ pass | 逐字一致 |
| 场景光位锚 | ⚠️ upstream_missing | 出图侧契约缺此字段（上游问题，不拦本步）：回 n2d-image 补 00_总览 视觉契约，image_preflight/image gate 会阻断 |
| 场景轴线视线 | ⚠️ upstream_missing | 出图侧契约缺此字段（上游问题，不拦本步）：回 n2d-image 补 00_总览 视觉契约，image_preflight/image gate 会阻断 |
| 角色状态演进 | ⚠️ upstream_missing | 出图侧契约缺此字段（上游问题，不拦本步）：回 n2d-image 补 00_总览 视觉契约，image_preflight/image gate 会阻断 |
| 景别阶梯 | ✅ pass | 逐字一致 |

## 场景光位锚 — upstream_missing
- 出图侧原文：（缺）
- 视频侧原文：（缺）
- 说明：出图侧契约缺此字段（上游问题，不拦本步）：回 n2d-image 补 00_总览 视觉契约，image_preflight/image gate 会阻断

## 场景轴线视线 — upstream_missing
- 出图侧原文：（缺）
- 视频侧原文：（缺）
- 说明：出图侧契约缺此字段（上游问题，不拦本步）：回 n2d-image 补 00_总览 视觉契约，image_preflight/image gate 会阻断

## 角色状态演进 — upstream_missing
- 出图侧原文：（缺）
- 视频侧原文：（缺）
- 说明：出图侧契约缺此字段（上游问题，不拦本步）：回 n2d-image 补 00_总览 视觉契约，image_preflight/image gate 会阻断

## 身份交接契约（出图首帧脸 → 出视频脸）
- ✅ 命名角色镜 10 个已核验 · 身份未锁 block 0
## 物料约束继承（场景/道具/服装/特效逐镜交接）
- ⚠️ 带资产的镜 7 个已核验 · 资产丢失 block 0 · id 缺 warn 5
  - ⚠️ [asset_handoff_dropped] Clip_03：出图绑定的资产 LOC_WAIMEN(?) 在出视频逐镜 prompt 丢了 id——执行端取不到其 reference_group/constraints/drift_forbidden，若非有意松引用，补回 LOC/PROP/WEAPON/VFX_xx 让结构/颜色/光位锚自动继承（防场景/道具/武器/特效跨镜漂移）。
  - ⚠️ [asset_handoff_dropped] Clip_04：出图绑定的资产 PROP_KEY(?)、PROP_TIE(?) 在出视频逐镜 prompt 丢了 id——执行端取不到其 reference_group/constraints/drift_forbidden，若非有意松引用，补回 LOC/PROP/WEAPON/VFX_xx 让结构/颜色/光位锚自动继承（防场景/道具/武器/特效跨镜漂移）。
  - ⚠️ [asset_handoff_dropped] Clip_05：出图绑定的资产 LOC_HOUSHAN(?)、PROP_SHUI(?) 在出视频逐镜 prompt 丢了 id——执行端取不到其 reference_group/constraints/drift_forbidden，若非有意松引用，补回 LOC/PROP/WEAPON/VFX_xx 让结构/颜色/光位锚自动继承（防场景/道具/武器/特效跨镜漂移）。
  - ⚠️ [asset_handoff_dropped] Clip_06：出图绑定的资产 LOC_HOUSHAN(?)、PROP_HEI(?)、PROP_SHUI(?) 在出视频逐镜 prompt 丢了 id——执行端取不到其 reference_group/constraints/drift_forbidden，若非有意松引用，补回 LOC/PROP/WEAPON/VFX_xx 让结构/颜色/光位锚自动继承（防场景/道具/武器/特效跨镜漂移）。
  - ⚠️ [asset_handoff_dropped] Clip_07：出图绑定的资产 LOC_HOUSHAN(?)、PROP_HEI(?) 在出视频逐镜 prompt 丢了 id——执行端取不到其 reference_group/constraints/drift_forbidden，若非有意松引用，补回 LOC/PROP/WEAPON/VFX_xx 让结构/颜色/光位锚自动继承（防场景/道具/武器/特效跨镜漂移）。
