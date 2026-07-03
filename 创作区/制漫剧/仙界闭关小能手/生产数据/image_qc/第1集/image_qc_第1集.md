# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **review** · 硬阻断 0（必须修） · 非阻断初筛 103 · 视觉降级 0
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 阶段跳转: **video** · full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 74 张；未声明 live Clip PNG 0 张

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🔴 block 2 · warn 5
- 服装 N1: 🔴 block 5 · warn 3
- 场景 O2: 🟡 block 0 · warn 1
- 道具/特效 P2: 🟢 block 0 · warn 0
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: 🟢 block 0 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 69 · covered 69 · missing 0 · pending 0 · precision full
- 人工脸部确认: applied 11 · 确认文件 `/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/face_confirmations.json`

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟢 已累积 4 个角色历史，暂无趋势性漂移。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 25 镜已 lint · block 0 · warn 28
  - 🟡 镜头 1（`EP01_CLIP01` · 黑殿全景慢推 · ensemble_blocking）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 2（`EP01_CLIP02` · 张老大问年龄 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 3（`EP01_CLIP03` · 贺平生答十四岁 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 4（`EP01_CLIP04` · 张老大问灵根 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 5（`EP01_CLIP05` · 贺平生答五行灵根 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 6（`EP01_CLIP06` · 群杂役笑影压近 · ensemble_blocking）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 7（`EP01_CLIP07` · 五行光点被压灭 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 8（`EP01_CLIP08` · 外门长老转身离开 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 9（`EP01_CLIP09` · 张老大拍肩落命令 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 10（`EP01_CLIP10` · 贺平生低头应是 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 11（`EP01_CLIP11` · 父母亡故资源被抢 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 12（`EP01_CLIP12` · 江剑背影送往秀竹峰 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 13（`EP01_CLIP13` · 选择留下望向仙途 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 14（`EP01_CLIP14` · 韩老三指两口水缸 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 15（`EP01_CLIP15` · 贺平生仰看水缸 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 16（`EP01_CLIP16` · 韩老三交钥匙铁索 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 17（`EP01_CLIP17` · 空屋硬板床铁碗 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 18（`EP01_CLIP18` · 门口自语先认路 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 19（`EP01_CLIP19` · 挑水动作蒙太奇 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 20（`EP01_CLIP20` · 第五次水边微光 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 21（`EP01_CLIP21` · 贺平生屏息停住 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 22（`EP01_CLIP22` · 水下黑陶破盆特写 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 23（`EP01_CLIP23` · 捞起破盆误判普通 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 24（`EP01_CLIP24` · 夹破盆转身能用 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 25（`EP01_CLIP25` · 盆底微光硬断 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 脸部锚弱信噪比 CHAR_ZHANG_LAODA/常态「基础」（出图/共享/图片/定妆_张老大.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_HAN_LAOSAN/常态「基础」（出图/共享/图片/定妆_韩老三.png）：脸占画面仅 1%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 场景/道具/特效漂移人审队列（D）
- 1 个资产漂移镜需人审：开并排对比图『资产参考 ↔ 本镜』判是否漂
  - scene Clip_07（秀竹峰杂役大殿.png）：/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/asset_review/scene_Clip_07_compare.png

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 20 · pending 0 · confirmed 20
- 确认文件: `/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_confirmations.json`
  - 🟢 Clip_11 图片/Clip11_first.png（PROP_XIUZHEN_ZIYUAN 修真资源包） 禁形=现代物件、文字水印、结构漂移、数量漂移、壶嘴、侧嘴、斜嘴、喷口；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_XIUZHEN_ZIYUAN_Clip_11_Clip11_first_compare.png
  - 🟢 Clip_14 图片/Clip14_first.png（PROP_WATER_JARS 两口巨大水缸） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_WATER_JARS_Clip_14_Clip14_first_compare.png
  - 🟢 Clip_15 图片/Clip15_first.png（PROP_WATER_JARS 两口巨大水缸） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_WATER_JARS_Clip_15_Clip15_first_compare.png
  - 🟢 Clip_16 图片/Clip16_first.png（PROP_KEY_LOCK 旧钥匙与生锈铁锁） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_KEY_LOCK_Clip_16_Clip16_first_compare.png
  - 🟢 Clip_17 图片/Clip17_first.png（PROP_KEY_LOCK 旧钥匙与生锈铁锁） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_KEY_LOCK_Clip_17_Clip17_first_compare.png
  - 🟢 Clip_17 图片/Clip17_first.png（PROP_TIE_WAN 铁碗钥匙铁锁） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_TIE_WAN_Clip_17_Clip17_first_compare.png
  - 🟢 Clip_18 图片/Clip18_first.png（PROP_KEY_LOCK 旧钥匙与生锈铁锁） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_KEY_LOCK_Clip_18_Clip18_first_compare.png
  - 🟢 Clip_18 图片/Clip18_first.png（PROP_TIE_WAN 铁碗钥匙铁锁） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_TIE_WAN_Clip_18_Clip18_first_compare.png
  - 🟢 Clip_19 图片/Clip19_first.png（PROP_BIAN_DAN 粗木扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_BIAN_DAN_Clip_19_Clip19_first_compare.png
  - 🟢 Clip_19 图片/Clip19_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_SHUI_TONG_Clip_19_Clip19_first_compare.png
  - 🟢 Clip_20 图片/Clip20_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_20_Clip20_first_compare.png
  - 🟢 Clip_20 图片/Clip20_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_SHUI_TONG_Clip_20_Clip20_first_compare.png
  - 🟢 Clip_21 图片/Clip21_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_SHUI_TONG_Clip_21_Clip21_first_compare.png
  - 🟢 Clip_22 图片/Clip22_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_22_Clip22_first_compare.png
  - 🟢 Clip_23 图片/Clip23_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_23_Clip23_first_compare.png
  - 🟢 Clip_23 图片/Clip23_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_SHUI_TONG_Clip_23_Clip23_first_compare.png
  - 🟢 Clip_24 图片/Clip24_first.png（PROP_BIAN_DAN 粗木扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_BIAN_DAN_Clip_24_Clip24_first_compare.png
  - 🟢 Clip_24 图片/Clip24_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_24_Clip24_first_compare.png
  - 🟢 Clip_24 图片/Clip24_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_SHUI_TONG_Clip_24_Clip24_first_compare.png
  - 🟢 Clip_25 图片/Clip25_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_25_Clip25_first_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/纯文生图/非法 CHAR_id），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
