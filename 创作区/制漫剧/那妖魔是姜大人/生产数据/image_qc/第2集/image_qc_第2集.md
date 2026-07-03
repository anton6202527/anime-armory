# n2d Image QC（出图落档机检）

- episode: 第2集
- 总判定: **block** · 硬阻断 55（必须修） · 非阻断初筛 23 · 视觉降级 2
- 机检能力: **degraded** · 当前解释器: `/opt/homebrew/opt/python@3.14/bin/python3.14`
- 阶段跳转: **image** · 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 缺失/降级: insightface/onnxruntime/buffalo_l face embedding, 崩脸 G1, 锚点门 N3
- 建议安装: 优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。

## 本集图片命名空间（硬闸）
- 🔴 当前 prompt 声明目标 30 张；未声明 live Clip PNG 1 张
  - 🔴 出图/第2集/图片/Clip03_a1.png：live 图片目录中的 Clip PNG 未被当前 01_分镜出图.md 目标集声明

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🔴 block 8 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: ⏭ 跳过（锚点质量门已跳过（未装 insightface/cv2）——主参考是否单张清晰正脸暂由人判。）

## 角色脸定妆比对覆盖（硬闸）
- 🔴 已落档角色图 required 24 · covered 0 · missing 24 · pending 6 · precision degraded
  - 🔴 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel） 图片/Clip01_first.png：face_precision_not_full
  - 🔴 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel） 图片/Clip01_mid.png：face_precision_not_full
  - 🔴 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel） 图片/Clip01_end.png：face_precision_not_full
  - 🔴 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse） 图片/Clip02_first.png：face_precision_not_full
  - 🔴 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse） 图片/Clip02_mid.png：face_precision_not_full
  - 🔴 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse） 图片/Clip02_end.png：face_precision_not_full
  - 🔴 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange） 图片/Clip03_first.png：face_precision_not_full
  - 🔴 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange） 图片/Clip03_mid.png：face_precision_not_full
  - 🔴 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange） 图片/Clip03_end.png：face_precision_not_full
  - 🔴 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange） 图片/Clip04_first.png：face_precision_not_full
  - 🔴 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange） 图片/Clip04_mid.png：face_precision_not_full
  - 🔴 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange） 图片/Clip04_end.png：face_precision_not_full
  - 🔴 镜头 5（`EP02_CLIP05` · 一百年到账与收录选择 · system_panel） 图片/Clip05_first.png：face_precision_not_full
  - 🔴 镜头 5（`EP02_CLIP05` · 一百年到账与收录选择 · system_panel） 图片/Clip05_mid.png：face_precision_not_full
  - 🔴 镜头 5（`EP02_CLIP05` · 一百年到账与收录选择 · system_panel） 图片/Clip05_end.png：face_precision_not_full
  - 🔴 镜头 6（`EP02_CLIP06` · 古卷收虎与道行流逝 · system_panel） 图片/Clip06_first.png：face_precision_not_full
  - 🔴 镜头 6（`EP02_CLIP06` · 古卷收虎与道行流逝 · system_panel） 图片/Clip06_mid.png：face_precision_not_full
  - 🔴 镜头 6（`EP02_CLIP06` · 古卷收虎与道行流逝 · system_panel） 图片/Clip06_end.png：face_precision_not_full
  - 🔴 镜头 7（`EP02_CLIP07` · 猛虎快刀圆满与状态面板 · system_panel） 图片/Clip07_first.png：face_precision_not_full
  - 🔴 镜头 7（`EP02_CLIP07` · 猛虎快刀圆满与状态面板 · system_panel） 图片/Clip07_mid.png：face_precision_not_full
  - 🔴 镜头 7（`EP02_CLIP07` · 猛虎快刀圆满与状态面板 · system_panel） 图片/Clip07_end.png：face_precision_not_full
  - 🔴 镜头 8（`EP02_CLIP08` · 姜月初读懂长久买卖 · ） 图片/Clip08_first.png：face_precision_not_full
  - 🔴 镜头 8（`EP02_CLIP08` · 姜月初读懂长久买卖 · ） 图片/Clip08_first.png：face_precision_not_full
  - 🔴 镜头 8（`EP02_CLIP08` · 姜月初读懂长久买卖 · ） 图片/Clip08_first.png：face_precision_not_full
- note: 已落档角色 PNG 存在，但 face_consistency 不是 full 精度；不能证明与定妆照同人。

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟢 已累积 2 个角色历史，暂无趋势性漂移。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 11 镜已 lint · block 0 · warn 23
  - 🟡 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 5（`EP02_CLIP05` · 一百年到账与收录选择 · system_panel）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 5（`EP02_CLIP05` · 一百年到账与收录选择 · system_panel）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 6（`EP02_CLIP06` · 古卷收虎与道行流逝 · system_panel）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 6（`EP02_CLIP06` · 古卷收虎与道行流逝 · system_panel）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 7（`EP02_CLIP07` · 猛虎快刀圆满与状态面板 · system_panel）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 7（`EP02_CLIP07` · 猛虎快刀圆满与状态面板 · system_panel）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 8（`EP02_CLIP08` · 姜月初读懂长久买卖 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 8（`EP02_CLIP08` · 姜月初读懂长久买卖 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 9（`EP02_CLIP09` · 替裴合眼与欠命账 · intimate_interaction）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 9（`EP02_CLIP09` · 替裴合眼与欠命账 · intimate_interaction）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 10（`EP02_CLIP10` · 官道火把马蹄逼近 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 10（`EP02_CLIP10` · 官道火把马蹄逼近 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。

## 降级近景人审队列（无 insightface 时人眼判同人 ①）
- 22 个近景脸需人审：开并排对比图『定妆主参考 ↔ 本镜脸』秒判同不同人
  - Clip_01（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_01_compare.png
  - Clip_01（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_01_compare.png
  - Clip_01（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_01_compare.png
  - Clip_02（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_02_compare.png
  - Clip_02（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_02_compare.png
  - Clip_02（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_02_compare.png
  - Clip_03（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_03_compare.png
  - Clip_03（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_03_compare.png
  - Clip_03（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_03_compare.png
  - Clip_05（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_05_compare.png
  - Clip_05（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_05_compare.png
  - Clip_05（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_05_compare.png
  - Clip_07（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_07_compare.png
  - Clip_07（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_07_compare.png
  - Clip_07（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_07_compare.png
  - Clip_08（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_08_compare.png
  - Clip_04（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_04_compare.png
  - Clip_04（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_04_compare.png
  - Clip_04（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_04_compare.png
  - Clip_06（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_06_compare.png
  - Clip_06（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_06_compare.png
  - Clip_06（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_06_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/纯文生图/非法 CHAR_id），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
