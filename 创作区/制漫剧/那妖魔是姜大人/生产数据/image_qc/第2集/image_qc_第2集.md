# n2d Image QC（出图落档机检）

- episode: 第2集
- 总判定: **block** · 硬阻断 83（必须修） · 非阻断初筛 35 · 视觉降级 3
- 机检能力: **degraded** · 当前解释器: `/opt/homebrew/opt/python@3.14/bin/python3.14`
- 阶段跳转: **image** · 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 缺失/降级: insightface/onnxruntime/buffalo_l face embedding, 人体解剖 N5, 崩脸 G1, 锚点门 N3
- 建议安装: 优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 35 张；未声明 live Clip PNG 0 张

## 人工逐图拒收（硬闸）
- 🟢 active rejects 0 · review `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/human_image_review.json`

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟡 block 0 · warn 2
- 场景 O2: 🟡 block 0 · warn 1
- 道具/特效 P2: 🟢 block 0 · warn 0
- 人体解剖 N5: ⏭ 跳过（手部畸形机检已跳过（未装 cv2）——多指/粘连暂由人逐帧放大看。）
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: ⏭ 跳过（锚点质量门已跳过（未装 insightface/cv2）——主参考是否单张清晰正脸暂由人判。）

## 角色脸定妆比对覆盖（硬闸）
- 🔴 已落档角色图 required 35 · covered 0 · missing 35 · pending 0 · precision degraded
  - 🔴 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel） 图片/Clip01_first.png：face_precision_not_full
  - 🔴 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel） 图片/Clip01_mid.png：face_precision_not_full
  - 🔴 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel） 图片/Clip01_end.png：face_precision_not_full
  - 🔴 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse） 图片/Clip02_first.png：face_precision_not_full
  - 🔴 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse） 图片/Clip02_mid.png：face_precision_not_full
  - 🔴 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse） 图片/Clip02_end.png：face_precision_not_full
  - 🔴 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange） 图片/Clip03_first.png：face_precision_not_full
  - 🔴 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange） 图片/Clip03_a1.png：face_precision_not_full
  - 🔴 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange） 图片/Clip03_a2.png：face_precision_not_full
  - 🔴 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange） 图片/Clip03_end.png：face_precision_not_full
  - 🔴 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange） 图片/Clip04_first.png：face_precision_not_full
  - 🔴 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange） 图片/Clip04_a1.png：face_precision_not_full
  - 🔴 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange） 图片/Clip04_a2.png：face_precision_not_full
  - 🔴 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange） 图片/Clip04_a3.png：face_precision_not_full
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
  - 🔴 镜头 8（`EP02_CLIP08` · 姜月初读懂长久买卖 · reveal_reaction_chain） 图片/Clip08_first.png：face_precision_not_full
  - 🔴 镜头 8（`EP02_CLIP08` · 姜月初读懂长久买卖 · reveal_reaction_chain） 图片/Clip08_mid.png：face_precision_not_full
  - 🔴 镜头 8（`EP02_CLIP08` · 姜月初读懂长久买卖 · reveal_reaction_chain） 图片/Clip08_end.png：face_precision_not_full
  - 🔴 镜头 9（`EP02_CLIP09` · 替裴合眼与欠命账 · intimate_interaction） 图片/Clip09_first.png：face_precision_not_full
  - 🔴 镜头 9（`EP02_CLIP09` · 替裴合眼与欠命账 · intimate_interaction） 图片/Clip09_a1.png：face_precision_not_full
  - 🔴 镜头 9（`EP02_CLIP09` · 替裴合眼与欠命账 · intimate_interaction） 图片/Clip09_a2.png：face_precision_not_full
  - 🔴 镜头 9（`EP02_CLIP09` · 替裴合眼与欠命账 · intimate_interaction） 图片/Clip09_a3.png：face_precision_not_full
  - 🔴 镜头 9（`EP02_CLIP09` · 替裴合眼与欠命账 · intimate_interaction） 图片/Clip09_end.png：face_precision_not_full
  - 🔴 镜头 10（`EP02_CLIP10` · 官道火把马蹄逼近 · stealth_stalk） 图片/Clip10_first.png：face_precision_not_full
  - 🔴 镜头 10（`EP02_CLIP10` · 官道火把马蹄逼近 · stealth_stalk） 图片/Clip10_mid.png：face_precision_not_full
  - 🔴 镜头 10（`EP02_CLIP10` · 官道火把马蹄逼近 · stealth_stalk） 图片/Clip10_end.png：face_precision_not_full
