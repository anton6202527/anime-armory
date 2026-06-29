# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **block** · 硬阻断 12（必须修） · 非阻断初筛 4 · 视觉降级 1
- 机检能力: **degraded** · 当前解释器: `/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 阶段跳转: **image** · 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 缺失/降级: 接缝接力
- 建议安装: 优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 接缝接力: ⏭ 跳过（不可用）
- 锚点门 N3: 🟢 block 0 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 0 · covered 0 · missing 0 · pending 0 · precision full

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🔴 8 镜已 lint · block 6 · warn 4
  - 🟡 Clip_01 黑殿审问 🔑前3秒冲突：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 Clip_01 黑殿审问 🔑前3秒冲突：本镜含清晰正脸肖像倾向却无视线防呆句——除非是 POV/对观众特写，角色不应正对镜头摆拍/对视；改可辨侧脸/过肩/三分之二，视线锁场内目标（对手/对话对象/所视之物）。
  - 🔴 Clip_04 两缸水和空屋：资产 `PROP_KEY_LOCK` 在 asset_registry 登记了 must_not_have=['现代防盗锁', '金色宝物', '法器符文', '巨大链锁', '多套重复']，但本镜 prompt 未继承禁项 ['现代防盗锁', '金色宝物', '法器符文', '巨大链锁', '多套重复']；关键道具禁形必须写进负向/结构约束。
  - 🔴 Clip_04 两缸水和空屋：资产 `PROP_TIE_WAN` 在 asset_registry 登记了 must_not_have=['现代锁具', '金色宝物', '瓷碗', '多套重复']，但本镜 prompt 未继承禁项 ['现代锁具', '金色宝物', '瓷碗', '多套重复']；关键道具禁形必须写进负向/结构约束。
  - 🔴 Clip_05 夜挑五趟：资产 `PROP_SHUI_TONG` 在 asset_registry 登记了 must_not_have=['现代塑料桶', '金属水桶', '单只桶漂移', '华丽法器化']，但本镜 prompt 未继承禁项 ['现代塑料桶', '金属水桶', '单只桶漂移', '华丽法器化']；关键道具禁形必须写进负向/结构约束。
  - 🔴 Clip_06 水底破盆 🔑核心机缘：资产 `PROP_HEI_TAO_PEN` 在 asset_registry 登记了 must_not_have=['强光柱', '金边', '符文文字', '玉石质感', '现代塑料盆', '多盆重复']，但本镜 prompt 未继承禁项 ['强光柱', '符文文字', '玉石质感', '现代塑料盆', '多盆重复']；关键道具禁形必须写进负向/结构约束。
  - 🔴 Clip_06 水底破盆 🔑核心机缘：资产 `PROP_SHUI_TONG` 在 asset_registry 登记了 must_not_have=['现代塑料桶', '金属水桶', '单只桶漂移', '华丽法器化']，但本镜 prompt 未继承禁项 ['现代塑料桶', '金属水桶', '单只桶漂移', '华丽法器化']；关键道具禁形必须写进负向/结构约束。
  - 🔴 Clip_07 盆底微光 🔑集尾硬断：资产 `PROP_HEI_TAO_PEN` 在 asset_registry 登记了 must_not_have=['强光柱', '金边', '符文文字', '玉石质感', '现代塑料盆', '多盆重复']，但本镜 prompt 未继承禁项 ['玉石质感', '多盆重复']；关键道具禁形必须写进负向/结构约束。
  - 🟡 Clip_07 盆底微光 🔑集尾硬断：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。
  - 🟡 Clip_07 盆底微光 🔑集尾硬断：本镜含清晰正脸肖像倾向却无视线防呆句——除非是 POV/对观众特写，角色不应正对镜头摆拍/对视；改可辨侧脸/过肩/三分之二，视线锁场内目标（对手/对话对象/所视之物）。

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 6 · pending 6 · confirmed 0
- 确认文件: `/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_confirmations.json`
  - 🔴 Clip_04 图片/Clip04_两缸水和空屋.png（PROP_KEY_LOCK 旧钥匙与生锈铁锁） 禁形=现代防盗锁、金色宝物、法器符文、巨大链锁、多套重复；尺寸=少年单手可握，锁体小，适合低矮旧房木门。；/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_KEY_LOCK_Clip_04_Clip04_两缸水和空屋_compare.png
  - 🔴 Clip_04 图片/Clip04_两缸水和空屋.png（PROP_TIE_WAN 铁碗/钥匙铁锁） 禁形=现代锁具、金色宝物、瓷碗、多套重复；尺寸=铁碗可手持，钥匙铁锁为小型杂役房门物件。；/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_TIE_WAN_Clip_04_Clip04_两缸水和空屋_compare.png
  - 🔴 Clip_05 图片/Clip05_夜挑五趟.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代塑料桶、金属水桶、单只桶漂移、华丽法器化；尺寸=少年挑水工具，桶身到少年膝上附近。；/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_SHUI_TONG_Clip_05_Clip05_夜挑五趟_compare.png
  - 🔴 Clip_06 图片/Clip06_水底破盆.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=强光柱、金边、符文文字、玉石质感、现代塑料盆、多盆重复；尺寸=普通脸盆大小，可被十四岁少年夹在臂弯。；/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_06_Clip06_水底破盆_compare.png
  - 🔴 Clip_06 图片/Clip06_水底破盆.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代塑料桶、金属水桶、单只桶漂移、华丽法器化；尺寸=少年挑水工具，桶身到少年膝上附近。；/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_SHUI_TONG_Clip_06_Clip06_水底破盆_compare.png
  - 🔴 Clip_07 图片/Clip07_盆底微光.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=强光柱、金边、符文文字、玉石质感、现代塑料盆、多盆重复；尺寸=普通脸盆大小，可被十四岁少年夹在臂弯。；/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_07_Clip07_盆底微光_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/纯文生图/非法 CHAR_id），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
