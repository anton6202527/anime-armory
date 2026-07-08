# n2d Image QC（出图落档机检）

- episode: 第5集
- 总判定: **block** · 硬阻断 3（必须修） · 非阻断初筛 10 · 视觉降级 0
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 阶段跳转: **image** · image_qc 有硬阻断，需修复/重抽受影响镜头后重跑

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 53 张；未声明 live Clip PNG 0 张

## 人工逐图拒收（硬闸）
- 🟢 active rejects 0 · review `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第5集/human_image_review.json`

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 人体解剖 N5: 🟢 block 0 · warn 0
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: 🔴 block 1 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 6 · covered 6 · missing 0 · pending 47 · precision full

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟡 CHAR_01__囚犯初醒态：第1集→第2集 均值 0.406→0.4461（掉幅 -0.0401）（跌破绝对下限）
- 🟡 CHAR_01__镇魔司伪装态：第3集→第5集 均值 0.7255→0.6038（掉幅 0.1217）
- 处置：以基线集为准重审该角色定妆继承链，或确认是有意的成长态(evolution_profile)；趋势性掉幅在硬伤前就该收。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 9 镜已 lint · block 0 · warn 4
  - 🟡 脸部锚弱信噪比 CHAR_05/常态「face_anchor」（出图/共享/图片/定妆_CHAR_05__常态_脸部特写_脸锚裁切.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_05/常态「face_anchor」（出图/共享/图片/定妆_CHAR_05__常态_脸部特写_脸锚裁切.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 资产 PROP_村道血迹破布：出图/共享/图片/定妆_道具_村道血迹破布_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 3 · pending 3 · confirmed 0
- 确认文件: `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第5集/prop_shape_confirmations.json`
  - 🔴 Clip_01 图片/Clip01_first.png（PROP_上盘村断石碑 上盘村断石碑） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第5集/prop_shape_review/PROP_上盘村断石碑_Clip_01_Clip01_first_compare.png
  - 🔴 Clip_01 图片/Clip01_first.png（PROP_村道血迹破布 村道血迹破布） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第5集/prop_shape_review/PROP_村道血迹破布_Clip_01_Clip01_first_compare.png
  - 🔴 Clip_01 图片/Clip01_first.png（PROP_镇魔司黑衣赤纹 镇魔司黑衣赤纹） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第5集/prop_shape_review/PROP_镇魔司黑衣赤纹_Clip_01_Clip01_first_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
