# n2d Image QC（出图落档机检）

- episode: 第2集
- 总判定: **review** · 硬阻断 0（必须修） · 非阻断初筛 30 · 视觉降级 0
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 阶段跳转: **video** · full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 26 张；未声明 live Clip PNG 0 张

## 人工逐图拒收（硬闸）
- 🟢 active rejects 0 · review `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/human_image_review.json`

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
- 🟢 已落档角色图 required 21 · covered 21 · missing 0 · pending 0 · precision full
  - 🟡 漏分类有脸镜 Clip_03 图片/Clip03_end.png：未在 character_shots 清单，待人工确认是否角色镜（非阻断）
  - 🟡 漏分类有脸镜 Clip_02 图片/EP02_CLIP02_preimpact.png：未在 character_shots 清单，待人工确认是否角色镜（非阻断）
- 人工脸部确认: applied 7 · 确认文件 `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_confirmations.json`

## 核心角色五角 turnaround（逐视图 hash 收据硬闸）
- 🟢 checked forms 3 · pending/stale receipts 0 · contract `front/three_quarter/side/rear_three_quarter/back`
- 像素头顶/脚底/中心线/身高与脸框只作 WARN 级可复算证据；硬条件仅是当前 PNG 的逐视图 pass 收据。

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟢 已累积 2 个角色历史，暂无趋势性漂移。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 8 镜已 lint · block 0 · warn 10
  - 🟡 脸部锚弱信噪比 CHAR_02/“濒死重伤态”「face_anchor」（出图/共享/图片/定妆_CHAR_02__濒死重伤态_脸部特写_脸锚裁切.png）：脸占画面仅 3%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_02/“濒死重伤态”「克制」（出图/共享/图片/定妆_CHAR_02__濒死重伤态_表情_克制.png）：脸占画面仅 3%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 多视图对齐初筛异常 CHAR_01/“囚途残损态”：视平线不齐：three_quarter(0.14) vs back(0.43)，跨视图脸中心高度差 29%>6%；比例不一：front 脸高是 rear_three_quarter 的 2.00 倍（>1.35），不是同距离同景别的定妆板——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 多视图对齐初筛异常 CHAR_02/“濒死重伤态”：脚底线不齐：side(0.950) vs rear_three_quarter(1.000)，差 0.050>0.035；身体中心线不齐：side(0.485) vs rear_three_quarter(0.625)，差 0.140>0.055——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 多视图对齐初筛异常 BEAST_01/“穿心复生态”：脚底线不齐：rear_three_quarter(0.936) vs side(0.972)，差 0.036>0.035；视平线不齐：rear_three_quarter(0.29) vs back(0.90)，跨视图脸中心高度差 61%>6%；比例不一：side 脸高是 back 的 2.11 倍（>1.35），不是同距离同景别的定妆板——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 静态长镜 EP02_CLIP02：first↔end 锚 dHash=10/64（≤10≈同构图）且时长 12.076s——视频后端拿到起点=终点的锚只会产几乎不动的长镜（成片 PPT 感根源）。处理：①改尾锚为不同构图/景别（推镜落幅、反应镜、插入镜）②按动作拆碎切 ③确属留白/定格镜则在 pacing_role 标注豁免。
  - 🟡 静态长镜 EP02_CLIP05：first↔end 锚 dHash=10/64（≤10≈同构图）且时长 9.207s——视频后端拿到起点=终点的锚只会产几乎不动的长镜（成片 PPT 感根源）。处理：①改尾锚为不同构图/景别（推镜落幅、反应镜、插入镜）②按动作拆碎切 ③确属留白/定格镜则在 pacing_role 标注豁免。
  - 🟡 镜头构图重复 EP02_CLIP02 ↔ EP02_CLIP03：首帧 dHash=10/64——观众在成片里会看到两个几乎一样的镜头。换景别/机位/构图重出其一，或合并两镜。
  - 🟡 镜头构图重复 EP02_CLIP04 ↔ EP02_CLIP05：首帧 dHash=6/64——观众在成片里会看到两个几乎一样的镜头。换景别/机位/构图重出其一，或合并两镜。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 79 · pending 0 · confirmed 79
