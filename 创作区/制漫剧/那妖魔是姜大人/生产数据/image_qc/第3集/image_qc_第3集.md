# n2d Image QC（出图落档机检）

- episode: 第3集
- 总判定: **block** · 硬阻断 3（必须修） · 非阻断初筛 26 · 视觉降级 0
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 阶段跳转: **image** · image_qc 有硬阻断，需修复/重抽受影响镜头后重跑

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 22 张；未声明 live Clip PNG 0 张

## 人工逐图拒收（硬闸）
- 🟢 active rejects 0 · review `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/human_image_review.json`

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🔴 block 1 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 人体解剖 N5: 🟢 block 0 · warn 0
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: 🟢 block 0 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 21 · covered 21 · missing 0 · pending 1 · precision full
- 人工脸部确认: applied 12 · 确认文件 `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/face_confirmations.json`

## 核心角色五角 turnaround（逐视图 hash 收据硬闸）
- 🟢 checked forms 6 · pending/stale receipts 0 · contract `front/three_quarter/side/rear_three_quarter/back`
- 像素头顶/脚底/中心线/身高与脸框只作 WARN 级可复算证据；硬条件仅是当前 PNG 的逐视图 pass 收据。

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟢 已累积 4 个角色历史，暂无趋势性漂移。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 8 镜已 lint · block 0 · warn 8
  - 🟡 脸部锚弱信噪比 CHAR_03/常态「face_anchor」（出图/共享/图片/定妆_CHAR_03__常态_脸部特写_脸锚裁切.png）：脸占画面仅 5%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_02/“濒死重伤态”「克制」（出图/共享/图片/定妆_CHAR_02__濒死重伤态_表情_克制.png）：脸占画面仅 3%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 多视图对齐初筛异常 CHAR_01/“囚途残损态”：视平线不齐：three_quarter(0.14) vs back(0.43)，跨视图脸中心高度差 29%>6%；比例不一：front 脸高是 rear_three_quarter 的 2.00 倍（>1.35），不是同距离同景别的定妆板——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 多视图对齐初筛异常 CHAR_03/常态：视平线不齐：three_quarter(0.13) vs back(0.77)，跨视图脸中心高度差 64%>6%——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 多视图对齐初筛异常 CHAR_02/“濒死重伤态”：脚底线不齐：side(0.950) vs rear_three_quarter(1.000)，差 0.050>0.035；身体中心线不齐：side(0.485) vs rear_three_quarter(0.625)，差 0.140>0.055——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 多视图对齐初筛异常 BEAST_01/“穿心复生态”：脚底线不齐：rear_three_quarter(0.936) vs side(0.972)，差 0.036>0.035；视平线不齐：rear_three_quarter(0.29) vs back(0.90)，跨视图脸中心高度差 61%>6%；比例不一：side 脸高是 back 的 2.11 倍（>1.35），不是同距离同景别的定妆板——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 静态长镜 EP03_CLIP06：first↔end 锚 dHash=8/64（≤10≈同构图）且时长 15.551s——视频后端拿到起点=终点的锚只会产几乎不动的长镜（成片 PPT 感根源）。处理：①改尾锚为不同构图/景别（推镜落幅、反应镜、插入镜）②按动作拆碎切 ③确属留白/定格镜则在 pacing_role 标注豁免。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 48 · pending 2 · confirmed 46
