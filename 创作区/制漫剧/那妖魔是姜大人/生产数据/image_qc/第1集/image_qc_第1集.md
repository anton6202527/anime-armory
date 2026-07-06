# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **review** · 硬阻断 0（必须修） · 非阻断初筛 67 · 视觉降级 0
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 阶段跳转: **video** · full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 31 张；未声明 live Clip PNG 0 张

## 人工逐图拒收（硬闸）
- 🟢 active rejects 0 · review `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/human_image_review.json`

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟡 block 0 · warn 3
- 道具/特效 P2: 🟢 block 0 · warn 0
- 人体解剖 N5: 🟢 block 0 · warn 0
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: 🟢 block 0 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 31 · covered 31 · missing 0 · pending 0 · precision full
- 人工脸部确认: applied 3 · 确认文件 `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_confirmations.json`

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟢 已累积 2 个角色历史，暂无趋势性漂移。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 11 镜已 lint · block 0 · warn 27
  - 🟡 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 4（`EP01_CLIP04` · 被迫扶裴南行 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 4（`EP01_CLIP04` · 被迫扶裴南行 · multi_character_same_frame）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 5（`EP01_CLIP05` · 虎妖诈死复苏 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 5（`EP01_CLIP05` · 虎妖诈死复苏 · reveal_reaction_chain）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 6（`EP01_CLIP06` · 裴长青最后一击被踹飞 · fight_exchange）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 6（`EP01_CLIP06` · 裴长青最后一击被踹飞 · fight_exchange）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 脸部锚弱信噪比 CHAR_04/常态「基础」（出图/共享/图片/定妆_CHAR_04__常态.png）：脸占画面仅 1%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定妆_CHAR_05__常态_脸部特写_脸锚裁切.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定妆_CHAR_05__常态_脸部特写_脸锚裁切.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_05/常态「基础」（出图/共享/图片/定妆_CHAR_05__常态.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 场景/道具/特效漂移人审队列（D）
- 3 个资产漂移镜需人审：开并排对比图『资产参考 ↔ 本镜』判是否漂
  - scene Clip_07（荒野尸骸战场）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/asset_review/scene_Clip_07_compare.png
  - scene Clip_07（荒野尸骸战场）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/asset_review/scene_Clip_07_compare.png
  - scene Clip_07（荒野尸骸战场）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/asset_review/scene_Clip_07_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
