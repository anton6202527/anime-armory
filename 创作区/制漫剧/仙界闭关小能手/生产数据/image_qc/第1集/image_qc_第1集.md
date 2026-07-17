# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **block** · 硬阻断 1（必须修） · 非阻断初筛 6 · 视觉降级 0
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 阶段跳转: **image** · image_qc 有硬阻断，需修复/重抽受影响镜头后重跑

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 17 张；未声明 live Clip PNG 0 张

## 人工逐图拒收（硬闸）
- 🟢 active rejects 0 · review `/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/human_image_review.json`

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 人体解剖 N5: 🟢 block 0 · warn 0
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: 🟢 block 0 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 5 · covered 5 · missing 0 · pending 12 · precision full
- 人工脸部确认: applied 2 · 确认文件 `/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/face_confirmations.json`

## 核心角色五角 turnaround（逐视图 hash 收据硬闸）
- 🟢 checked forms 4 · pending/stale receipts 0 · contract `front/three_quarter/side/rear_three_quarter/back`
- 像素头顶/脚底/中心线/身高与脸框只作 WARN 级可复算证据；硬条件仅是当前 PNG 的逐视图 pass 收据。

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟢 已累积 2 个角色历史，暂无趋势性漂移。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🔴 7 镜已 lint · block 1 · warn 4
  - 🔴 脸部锚弱信噪比 CHAR_01/本集为14岁杂役常态「face_anchor」（出图/共享/图片/定妆_CHAR_01__本集为14岁杂役常态_表情_六联表.png）：脸占画面仅 2%（建议 ≥30%，核心角教头线 ≥20%）；裁切短边 941px（建议 ≥1024px，核心角教头线 ≥1024px）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_03/常态「face_anchor」（出图/共享/图片/定妆_CHAR_03__常态.png）：脸占画面仅 1%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 多视图对齐初筛异常 CHAR_01/本集为14岁杂役常态：身体中心线不齐：front(0.399) vs three_quarter(0.618)，差 0.219>0.055——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 多视图对齐初筛异常 CHAR_02/常态：比例不一：front 脸高是 side 的 2.52 倍（>1.35），不是同距离同景别的定妆板——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 2 · pending 0 · confirmed 2
- 确认文件: `/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_confirmations.json`
  - 🟢 Clip_01 图片/EP01_CLIP01.png（PROP_木牌 木牌） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_木牌_Clip_01_EP01_CLIP01_compare.png
  - 🟢 Clip_02 图片/EP01_CLIP02.png（PROP_木牌 木牌） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_木牌_Clip_02_EP01_CLIP02_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
