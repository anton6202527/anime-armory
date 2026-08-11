# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **block** · 硬阻断 1（必须修） · 非阻断初筛 5 · 视觉降级 1
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 阶段跳转: **image** · image_qc 有硬阻断，需修复/重抽受影响镜头后重跑

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 55 张；未声明 live Clip PNG 0 张
- note: 本集图片目录不存在。

## 人工逐图拒收（硬闸）
- 🟢 active rejects 0 · review `/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/human_image_review.json`

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 人体解剖 N5: 🟢 block 0 · warn 0
- 接缝接力: ⏭ 跳过（无 /Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/出图/第1集/图片——出图后再跑接缝机检。）
- 锚点门 N3: 🟢 block 0 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 0 · covered 0 · missing 0 · pending 47 · precision full

## 核心角色五角 turnaround（逐视图 hash 收据硬闸）
- 🟢 checked forms 7 · pending/stale receipts 0 · contract `front/three_quarter/side/rear_three_quarter/back`
- 像素头顶/脚底/中心线/身高与脸框只作 WARN 级可复算证据；硬条件仅是当前 PNG 的逐视图 pass 收据。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🔴 15 镜已 lint · block 1 · warn 5
  - 🟡 脸部锚弱信噪比 CHAR_WUDA/日常卖饼态「克制」（出图/共享/图片/定妆_CHAR_WUDA__日常卖饼态_表情_克制.png）：脸占画面仅 4%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🔴 脸部锚弱信噪比 CHAR_PANJINLIAN/25岁武大家常态「CHAR_PANJINLIAN/25岁武大家常态 同源脸锚」（出图/共享/图片/定妆_CHAR_PANJINLIAN__25岁武大家常态_脸部特写_脸锚裁切.png）：脸占画面仅 13%（建议 ≥30%，核心角教头线 ≥20%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_MAGISTRATE/常态「基础」（出图/共享/图片/定妆_CHAR_MAGISTRATE__常态_脸部特写_脸锚裁切.png）：脸占画面仅 4%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_XIMENQING/常态「基础」（出图/共享/图片/定妆_CHAR_XIMENQING__常态_脸部特写_脸锚裁切.png）：脸占画面仅 4%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 多视图对齐初筛异常 CHAR_WUSONG/28岁打虎态：视平线不齐：three_quarter(0.16) vs back(0.68)，跨视图脸中心高度差 52%>6%——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 多视图对齐初筛异常 CHAR_WUDA/日常卖饼态：视平线不齐：front(0.53) vs three_quarter(0.82)，跨视图脸中心高度差 29%>6%——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
