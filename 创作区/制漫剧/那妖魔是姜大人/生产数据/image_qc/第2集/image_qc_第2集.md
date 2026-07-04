# n2d Image QC（出图落档机检）

- episode: 第2集
- 总判定: **review** · 硬阻断 0（必须修） · 非阻断初筛 8 · 视觉降级 0
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 阶段跳转: **video** · full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 35 张；未声明 live Clip PNG 0 张

## 人工逐图拒收（硬闸）
- 🟢 active rejects 0 · review `/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/human_image_review.json`

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟡 block 0 · warn 2
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 人体解剖 N5: 🟢 block 0 · warn 0
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: 🟢 block 0 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 35 · covered 35 · missing 0 · pending 0 · precision full

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟡 CHAR_01__囚犯初醒态：第1集→第2集 均值 0.4057→0.4469（掉幅 -0.0412）（跌破绝对下限）
- 处置：以基线集为准重审该角色定妆继承链，或确认是有意的成长态(evolution_profile)；趋势性掉幅在硬伤前就该收。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 10 镜已 lint · block 0 · warn 3
  - 🟡 脸部锚弱信噪比 CHAR_01/囚犯初醒态「克制」（出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png）：脸占画面仅 8%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_01/囚犯初醒态「震动」（出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png）：脸占画面仅 11%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
