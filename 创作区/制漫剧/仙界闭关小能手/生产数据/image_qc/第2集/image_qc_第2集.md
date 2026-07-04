# n2d Image QC（出图落档机检）

- episode: 第2集
- 总判定: **block** · 硬阻断 7（必须修） · 非阻断初筛 14 · 视觉降级 0
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 阶段跳转: **image** · image_qc 有硬阻断，需修复/重抽受影响镜头后重跑

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 53 张；未声明 live Clip PNG 0 张

## 人工逐图拒收（硬闸）
- 🔴 active rejects 2 · review `/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/human_image_review.json`
  - 🔴 图片/Clip14_end.png：style_consistency；人工复核：当前图未通过项目写实风格锚归属签收；需按写实 style_anchor 重出并复验，不得进入视频。
  - 🔴 图片/Clip15_first.png：style_consistency；人工复核：当前图未通过项目写实风格锚归属签收；需按写实 style_anchor 重出并复验，不得进入视频。

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🟡 block 0 · warn 3
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 人体解剖 N5: 🟢 block 0 · warn 0
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: 🟢 block 0 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 40 · covered 40 · missing 0 · pending 0 · precision full
- 人工脸部确认: applied 1 · 确认文件 `/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/face_confirmations.json`

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟢 已累积 4 个角色历史，暂无趋势性漂移。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 27 镜已 lint · block 0 · warn 3
  - 🟡 脸部锚弱信噪比 CHAR_ZHANG_LAODA/常态「基础」（出图/共享/图片/定妆_张老大.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_HAN_LAOSAN/常态「基础」（出图/共享/图片/定妆_韩老三.png）：脸占画面仅 1%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 49 · pending 5 · confirmed 44
