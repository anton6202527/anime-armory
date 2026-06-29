# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **block** · 硬阻断 9（必须修） · 非阻断初筛 17 · 视觉降级 0
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 阶段跳转: **image** · image_qc 有硬阻断，需修复/重抽受影响镜头后重跑

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🔴 block 1 · warn 1
- 发型 H1: 🔴 block 1 · warn 0
- 服装 N1: 🔴 block 1 · warn 2
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: 🔴 block 1 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🔴 已落档角色图 required 12 · covered 10 · missing 2 · pending 3 · precision full
  - 🔴 Clip 04 两缸水和空屋 图片/Clip04_两缸水和空屋.png：face_verdict_warn
  - 🔴 Clip 04 两缸水和空屋 图片/Clip04_两缸水和空屋_end.png：face_verdict_noface
  - 🟡 漏分类有脸镜 Clip_02 图片/Clip02_挑水命令.png：未在 character_shots 清单，待人工确认是否角色镜（非阻断）

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟢 已累积 1 个角色历史，暂无趋势性漂移。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 8 镜已 lint · block 0 · warn 9
  - 🟡 脸部锚弱信噪比 CHAR_JIANG_JIAN/背影「侧背锚」（出图/共享/图片/定妆_江剑_背影_侧背.png）：脸占画面仅 3%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_JIANG_JIAN/背影「侧背锚」（出图/共享/图片/定妆_江剑_背影_侧背.png）：脸占画面仅 3%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_TAIXUMEN_ZHANGLAO/回忆背影「背影锚」（出图/共享/图片/定妆_太虚门长老_回忆背影_侧背.png）：脸占画面仅 7%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_TAIXUMEN_ZHANGLAO/回忆背影「背影锚」（出图/共享/图片/定妆_太虚门长老_回忆背影_侧背.png）：脸占画面仅 7%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_HE_SANJIE/回忆影「回忆侧影锚」（出图/共享/图片/定妆_贺三杰_回忆影_侧影.png）：脸占画面仅 5%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_HE_SANJIE/回忆影「回忆侧影锚」（出图/共享/图片/定妆_贺三杰_回忆影_侧影.png）：脸占画面仅 5%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CROWD_ZAYI/虚化「群像虚化锚」（出图/共享/图片/定妆_群杂役_虚化_群像sheet.png）：脸占画面仅 7%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CROWD_ZAYI/虚化「群像虚化锚」（出图/共享/图片/定妆_群杂役_虚化_群像sheet.png）：脸占画面仅 7%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 6 · pending 6 · confirmed 0
- 确认文件: `/Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_confirmations.json`
  - 🔴 Clip_04 图片/Clip04_两缸水和空屋.png（PROP_KEY_LOCK 旧钥匙与生锈铁锁） 禁形=现代防盗锁、金色宝物、符文刻字、巨大链锁、多套重复；尺寸=少年单手可握，锁体小，适合低矮旧房木门。；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_KEY_LOCK_Clip_04_Clip04_两缸水和空屋_compare.png
  - 🔴 Clip_04 图片/Clip04_两缸水和空屋.png（PROP_TIE_WAN 铁碗/钥匙铁锁） 禁形=现代锁具、金色宝物、瓷碗、异物化、多套重复；尺寸=铁碗可手持，钥匙铁锁为小型杂役房门物件。；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_TIE_WAN_Clip_04_Clip04_两缸水和空屋_compare.png
  - 🔴 Clip_05 图片/Clip05_夜挑五趟.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代塑料桶、金属水桶、单只桶漂移、华丽异物化；尺寸=少年挑水工具，桶身到少年膝上附近。；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_SHUI_TONG_Clip_05_Clip05_夜挑五趟_compare.png
  - 🔴 Clip_06 图片/Clip06_水底破盆.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=强光柱、金边、符文文字、玉石质感、现代塑料盆、多盆重复；尺寸=普通脸盆大小，可被十四岁少年夹在臂弯。；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_06_Clip06_水底破盆_compare.png
  - 🔴 Clip_06 图片/Clip06_水底破盆.png（PROP_SHUI_TONG 水桶与扁担） 禁形=现代塑料桶、金属水桶、单只桶漂移、华丽异物化；尺寸=少年挑水工具，桶身到少年膝上附近。；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_SHUI_TONG_Clip_06_Clip06_水底破盆_compare.png
  - 🔴 Clip_07 图片/Clip07_盆底微光.png（PROP_HEI_TAO_PEN 黑陶破盆） 禁形=强光柱、金边、符文文字、玉石质感、现代塑料盆、多盆重复；尺寸=普通脸盆大小，可被十四岁少年夹在臂弯。；/Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/prop_shape_review/PROP_HEI_TAO_PEN_Clip_07_Clip07_盆底微光_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/纯文生图/非法 CHAR_id），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