- note: 已落档角色 PNG 存在，但 face_consistency 不是 full 精度；不能证明与定妆照同人。

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟡 CHAR_01__囚犯初醒态：第1集→第2集 均值 0.4057→0.4469（掉幅 -0.0412）（跌破绝对下限）
- 处置：以基线集为准重审该角色定妆继承链，或确认是有意的成长态(evolution_profile)；趋势性掉幅在硬伤前就该收。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🔴 10 镜已 lint · block 15 · warn 31
  - 🔴 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel）：资产 `VFX_系统面板` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse）：资产 `VFX_系统面板` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange）：资产 `VFX_妖气` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange）：资产 `VFX_系统面板` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 5（`EP02_CLIP05` · 一百年到账与收录选择 · system_panel）：资产 `VFX_系统面板` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 5（`EP02_CLIP05` · 一百年到账与收录选择 · system_panel）：资产 `VFX_虎山神摹影` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 5（`EP02_CLIP05` · 一百年到账与收录选择 · system_panel）：资产 `VFX_道行计数overlay` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 6（`EP02_CLIP06` · 古卷收虎与道行流逝 · system_panel）：资产 `VFX_系统面板` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 6（`EP02_CLIP06` · 古卷收虎与道行流逝 · system_panel）：资产 `VFX_虎山神摹影` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 6（`EP02_CLIP06` · 古卷收虎与道行流逝 · system_panel）：资产 `VFX_道行计数overlay` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 7（`EP02_CLIP07` · 猛虎快刀圆满与状态面板 · system_panel）：资产 `VFX_系统面板` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 7（`EP02_CLIP07` · 猛虎快刀圆满与状态面板 · system_panel）：资产 `VFX_虎山神摹影` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 7（`EP02_CLIP07` · 猛虎快刀圆满与状态面板 · system_panel）：资产 `VFX_道行计数overlay` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 8（`EP02_CLIP08` · 姜月初读懂长久买卖 · reveal_reaction_chain）：资产 `VFX_残余金纹` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🔴 镜头 8（`EP02_CLIP08` · 姜月初读懂长久买卖 · reveal_reaction_chain）：资产 `VFX_系统面板` 在 asset_registry 登记了 must_not_have=['现代UI', '乱码汉字', '水印', '高饱和页游光污染']，但本镜 prompt 未继承禁项 ['现代UI', '高饱和页游光污染']；关键道具禁形必须写进负向/结构约束。
  - 🟡 资产 LOC_01：出图/共享/图片/定妆_场景_荒野尸骸战场.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 LOC_01：出图/共享/图片/定妆_场景_荒野尸骸战场.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 LOC_01：出图/共享/图片/定妆_场景_荒野尸骸战场.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 LOC_01：出图/共享/图片/定妆_场景_荒野尸骸战场.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_尸场物资包：出图/共享/图片/定妆_道具_尸场物资包.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_尸场物资包：出图/共享/图片/定妆_道具_尸场物资包_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_尸场物资包：出图/共享/图片/定妆_道具_尸场物资包_手持.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 LOC_02：出图/共享/图片/定妆_场景_荒野官道夜路.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 LOC_02：出图/共享/图片/定妆_场景_荒野官道夜路.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 LOC_02：出图/共享/图片/定妆_场景_荒野官道夜路_反打.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 LOC_02：出图/共享/图片/定妆_场景_荒野官道夜路_平面图.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 LOC_03：出图/共享/图片/定妆_场景_上盘村村口与村道.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 LOC_03：出图/共享/图片/定妆_场景_上盘村村口与村道.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 LOC_03：出图/共享/图片/定妆_场景_上盘村村口与村道_反打.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 LOC_03：出图/共享/图片/定妆_场景_上盘村村口与村道_平面图.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_镇魔司黑衣赤纹：出图/共享/图片/定妆_道具_镇魔司黑衣赤纹.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_镇魔司黑衣赤纹：出图/共享/图片/定妆_道具_镇魔司黑衣赤纹_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_镇魔司黑衣赤纹：出图/共享/图片/定妆_道具_镇魔司黑衣赤纹_手持.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 MOUNT_GROUP_01：出图/共享/图片/定妆_道具_飞鹰门马匹与火把.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 MOUNT_GROUP_01：出图/共享/图片/定妆_道具_飞鹰门马匹与火把_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 MOUNT_GROUP_01：出图/共享/图片/定妆_道具_飞鹰门马匹与火把_手持.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_上盘村断石碑：出图/共享/图片/定妆_道具_上盘村断石碑.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_上盘村断石碑：出图/共享/图片/定妆_道具_上盘村断石碑_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_上盘村断石碑：出图/共享/图片/定妆_道具_上盘村断石碑_手持.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_村道血迹破布：出图/共享/图片/定妆_道具_村道血迹破布.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_村道血迹破布：出图/共享/图片/定妆_道具_村道血迹破布_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_木架残肢剪影：出图/共享/图片/定妆_道具_木架残肢剪影.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 VFX_狼爪寒光：出图/共享/图片/定妆_特效_狼爪寒光.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。

## 降级近景人审队列（无 insightface 时人眼判同人 ①）
- 32 个近景脸需人审：开并排对比图『定妆主参考 ↔ 本镜脸』秒判同不同人
  - Clip_01（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_01_compare.png
  - Clip_01（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_01_compare.png
  - Clip_01（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_01_compare.png
  - Clip_02（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_02_compare.png
  - Clip_02（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_02_compare.png
  - Clip_02（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_02_compare.png
  - Clip_03（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_03_compare.png
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
  - Clip_08（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_08_compare.png
  - Clip_08（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_08_compare.png
  - Clip_09（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_09_compare.png
  - Clip_09（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_09_compare.png
  - Clip_09（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_09_compare.png
  - Clip_09（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_09_compare.png
  - Clip_09（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_09_compare.png
  - Clip_04（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_04_compare.png
  - Clip_04（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_04_compare.png
  - Clip_04（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_04_compare.png
  - Clip_04（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_04_compare.png
  - Clip_04（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_04_compare.png
  - Clip_06（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_06_compare.png
  - Clip_06（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_06_compare.png
  - Clip_06（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/face_review/Clip_06_compare.png

## 场景/道具/特效漂移人审队列（D）
- 1 个资产漂移镜需人审：开并排对比图『资产参考 ↔ 本镜』判是否漂
  - scene Clip_07（荒野尸骸战场）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/asset_review/scene_Clip_07_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
