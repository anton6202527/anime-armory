# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **block** · 硬阻断 65（必须修） · 非阻断初筛 57 · 视觉降级 3
- 机检能力: **degraded** · 当前解释器: `/opt/homebrew/opt/python@3.14/bin/python3.14`
- 阶段跳转: **image** · 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 缺失/降级: insightface/onnxruntime/buffalo_l face embedding, 人体解剖 N5, 崩脸 G1, 锚点门 N3
- 建议安装: 优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。

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
- 人体解剖 N5: ⏭ 跳过（手部畸形机检已跳过（未装 cv2）——多指/粘连暂由人逐帧放大看。）
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: ⏭ 跳过（锚点质量门已跳过（未装 insightface/cv2）——主参考是否单张清晰正脸暂由人判。）

## 角色脸定妆比对覆盖（硬闸）
- 🔴 已落档角色图 required 31 · covered 0 · missing 31 · pending 0 · precision degraded
  - 🔴 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ） 图片/Clip01_first.png：face_precision_not_full
  - 🔴 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ） 图片/Clip01_mid.png：face_precision_not_full
  - 🔴 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ） 图片/Clip01_end.png：face_precision_not_full
  - 🔴 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal） 图片/Clip02_first.png：face_precision_not_full
  - 🔴 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal） 图片/Clip02_mid.png：face_precision_not_full
  - 🔴 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal） 图片/Clip02_end.png：face_precision_not_full
  - 🔴 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse） 图片/Clip03_first.png：face_precision_not_full
  - 🔴 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse） 图片/Clip03_mid.png：face_precision_not_full
  - 🔴 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse） 图片/Clip03_end.png：face_precision_not_full
  - 🔴 镜头 4（`EP01_CLIP04` · 被迫扶裴南行 · multi_character_same_frame） 图片/Clip04_first.png：face_precision_not_full
  - 🔴 镜头 4（`EP01_CLIP04` · 被迫扶裴南行 · multi_character_same_frame） 图片/Clip04_mid.png：face_precision_not_full
  - 🔴 镜头 4（`EP01_CLIP04` · 被迫扶裴南行 · multi_character_same_frame） 图片/Clip04_end.png：face_precision_not_full
  - 🔴 镜头 5（`EP01_CLIP05` · 虎妖诈死复苏 · reveal_reaction_chain） 图片/Clip05_first.png：face_precision_not_full
  - 🔴 镜头 5（`EP01_CLIP05` · 虎妖诈死复苏 · reveal_reaction_chain） 图片/Clip05_mid.png：face_precision_not_full
  - 🔴 镜头 5（`EP01_CLIP05` · 虎妖诈死复苏 · reveal_reaction_chain） 图片/Clip05_end.png：face_precision_not_full
  - 🔴 镜头 6（`EP01_CLIP06` · 裴长青最后一击被踹飞 · fight_exchange） 图片/Clip06_first.png：face_precision_not_full
  - 🔴 镜头 6（`EP01_CLIP06` · 裴长青最后一击被踹飞 · fight_exchange） 图片/Clip06_mid.png：face_precision_not_full
  - 🔴 镜头 6（`EP01_CLIP06` · 裴长青最后一击被踹飞 · fight_exchange） 图片/Clip06_end.png：face_precision_not_full
  - 🔴 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel） 图片/Clip07_first.png：face_precision_not_full
  - 🔴 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel） 图片/Clip07_mid.png：face_precision_not_full
  - 🔴 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel） 图片/Clip07_end.png：face_precision_not_full
  - 🔴 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel） 图片/Clip08_first.png：face_precision_not_full
  - 🔴 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel） 图片/Clip08_mid.png：face_precision_not_full
  - 🔴 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel） 图片/Clip08_end.png：face_precision_not_full
  - 🔴 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse） 图片/Clip09_first.png：face_precision_not_full
  - 🔴 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse） 图片/Clip09_mid.png：face_precision_not_full
  - 🔴 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse） 图片/Clip09_end.png：face_precision_not_full
  - 🔴 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange） 图片/Clip10_first.png：face_precision_not_full
  - 🔴 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange） 图片/Clip10_mid.png：face_precision_not_full
  - 🔴 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange） 图片/Clip10_end.png：face_precision_not_full
  - 🔴 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame） 图片/Clip11_first.png：face_precision_not_full
- note: 已落档角色 PNG 存在，但 face_consistency 不是 full 精度；不能证明与定妆照同人。

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟢 已累积 2 个角色历史，暂无趋势性漂移。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 11 镜已 lint · block 0 · warn 54
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
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 降级近景人审队列（无 insightface 时人眼判同人 ①）
- 31 个近景脸需人审：开并排对比图『定妆主参考 ↔ 本镜脸』秒判同不同人
  - Clip_01（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_01_compare.png
  - Clip_01（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_01_compare.png
  - Clip_01（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_01_compare.png
  - Clip_02（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_02_compare.png
  - Clip_02（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_02_compare.png
  - Clip_02（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_02_compare.png
  - Clip_03（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_03_compare.png
  - Clip_03（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_03_compare.png
  - Clip_03（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_03_compare.png
  - Clip_05（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_05_compare.png
  - Clip_05（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_05_compare.png
  - Clip_05（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_05_compare.png
  - Clip_06（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_06_compare.png
  - Clip_06（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_06_compare.png
  - Clip_06（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_06_compare.png
  - Clip_07（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_07_compare.png
  - Clip_07（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_07_compare.png
  - Clip_07（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_07_compare.png
  - Clip_08（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_08_compare.png
  - Clip_08（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_08_compare.png
  - Clip_08（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_08_compare.png
  - Clip_09（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_09_compare.png
  - Clip_09（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_09_compare.png
  - Clip_09（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_09_compare.png
  - Clip_10（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_10_compare.png
  - Clip_10（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_10_compare.png
  - Clip_10（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_10_compare.png
  - Clip_11（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_11_compare.png
  - Clip_04（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_04_compare.png
  - Clip_04（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_04_compare.png
  - Clip_04（CHAR_01__囚犯初醒态）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/face_review/Clip_04_compare.png

## 场景/道具/特效漂移人审队列（D）
- 3 个资产漂移镜需人审：开并排对比图『资产参考 ↔ 本镜』判是否漂
  - scene Clip_07（荒野尸骸战场）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/asset_review/scene_Clip_07_compare.png
  - scene Clip_07（荒野尸骸战场）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/asset_review/scene_Clip_07_compare.png
  - scene Clip_07（荒野尸骸战场）：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/asset_review/scene_Clip_07_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
