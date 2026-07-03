# n2d Image QC（出图落档机检）

- episode: 第2集
- 总判定: **block** · 硬阻断 16（必须修） · 非阻断初筛 75 · 视觉降级 0
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 阶段跳转: **image** · image_qc 有硬阻断，需修复/重抽受影响镜头后重跑

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 53 张；未声明 live Clip PNG 0 张

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🟡 block 0 · warn 3
- 服装 N1: 🔴 block 1 · warn 0
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 人体解剖 N5: 🟢 block 0 · warn 0
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: 🟢 block 0 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 20 · covered 20 · missing 0 · pending 20 · precision full

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟢 已累积 4 个角色历史，暂无趋势性漂移。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 28 镜已 lint · block 0 · warn 51
  - 🟡 剧本可看性全局合同：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 1（`EP02_CLIP01` · 冷开·破盆满出碧绿灵水 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 2（`EP02_CLIP02` · 盆底一缕微光游动 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 3（`EP02_CLIP03` · 贺平生僵住 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 3（`EP02_CLIP03` · 贺平生僵住 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 4（`EP02_CLIP04` · 误判满盆绿水 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 4（`EP02_CLIP04` · 误判满盆绿水 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 5（`EP02_CLIP05` · 近看判作腐坏 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 6（`EP02_CLIP06` · 决定不用破盆盛水 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 6（`EP02_CLIP06` · 决定不用破盆盛水 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 7（`EP02_CLIP07` · 整盆灵水泼出窗外 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 7（`EP02_CLIP07` · 整盆灵水泼出窗外 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 8（`EP02_CLIP08` · 洗衣盆误用落点 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 8（`EP02_CLIP08` · 洗衣盆误用落点 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 9（`EP02_CLIP09` · 旁白确认灵水价值 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 10（`EP02_CLIP10` · 破盆被丢回墙角 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 10（`EP02_CLIP10` · 破盆被丢回墙角 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 11（`EP02_CLIP11` · 十五趟挑水压到天黑 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 11（`EP02_CLIP11` · 十五趟挑水压到天黑 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 12（`EP02_CLIP12` · 明日二十趟压力 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 12（`EP02_CLIP12` · 明日二十趟压力 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 13（`EP02_CLIP13` · 早饭场转入假关照 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 14（`EP02_CLIP14` · 张老大吩咐加肉 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 14（`EP02_CLIP14` · 张老大吩咐加肉 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 15（`EP02_CLIP15` · 贺平生懵懂道谢 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 15（`EP02_CLIP15` · 贺平生懵懂道谢 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 16（`EP02_CLIP16` · 旁白点破真剥削 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 16（`EP02_CLIP16` · 旁白点破真剥削 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 17（`EP02_CLIP17` · 夜里门板被拍响 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 17（`EP02_CLIP17` · 夜里门板被拍响 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 18（`EP02_CLIP18` · 张老大夜访寒暄 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 18（`EP02_CLIP18` · 张老大夜访寒暄 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 19（`EP02_CLIP19` · 贺平生疲惫应答 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 19（`EP02_CLIP19` · 贺平生疲惫应答 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 20（`EP02_CLIP20` · 十斤灵米施恩话术 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 20（`EP02_CLIP20` · 十斤灵米施恩话术 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 21（`EP02_CLIP21` · 贺平生问缘由 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 21（`EP02_CLIP21` · 贺平生问缘由 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 22（`EP02_CLIP22` · 张老大催找容器 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 22（`EP02_CLIP22` · 张老大催找容器 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 23（`EP02_CLIP23` · 灵米倒入破盆 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 23（`EP02_CLIP23` · 灵米倒入破盆 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 24（`EP02_CLIP24` · 贺平生识破斤两 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 24（`EP02_CLIP24` · 贺平生识破斤两 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 25（`EP02_CLIP25` · 灰败灵米揭克扣 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 26（`EP02_CLIP26` · 弱小吞下憋屈 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 镜头 26（`EP02_CLIP26` · 弱小吞下憋屈 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）
  - 🟡 镜头 27（`EP02_CLIP27` · 灰败灵米唤醒盆底微光 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 脸部锚弱信噪比 CHAR_ZHANG_LAODA/常态「基础」（出图/共享/图片/定妆_张老大.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_HAN_LAOSAN/常态「基础」（出图/共享/图片/定妆_韩老三.png）：脸占画面仅 1%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 28 · pending 16 · confirmed 12