- 确认文件: `/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_confirmations.json`
  - 🟢 Clip_01 图片/Clip01_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_01_Clip01_first_compare.png
  - 🟢 Clip_01 图片/Clip01_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_01_Clip01_first_compare.png
  - 🟢 Clip_02 图片/Clip02_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_02_Clip02_first_compare.png
  - 🟢 Clip_02 图片/Clip02_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_02_Clip02_first_compare.png
  - 🔴 Clip_03 图片/Clip03_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_03_Clip03_first_compare.png
  - 🔴 Clip_03 图片/Clip03_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_03_Clip03_first_compare.png
  - 🟢 Clip_04 图片/Clip04_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_04_Clip04_first_compare.png
  - 🟢 Clip_04 图片/Clip04_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_04_Clip04_first_compare.png
  - 🟢 Clip_05 图片/Clip05_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_05_Clip05_first_compare.png
  - 🟢 Clip_05 图片/Clip05_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_05_Clip05_first_compare.png
  - 🟢 Clip_06 图片/Clip06_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_06_Clip06_first_compare.png
  - 🟢 Clip_06 图片/Clip06_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_06_Clip06_first_compare.png
  - 🟢 Clip_07 图片/Clip07_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_07_Clip07_first_compare.png
  - 🟢 Clip_07 图片/Clip07_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_07_Clip07_first_compare.png
  - 🟢 Clip_08 图片/Clip08_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_08_Clip08_first_compare.png
  - 🟢 Clip_08 图片/Clip08_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_08_Clip08_first_compare.png
  - 🟢 Clip_09 图片/Clip09_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_09_Clip09_first_compare.png
  - 🟢 Clip_09 图片/Clip09_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SHUI_TONG_Clip_09_Clip09_first_compare.png
  - 🟢 Clip_10 图片/Clip10_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_10_Clip10_first_compare.png
  - 🟢 Clip_10 图片/Clip10_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SHUI_TONG_Clip_10_Clip10_first_compare.png
  - 🟢 Clip_11 图片/Clip11_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_11_Clip11_first_compare.png
  - 🟢 Clip_11 图片/Clip11_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SHUI_TONG_Clip_11_Clip11_first_compare.png
  - 🟢 Clip_12 图片/Clip12_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SHUI_TONG_Clip_12_Clip12_first_compare.png
  - 🟢 Clip_13 图片/Clip13_first.png（PROP_FOOD_BOWL 杂役饭碗） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_FOOD_BOWL_Clip_13_Clip13_first_compare.png
  - 🟢 Clip_13 图片/Clip13_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SHUI_TONG_Clip_13_Clip13_first_compare.png
  - 🔴 Clip_14 图片/Clip14_first.png（PROP_FOOD_BOWL 杂役饭碗） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_FOOD_BOWL_Clip_14_Clip14_first_compare.png
  - 🔴 Clip_15 图片/Clip15_first.png（PROP_FOOD_BOWL 杂役饭碗） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_FOOD_BOWL_Clip_15_Clip15_first_compare.png
  - 🔴 Clip_15 图片/Clip15_first.png（PROP_WATER_JARS 两口巨大水缸） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_WATER_JARS_Clip_15_Clip15_first_compare.png
  - 🟢 Clip_16 图片/Clip16_first.png（PROP_FOOD_BOWL 杂役饭碗） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_FOOD_BOWL_Clip_16_Clip16_first_compare.png
  - 🟢 Clip_16 图片/Clip16_first.png（PROP_WATER_JARS 两口巨大水缸） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_WATER_JARS_Clip_16_Clip16_first_compare.png
  - 🟢 Clip_17 图片/Clip17_first.png（PROP_WATER_JARS 两口巨大水缸） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_WATER_JARS_Clip_17_Clip17_first_compare.png
  - 🟢 Clip_19 图片/Clip19_first.png（PROP_SPIRIT_RICE_BAG 灵米布袋） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SPIRIT_RICE_BAG_Clip_19_Clip19_first_compare.png
  - 🟢 Clip_20 图片/Clip20_first.png（PROP_SPIRIT_RICE_BAG 灵米布袋） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SPIRIT_RICE_BAG_Clip_20_Clip20_first_compare.png
  - 🟢 Clip_21 图片/Clip21_first.png（PROP_SPIRIT_RICE_BAG 灵米布袋） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SPIRIT_RICE_BAG_Clip_21_Clip21_first_compare.png
  - 🟢 Clip_22 图片/Clip22_first.png（PROP_GRAY_RICE 灰败灵米） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GRAY_RICE_Clip_22_Clip22_first_compare.png
  - 🟢 Clip_22 图片/Clip22_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_22_Clip22_first_compare.png
  - 🟢 Clip_22 图片/Clip22_first.png（PROP_SPIRIT_RICE_BAG 灵米布袋） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SPIRIT_RICE_BAG_Clip_22_Clip22_first_compare.png
  - 🟢 Clip_23 图片/Clip23_first.png（PROP_GRAY_RICE 灰败灵米） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GRAY_RICE_Clip_23_Clip23_first_compare.png
  - 🟢 Clip_23 图片/Clip23_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_23_Clip23_first_compare.png
  - 🟢 Clip_23 图片/Clip23_first.png（PROP_SPIRIT_RICE_BAG 灵米布袋） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SPIRIT_RICE_BAG_Clip_23_Clip23_first_compare.png
  - 🟢 Clip_24 图片/Clip24_first.png（PROP_GRAY_RICE 灰败灵米） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GRAY_RICE_Clip_24_Clip24_first_compare.png
  - 🟢 Clip_24 图片/Clip24_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_24_Clip24_first_compare.png
  - 🟢 Clip_24 图片/Clip24_first.png（PROP_SPIRIT_RICE_BAG 灵米布袋） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SPIRIT_RICE_BAG_Clip_24_Clip24_first_compare.png
  - 🟢 Clip_25 图片/Clip25_first.png（PROP_GRAY_RICE 灰败灵米） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GRAY_RICE_Clip_25_Clip25_first_compare.png
  - 🟢 Clip_25 图片/Clip25_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_25_Clip25_first_compare.png
  - 🟢 Clip_26 图片/Clip26_first.png（PROP_GRAY_RICE 灰败灵米） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GRAY_RICE_Clip_26_Clip26_first_compare.png
  - 🟢 Clip_26 图片/Clip26_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_26_Clip26_first_compare.png
  - 🟢 Clip_27 图片/Clip27_first.png（PROP_GRAY_RICE 灰败灵米） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GRAY_RICE_Clip_27_Clip27_first_compare.png
  - 🟢 Clip_27 图片/Clip27_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_27_Clip27_first_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
