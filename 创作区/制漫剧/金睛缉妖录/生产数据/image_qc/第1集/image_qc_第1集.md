# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **block** · 硬阻断 52（必须修） · 非阻断初筛 28 · 视觉降级 3
- 机检能力: **degraded** · 当前解释器: `/Applications/Xcode.app/Contents/Developer/usr/bin/python3`
- 阶段跳转: **image** · 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 缺失/降级: insightface/onnxruntime/buffalo_l face embedding, 崩脸 G1, 接缝接力, 锚点门 N3
- 建议安装: 优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🔴 block 36 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 接缝接力: ⏭ 跳过（无 /Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/出图/第1集/图片——出图后再跑接缝机检。）
- 锚点门 N3: ⏭ 跳过（锚点质量门已跳过（未装 insightface/cv2）——主参考是否单张清晰正脸暂由人判。）

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 0 · covered 0 · missing 0 · pending 36 · precision degraded

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 12 镜已 lint · block 0 · warn 28
  - 🟡 镜头 1（`EP01_CLIP01` · 死人喝茶冷开 · evidence_search）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 2（`EP01_CLIP02` · 画押与拒押 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 3（`EP01_CLIP03` · 证据四连 · evidence_search）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 4（`EP01_CLIP04` · 鞋证逼问 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 5（`EP01_CLIP05` · 陈妻压情绪与旧铜发烫 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 6（`EP01_CLIP06` · 金睛开眼 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 7（`EP01_CLIP07` · 妖识金睛 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 8（`EP01_CLIP08` · 当众揭穿 · public_confrontation）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 9（`EP01_CLIP09` · 妖以家人为筹码 · public_confrontation）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 10（`EP01_CLIP10` · 妖影暴起 · fight_exchange）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 11（`EP01_CLIP11` · 符火钉妖 · magic_burst）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 12（`EP01_CLIP12` · 他当年也有 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 资产 PROP_BLOOD_THRESHOLD：出图/共享/图片/定妆_道具_门槛血迹.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_BLOOD_THRESHOLD：出图/共享/图片/定妆_道具_门槛血迹_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_BLOOD_THRESHOLD：出图/共享/图片/定妆_道具_门槛血迹_手持.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_MUD_FOOTPRINT：出图/共享/图片/定妆_道具_泥脚印.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_MUD_FOOTPRINT：出图/共享/图片/定妆_道具_泥脚印_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_MUD_FOOTPRINT：出图/共享/图片/定妆_道具_泥脚印_手持.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_CLEAN_BLACK_BOOT：出图/共享/图片/定妆_道具_干净皂靴.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_CLEAN_BLACK_BOOT：出图/共享/图片/定妆_道具_干净皂靴_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_CLEAN_BLACK_BOOT：出图/共享/图片/定妆_道具_干净皂靴_手持.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_STILL_TEA：出图/共享/图片/定妆_道具_不动热茶.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_STILL_TEA：出图/共享/图片/定妆_道具_不动热茶_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_STILL_TEA：出图/共享/图片/定妆_道具_不动热茶_手持.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_OLD_COPPER_HALF：出图/共享/图片/定妆_道具_半片旧铜.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_OLD_COPPER_HALF：出图/共享/图片/定妆_道具_半片旧铜_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 资产 PROP_OLD_COPPER_HALF：出图/共享/图片/定妆_道具_半片旧铜_手持.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 16 · pending 16 · confirmed 0
- 确认文件: `/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_confirmations.json`
  - 🔴 Clip_01 图片/Clip01_first.png（PROP_BLOOD_THRESHOLD 门槛半干血迹） 禁形=器官、大面积血泊；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_BLOOD_THRESHOLD_Clip_01_Clip01_first_compare.png
  - 🔴 Clip_01 图片/Clip01_first.png（PROP_STILL_TEA 不动热茶） 禁形=现代杯柄、文字茶杯；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_STILL_TEA_Clip_01_Clip01_first_compare.png
  - 🔴 Clip_02 图片/Clip02_first.png（PROP_BLOOD_THRESHOLD 门槛半干血迹） 禁形=器官、大面积血泊；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_BLOOD_THRESHOLD_Clip_02_Clip02_first_compare.png
  - 🔴 Clip_02 图片/Clip02_first.png（PROP_MUD_FOOTPRINT 雨水泥脚印） 禁形=发光边、现代箭头；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_MUD_FOOTPRINT_Clip_02_Clip02_first_compare.png
  - 🔴 Clip_03 图片/Clip03_first.png（PROP_BLOOD_THRESHOLD 门槛半干血迹） 禁形=器官、大面积血泊；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_BLOOD_THRESHOLD_Clip_03_Clip03_first_compare.png
  - 🔴 Clip_03 图片/Clip03_first.png（PROP_CLEAN_BLACK_BOOT 干净皂靴） 禁形=现代鞋底、运动鞋纹；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_CLEAN_BLACK_BOOT_Clip_03_Clip03_first_compare.png
  - 🔴 Clip_03 图片/Clip03_first.png（PROP_MUD_FOOTPRINT 雨水泥脚印） 禁形=发光边、现代箭头；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_MUD_FOOTPRINT_Clip_03_Clip03_first_compare.png
  - 🔴 Clip_03 图片/Clip03_first.png（PROP_STILL_TEA 不动热茶） 禁形=现代杯柄、文字茶杯；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_STILL_TEA_Clip_03_Clip03_first_compare.png
  - 🔴 Clip_04 图片/Clip04_first.png（PROP_CLEAN_BLACK_BOOT 干净皂靴） 禁形=现代鞋底、运动鞋纹；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_CLEAN_BLACK_BOOT_Clip_04_Clip04_first_compare.png
  - 🔴 Clip_04 图片/Clip04_first.png（PROP_MUD_FOOTPRINT 雨水泥脚印） 禁形=发光边、现代箭头；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_MUD_FOOTPRINT_Clip_04_Clip04_first_compare.png
  - 🔴 Clip_04 图片/Clip04_first.png（PROP_STILL_TEA 不动热茶） 禁形=现代杯柄、文字茶杯；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_STILL_TEA_Clip_04_Clip04_first_compare.png
  - 🔴 Clip_05 图片/Clip05_first.png（PROP_OLD_COPPER_HALF 半片旧铜） 禁形=现代硬币、长铭文；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_OLD_COPPER_HALF_Clip_05_Clip05_first_compare.png
  - 🔴 Clip_07 图片/Clip07_first.png（PROP_STILL_TEA 不动热茶） 禁形=现代杯柄、文字茶杯；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_STILL_TEA_Clip_07_Clip07_first_compare.png
  - 🔴 Clip_08 图片/Clip08_first.png（PROP_BLOOD_THRESHOLD 门槛半干血迹） 禁形=器官、大面积血泊；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_BLOOD_THRESHOLD_Clip_08_Clip08_first_compare.png
  - 🔴 Clip_08 图片/Clip08_first.png（PROP_CLEAN_BLACK_BOOT 干净皂靴） 禁形=现代鞋底、运动鞋纹；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_CLEAN_BLACK_BOOT_Clip_08_Clip08_first_compare.png
  - 🔴 Clip_08 图片/Clip08_first.png（PROP_STILL_TEA 不动热茶） 禁形=现代杯柄、文字茶杯；尺寸=None；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/image_qc/第1集/prop_shape_review/PROP_STILL_TEA_Clip_08_Clip08_first_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/纯文生图/非法 CHAR_id），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