- 确认文件: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_confirmations.json`
  - 🟢 shared_primary 出图/共享/图片/定妆_特效_墨虎谱影.png（VFX_墨虎谱影 墨虎谱影） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_墨虎谱影_shared_primary_定妆_特效_墨虎谱影_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_特效_百妖谱.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_shared_primary_定妆_特效_百妖谱_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_特效_百妖谱金色古卷面板.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_shared_primary_定妆_特效_百妖谱金色古卷面板_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_武器_横刀.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_shared_primary_定妆_武器_横刀_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_武器_横刀.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_shared_primary_定妆_武器_横刀_compare.png
  - 🟢 Clip_01 图片/Clip01_end.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_01_Clip01_end_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_01_EP02_CLIP01_start_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a1.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_01_EP02_CLIP01_start_a1_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a2.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_01_EP02_CLIP01_start_a2_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a3.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_01_EP02_CLIP01_start_a3_compare.png
  - 🟢 Clip_01 图片/Clip01_end.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_01_Clip01_end_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_01_EP02_CLIP01_start_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a1.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_01_EP02_CLIP01_start_a1_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a2.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_01_EP02_CLIP01_start_a2_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a3.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_01_EP02_CLIP01_start_a3_compare.png
  - 🟢 Clip_01 图片/Clip01_end.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_01_Clip01_end_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_01_EP02_CLIP01_start_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_01_EP02_CLIP01_start_a1_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a2.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_01_EP02_CLIP01_start_a2_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a3.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_01_EP02_CLIP01_start_a3_compare.png
  - 🟢 Clip_01 图片/Clip01_end.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_01_Clip01_end_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_01_EP02_CLIP01_start_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_01_EP02_CLIP01_start_a1_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a2.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_01_EP02_CLIP01_start_a2_compare.png
  - 🟢 Clip_01 图片/EP02_CLIP01_start_a3.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_01_EP02_CLIP01_start_a3_compare.png
  - 🟢 Clip_02 图片/EP02_CLIP02_preimpact.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_02_EP02_CLIP02_preimpact_compare.png
  - 🟢 Clip_02 图片/EP02_CLIP02_start.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_02_EP02_CLIP02_start_compare.png
  - 🟢 Clip_02 图片/EP02_CLIP02_start_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_02_EP02_CLIP02_start_a1_compare.png
  - 🟢 Clip_02 图片/EP02_CLIP02_preimpact.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_02_EP02_CLIP02_preimpact_compare.png
  - 🟢 Clip_02 图片/EP02_CLIP02_start.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_02_EP02_CLIP02_start_compare.png
  - 🟢 Clip_02 图片/EP02_CLIP02_start_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_02_EP02_CLIP02_start_a1_compare.png
  - 🟢 Clip_03 图片/Clip03_end.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_03_Clip03_end_compare.png
  - 🟢 Clip_03 图片/EP02_CLIP03_impact.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_03_EP02_CLIP03_impact_compare.png
  - 🟢 Clip_03 图片/EP02_CLIP03_recovery.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_03_EP02_CLIP03_recovery_compare.png
  - 🟢 Clip_03 图片/Clip03_end.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_03_Clip03_end_compare.png
  - 🟢 Clip_03 图片/EP02_CLIP03_impact.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_03_EP02_CLIP03_impact_compare.png
  - 🟢 Clip_03 图片/EP02_CLIP03_recovery.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_03_EP02_CLIP03_recovery_compare.png
  - 🟢 Clip_04 图片/EP02_CLIP04_end.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_04_EP02_CLIP04_end_compare.png
  - 🟢 Clip_04 图片/EP02_CLIP04_end_a1.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_04_EP02_CLIP04_end_a1_compare.png
  - 🟢 Clip_04 图片/EP02_CLIP04_end_a2.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_04_EP02_CLIP04_end_a2_compare.png
  - 🟢 Clip_04 图片/EP02_CLIP04_start.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_04_EP02_CLIP04_start_compare.png
  - 🟢 Clip_04 图片/EP02_CLIP04_end.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_04_EP02_CLIP04_end_compare.png
  - 🟢 Clip_04 图片/EP02_CLIP04_end_a1.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_04_EP02_CLIP04_end_a1_compare.png
  - 🟢 Clip_04 图片/EP02_CLIP04_end_a2.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_04_EP02_CLIP04_end_a2_compare.png
  - 🟢 Clip_04 图片/EP02_CLIP04_start.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_04_EP02_CLIP04_start_compare.png
  - 🟢 Clip_05 图片/Clip05_end.png（VFX_墨虎谱影 墨虎谱影） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_墨虎谱影_Clip_05_Clip05_end_compare.png
  - 🟢 Clip_05 图片/Clip05_end.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_05_Clip05_end_compare.png
  - 🟢 Clip_05 图片/Clip05_end.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_05_Clip05_end_compare.png
  - 🟢 Clip_05 图片/Clip05_end.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_05_Clip05_end_compare.png
  - 🟢 Clip_05 图片/Clip05_end.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_05_Clip05_end_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_end.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_06_EP02_CLIP06_end_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_start.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_06_EP02_CLIP06_start_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_start_a1.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_06_EP02_CLIP06_start_a1_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_end.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_06_EP02_CLIP06_end_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_start.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_06_EP02_CLIP06_start_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_start_a1.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_06_EP02_CLIP06_start_a1_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_end.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_06_EP02_CLIP06_end_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_start.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_06_EP02_CLIP06_start_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_start_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_06_EP02_CLIP06_start_a1_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_end.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_06_EP02_CLIP06_end_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_start.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_06_EP02_CLIP06_start_compare.png
  - 🟢 Clip_06 图片/EP02_CLIP06_start_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_06_EP02_CLIP06_start_a1_compare.png
  - 🟢 Clip_07 图片/Clip07_end.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_07_Clip07_end_compare.png
  - 🟢 Clip_07 图片/EP02_CLIP07_start.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_07_EP02_CLIP07_start_compare.png
  - 🟢 Clip_07 图片/EP02_CLIP07_start_a1.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_07_EP02_CLIP07_start_a1_compare.png
  - 🟢 Clip_07 图片/EP02_CLIP07_start_a2.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_01_Clip_07_EP02_CLIP07_start_a2_compare.png
  - 🟢 Clip_07 图片/Clip07_end.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_07_Clip07_end_compare.png
  - 🟢 Clip_07 图片/EP02_CLIP07_start.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_07_EP02_CLIP07_start_compare.png
  - 🟢 Clip_07 图片/EP02_CLIP07_start_a1.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_07_EP02_CLIP07_start_a1_compare.png
  - 🟢 Clip_07 图片/EP02_CLIP07_start_a2.png（WEAPON_横刀 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/WEAPON_横刀_Clip_07_EP02_CLIP07_start_a2_compare.png
  - 🟢 Clip_08 图片/EP02_CLIP08_end.png（VFX_墨虎谱影 墨虎谱影） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_墨虎谱影_Clip_08_EP02_CLIP08_end_compare.png
  - 🟢 Clip_08 图片/EP02_CLIP08_start.png（VFX_墨虎谱影 墨虎谱影） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_墨虎谱影_Clip_08_EP02_CLIP08_start_compare.png
  - 🟢 Clip_08 图片/EP02_CLIP08_start_a1.png（VFX_墨虎谱影 墨虎谱影） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_墨虎谱影_Clip_08_EP02_CLIP08_start_a1_compare.png
  - 🟢 Clip_08 图片/EP02_CLIP08_end.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_08_EP02_CLIP08_end_compare.png
  - 🟢 Clip_08 图片/EP02_CLIP08_start.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_08_EP02_CLIP08_start_compare.png
  - 🟢 Clip_08 图片/EP02_CLIP08_start_a1.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_百妖谱_Clip_08_EP02_CLIP08_start_a1_compare.png
  - 🟢 Clip_08 图片/EP02_CLIP08_end.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_08_EP02_CLIP08_end_compare.png
  - 🟢 Clip_08 图片/EP02_CLIP08_start.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_08_EP02_CLIP08_start_compare.png
  - 🟢 Clip_08 图片/EP02_CLIP08_start_a1.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/prop_shape_review/VFX_系统面板_Clip_08_EP02_CLIP08_start_a1_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