- 确认文件: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_confirmations.json`
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_镇魔司制服.png（PROP_镇魔司制服 镇魔司制服） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/PROP_镇魔司制服_shared_primary_定妆_道具_镇魔司制服_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_武器_横刀.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_shared_primary_定妆_武器_横刀_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_武器_横刀.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_shared_primary_定妆_武器_横刀_compare.png
  - 🔴 Clip_01 图片/Clip01_end.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_01_Clip01_end_compare.png
  - 🟢 Clip_01 图片/Clip01_first.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_01_Clip01_first_compare.png
  - 🟢 Clip_01 图片/Clip01_first_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_01_Clip01_first_a1_compare.png
  - 🔴 Clip_01 图片/Clip01_end.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_01_Clip01_end_compare.png
  - 🟢 Clip_01 图片/Clip01_first.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_01_Clip01_first_compare.png
  - 🟢 Clip_01 图片/Clip01_first_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_01_Clip01_first_a1_compare.png
  - 🟢 Clip_02 图片/Clip02_first.png（PROP_镇魔司制服 镇魔司制服） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/PROP_镇魔司制服_Clip_02_Clip02_first_compare.png
  - 🟢 Clip_02 图片/Clip02_first.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_02_Clip02_first_compare.png
  - 🟢 Clip_02 图片/Clip02_first.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_02_Clip02_first_compare.png
  - 🟢 Clip_03 图片/Clip03_first.png（PROP_镇魔司制服 镇魔司制服） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/PROP_镇魔司制服_Clip_03_Clip03_first_compare.png
  - 🟢 Clip_03 图片/EP03_CLIP03_a1.png（PROP_镇魔司制服 镇魔司制服） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/PROP_镇魔司制服_Clip_03_EP03_CLIP03_a1_compare.png
  - 🟢 Clip_03 图片/Clip03_first.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_03_Clip03_first_compare.png
  - 🟢 Clip_03 图片/EP03_CLIP03_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_03_EP03_CLIP03_a1_compare.png
  - 🟢 Clip_03 图片/Clip03_first.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_03_Clip03_first_compare.png
  - 🟢 Clip_03 图片/EP03_CLIP03_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_03_EP03_CLIP03_a1_compare.png
  - 🟢 Clip_04 图片/Clip04_end.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_04_Clip04_end_compare.png
  - 🟢 Clip_04 图片/Clip04_first.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_04_Clip04_first_compare.png
  - 🟢 Clip_04 图片/Clip04_first_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_04_Clip04_first_a1_compare.png
  - 🟢 Clip_04 图片/Clip04_end.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_04_Clip04_end_compare.png
  - 🟢 Clip_04 图片/Clip04_first.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_04_Clip04_first_compare.png
  - 🟢 Clip_04 图片/Clip04_first_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_04_Clip04_first_a1_compare.png
  - 🟢 Clip_05 图片/Clip05_first.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_05_Clip05_first_compare.png
  - 🟢 Clip_05 图片/Clip05_first_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_05_Clip05_first_a1_compare.png
  - 🟢 Clip_05 图片/Clip05_first.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_05_Clip05_first_compare.png
  - 🟢 Clip_05 图片/Clip05_first_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_05_Clip05_first_a1_compare.png
  - 🟢 Clip_06 图片/Clip06_end.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_06_Clip06_end_compare.png
  - 🟢 Clip_06 图片/Clip06_first.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_06_Clip06_first_compare.png
  - 🟢 Clip_06 图片/Clip06_first_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_06_Clip06_first_a1_compare.png
  - 🟢 Clip_06 图片/Clip06_first_a2.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_06_Clip06_first_a2_compare.png
  - 🟢 Clip_06 图片/Clip06_first_a3.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_06_Clip06_first_a3_compare.png
  - 🟢 Clip_06 图片/Clip06_end.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_06_Clip06_end_compare.png
  - 🟢 Clip_06 图片/Clip06_first.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_06_Clip06_first_compare.png
  - 🟢 Clip_06 图片/Clip06_first_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_06_Clip06_first_a1_compare.png
  - 🟢 Clip_06 图片/Clip06_first_a2.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_06_Clip06_first_a2_compare.png
  - 🟢 Clip_06 图片/Clip06_first_a3.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_06_Clip06_first_a3_compare.png
  - 🟢 Clip_07 图片/Clip07_first.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_07_Clip07_first_compare.png
  - 🟢 Clip_07 图片/Clip07_first_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_07_Clip07_first_a1_compare.png
  - 🟢 Clip_07 图片/EP03_CLIP07_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_07_EP03_CLIP07_a1_compare.png
  - 🟢 Clip_07 图片/Clip07_first.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_07_Clip07_first_compare.png
  - 🟢 Clip_07 图片/Clip07_first_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_07_Clip07_first_a1_compare.png
  - 🟢 Clip_07 图片/EP03_CLIP07_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_07_EP03_CLIP07_a1_compare.png
  - 🟢 Clip_08 图片/Clip08_first.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_08_Clip08_first_compare.png
  - 🟢 Clip_08 图片/EP03_CLIP08_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_01_Clip_08_EP03_CLIP08_a1_compare.png
  - 🟢 Clip_08 图片/Clip08_first.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_08_Clip08_first_compare.png
  - 🟢 Clip_08 图片/EP03_CLIP08_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/prop_shape_review/WEAPON_横刀_Clip_08_EP03_CLIP08_a1_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