- 确认文件: `/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_confirmations.json`
  - 🔴 Clip_01 图片/Clip01_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_01_Clip01_first_compare.png
  - 🔴 Clip_01 图片/Clip01_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_01_Clip01_first_compare.png
  - 🔴 Clip_02 图片/Clip02_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_02_Clip02_first_compare.png
  - 🔴 Clip_02 图片/Clip02_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_02_Clip02_first_compare.png
  - 🔴 Clip_03 图片/Clip03_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_03_Clip03_first_compare.png
  - 🔴 Clip_03 图片/Clip03_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_03_Clip03_first_compare.png
  - 🔴 Clip_04 图片/Clip04_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_04_Clip04_first_compare.png
  - 🔴 Clip_04 图片/Clip04_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_04_Clip04_first_compare.png
  - 🟢 Clip_05 图片/Clip05_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_05_Clip05_first_compare.png
  - 🟢 Clip_05 图片/Clip05_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_05_Clip05_first_compare.png
  - 🟢 Clip_06 图片/Clip06_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_06_Clip06_first_compare.png
  - 🟢 Clip_06 图片/Clip06_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_06_Clip06_first_compare.png
  - 🟢 Clip_07 图片/Clip07_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_07_Clip07_first_compare.png
  - 🟢 Clip_07 图片/Clip07_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_07_Clip07_first_compare.png
  - 🟢 Clip_08 图片/Clip08_first.png（PROP_GREEN_WATER 碧绿灵水） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_GREEN_WATER_Clip_08_Clip08_first_compare.png
  - 🟢 Clip_08 图片/Clip08_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_08_Clip08_first_compare.png
  - 🟢 Clip_09 图片/Clip09_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_09_Clip09_first_compare.png
  - 🟢 Clip_09 图片/Clip09_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SHUI_TONG_Clip_09_Clip09_first_compare.png
  - 🟢 Clip_10 图片/Clip10_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_10_Clip10_first_compare.png
  - 🟢 Clip_10 图片/Clip10_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SHUI_TONG_Clip_10_Clip10_first_compare.png
  - 🔴 Clip_11 图片/Clip11_first.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_11_Clip11_first_compare.png
  - 🔴 Clip_11 图片/Clip11_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SHUI_TONG_Clip_11_Clip11_first_compare.png
  - 🔴 Clip_12 图片/Clip12_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SHUI_TONG_Clip_12_Clip12_first_compare.png
  - 🔴 Clip_13 图片/Clip13_first.png（PROP_FOOD_BOWL 杂役饭碗） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_FOOD_BOWL_Clip_13_Clip13_first_compare.png
  - 🔴 Clip_13 图片/Clip13_first.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_SHUI_TONG_Clip_13_Clip13_first_compare.png
  - 🔴 Clip_14 图片/Clip14_first.png（PROP_FOOD_BOWL 杂役饭碗） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_FOOD_BOWL_Clip_14_Clip14_first_compare.png
  - 🔴 Clip_15 图片/Clip15_first.png（PROP_FOOD_BOWL 杂役饭碗） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_FOOD_BOWL_Clip_15_Clip15_first_compare.png
  - 🔴 Clip_15 图片/Clip15_first.png（PROP_WATER_JARS 两口巨大水缸） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第2集/prop_shape_review/PROP_WATER_JARS_Clip_15_Clip15_first_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
