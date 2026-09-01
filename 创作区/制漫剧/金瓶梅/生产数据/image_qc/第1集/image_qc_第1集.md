# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **review** · 硬阻断 0（必须修） · 非阻断初筛 38 · 视觉降级 0
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 阶段跳转: **video** · full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 59 张；未声明 live Clip PNG 0 张

## 人工逐图拒收（硬闸）
- 🟢 active rejects 0 · review `/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/human_image_review.json`

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🟡 block 0 · warn 6
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟡 block 0 · warn 1
- 道具/特效 P2: 🟢 block 0 · warn 0
- 人体解剖 N5: 🟢 block 0 · warn 0
- 接缝接力: 🟢 block 0 · warn 0
- 锚点门 N3: 🟢 block 0 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 15 · covered 15 · missing 0 · pending 36 · precision full
  - 🟡 漏分类有脸镜 Clip_01 图片/Clip01_end.png：未在 character_shots 清单，待人工确认是否角色镜（非阻断）
  - 🟡 漏分类有脸镜 Clip_02 图片/Clip02_end.png：未在 character_shots 清单，待人工确认是否角色镜（非阻断）
- 人工脸部确认: applied 11 · 确认文件 `/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/face_confirmations.json`

## 核心角色五角 turnaround（逐视图 hash 收据硬闸）
- 🟢 checked forms 7 · pending/stale receipts 0 · contract `front/three_quarter/side/rear_three_quarter/back`
- 像素头顶/脚底/中心线/身高与脸框只作 WARN 级可复算证据；硬条件仅是当前 PNG 的逐视图 pass 收据。

## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）
- 🟢 已累积 3 个角色历史，暂无趋势性漂移。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 15 镜已 lint · block 0 · warn 8
  - 🟡 脸部锚弱信噪比 CHAR_WUDA/日常卖饼态「克制」（出图/共享/图片/定妆_CHAR_WUDA__日常卖饼态_表情_克制.png）：脸占画面仅 4%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_MAGISTRATE/常态「face_anchor」（出图/共享/图片/定妆_CHAR_MAGISTRATE__常态_脸部特写_脸锚裁切.png）：脸占画面仅 4%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 脸部锚弱信噪比 CHAR_XIMENQING/常态「face_anchor」（出图/共享/图片/定妆_CHAR_XIMENQING__常态_脸部特写_脸锚裁切.png）：脸占画面仅 4%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - 🟡 多视图对齐初筛异常 CHAR_WUSONG/28岁打虎态：视平线不齐：three_quarter(0.16) vs back(0.68)，跨视图脸中心高度差 52%>6%——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 多视图对齐初筛异常 BEAST_TIGER/常态：头顶线不齐：rear_three_quarter(0.047) vs side(0.114)，差 0.067>0.045；脚底线不齐：side(0.917) vs front(0.953)，差 0.036>0.035；身体中心线不齐：rear_three_quarter(0.471) vs front(0.546)，差 0.075>0.055；全身高度不一：rear_three_quarter 是 side 的 1.104 倍（>1.1）；视平线不齐：front(0.33) vs three_quarter(0.70)，跨视图脸中心高度差 37%>6%；比例不一：front 脸高是 three_quarter 的 7.95 倍（>1.35），不是同距离同景别的定妆板——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 多视图对齐初筛异常 CHAR_WUDA/日常卖饼态：视平线不齐：front(0.53) vs three_quarter(0.82)，跨视图脸中心高度差 29%>6%；比例不一：three_quarter 脸高是 side 的 3.89 倍（>1.35），不是同距离同景别的定妆板——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 多视图对齐初筛异常 CHAR_MAGISTRATE/常态：视平线不齐：three_quarter(0.15) vs side(0.78)，跨视图脸中心高度差 63%>6%；比例不一：front 脸高是 side 的 4.04 倍（>1.35），不是同距离同景别的定妆板——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。
  - 🟡 VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。

## 场景/道具/特效漂移人审队列（D）
- 1 个资产漂移镜需人审：开并排对比图『资产参考 ↔ 本镜』判是否漂
  - scene Clip_03（景阳冈夜间空地）：/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/asset_review/scene_Clip_03_compare.png

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 53 · pending 0 · confirmed 53
- 确认文件: `/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_confirmations.json`
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_都头腰牌.png（PROP_BADGE 都头腰牌） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约一掌高（12至16厘米），宽度略窄于成年男子手掌；可单手完整握持。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_BADGE_shared_primary_定妆_道具_都头腰牌_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_炭盆.png（PROP_BRAZIER 炭盆） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_BRAZIER_shared_primary_定妆_道具_炭盆_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_炊饼担.png（PROP_CAKE_POLE 炊饼担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_CAKE_POLE_shared_primary_定妆_道具_炊饼担_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_叉竿.png（PROP_CURTAIN_FORK 叉竿） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_CURTAIN_FORK_shared_primary_定妆_道具_叉竿_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_DINING_TABLE.png（PROP_DINING_TABLE DINING TABLE） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约长 120–140 厘米、宽 60–75 厘米、高 70–75 厘米；坐下时桌沿在腰上，两人对坐后中间仍有放置茶盏的空间。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_DINING_TABLE_shared_primary_定妆_道具_DINING_TABLE_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_武大家木门.png（PROP_DOOR 武大家木门） 禁形=现代物件、文字水印、结构漂移、数量漂移、现代防盗门、现代门锁、无来源文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_DOOR_shared_primary_定妆_道具_武大家木门_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_DOORFRAME.png（PROP_DOORFRAME DOORFRAME） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=净宽约 75–85 厘米，净高约 180–190 厘米；成年人单人通行，横楣略高于头顶，门槛低于脚踝。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_DOORFRAME_shared_primary_定妆_道具_DOORFRAME_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_门闩.png（PROP_DOOR_LATCH 门闩） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=木闩长约 75–90 厘米，截面约 5–7 厘米方，安装在成人腰部至腹部高度，可单手包握并水平推动。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_DOOR_LATCH_shared_primary_定妆_道具_门闩_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_东京礼担.png（PROP_GIFT_LOAD 东京礼担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_GIFT_LOAD_shared_primary_定妆_道具_东京礼担_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_素布行李.png（PROP_LUGGAGE 素布行李） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_LUGGAGE_shared_primary_定妆_道具_素布行李_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_公文.png（PROP_OFFICIAL_DOC 公文） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_OFFICIAL_DOC_shared_primary_定妆_道具_公文_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_梢棒.png（PROP_QUARTERSTAFF 梢棒） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_QUARTERSTAFF_shared_primary_定妆_道具_梢棒_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_REWARD_SILVER.png（PROP_REWARD_SILVER REWARD SILVER） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=单枚约成年男子掌心大小，可一手托住；不得大于整只手掌或小成硬币。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_REWARD_SILVER_shared_primary_定妆_道具_REWARD_SILVER_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_SPILLED_WINE.png（PROP_SPILLED_WINE SPILLED WINE） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_SPILLED_WINE_shared_primary_定妆_道具_SPILLED_WINE_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_STAIR_RAIL.png（PROP_STAIR_RAIL STAIR RAIL） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=扶手顶面距踏步前缘约 85–95 厘米，为成年人腰部高度；一手可自然包握，直棂间距均匀。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_STAIR_RAIL_shared_primary_定妆_道具_STAIR_RAIL_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_TEA_CUP.png（PROP_TEA_CUP TEA CUP） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=口径约 8–10 厘米，高约 5–7 厘米，可一手托住或以拇指与其余手指环持，整体明显小于成人掌宽。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_TEA_CUP_shared_primary_定妆_道具_TEA_CUP_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_WINDOW_CURTAIN.png（PROP_WINDOW_CURTAIN WINDOW CURTAIN） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_WINDOW_CURTAIN_shared_primary_定妆_道具_WINDOW_CURTAIN_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_WINDOW_LATTICE.png（PROP_WINDOW_LATTICE WINDOW LATTICE） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=窗框约高 110–130 厘米、宽 55–70 厘米；窗台约在成年人腰至胸下，人站立可单手推开窗扇。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_WINDOW_LATTICE_shared_primary_定妆_道具_WINDOW_LATTICE_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_半杯酒.png（PROP_WINE_CUP 半杯酒） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_WINE_CUP_shared_primary_定妆_道具_半杯酒_compare.png
  - 🟢 Clip_02 图片/Clip02_end.png（PROP_QUARTERSTAFF 梢棒） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_QUARTERSTAFF_Clip_02_Clip02_end_compare.png
  - 🟢 Clip_02 图片/Clip02_first.png（PROP_QUARTERSTAFF 梢棒） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_QUARTERSTAFF_Clip_02_Clip02_first_compare.png
  - 🟢 Clip_02 图片/EP01_CLIP02_a1.png（PROP_QUARTERSTAFF 梢棒） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_QUARTERSTAFF_Clip_02_EP01_CLIP02_a1_compare.png
  - 🟢 Clip_02 图片/EP01_CLIP02_a2.png（PROP_QUARTERSTAFF 梢棒） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_QUARTERSTAFF_Clip_02_EP01_CLIP02_a2_compare.png
  - 🟢 Clip_02 图片/EP01_CLIP02_a3.png（PROP_QUARTERSTAFF 梢棒） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_QUARTERSTAFF_Clip_02_EP01_CLIP02_a3_compare.png
  - 🟢 Clip_03 图片/EP01_CLIP03_a1.png（PROP_BADGE 都头腰牌） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约一掌高（12至16厘米），宽度略窄于成年男子手掌；可单手完整握持。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_BADGE_Clip_03_EP01_CLIP03_a1_compare.png
  - 🟢 Clip_03 图片/EP01_CLIP03_a2.png（PROP_BADGE 都头腰牌） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约一掌高（12至16厘米），宽度略窄于成年男子手掌；可单手完整握持。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_BADGE_Clip_03_EP01_CLIP03_a2_compare.png
  - 🟢 Clip_03 图片/EP01_CLIP03_a3.png（PROP_BADGE 都头腰牌） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约一掌高（12至16厘米），宽度略窄于成年男子手掌；可单手完整握持。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_BADGE_Clip_03_EP01_CLIP03_a3_compare.png
  - 🟢 Clip_03 图片/EP01_CLIP03_a1.png（PROP_QUARTERSTAFF 梢棒） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_QUARTERSTAFF_Clip_03_EP01_CLIP03_a1_compare.png
  - 🟢 Clip_03 图片/EP01_CLIP03_a1.png（PROP_REWARD_SILVER REWARD SILVER） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=单枚约成年男子掌心大小，可一手托住；不得大于整只手掌或小成硬币。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_REWARD_SILVER_Clip_03_EP01_CLIP03_a1_compare.png
  - 🟢 Clip_04 图片/Clip04_first.png（PROP_CAKE_POLE 炊饼担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_CAKE_POLE_Clip_04_Clip04_first_compare.png
  - 🟢 Clip_04 图片/EP01_CLIP04_a1.png（PROP_WINDOW_LATTICE WINDOW LATTICE） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=窗框约高 110–130 厘米、宽 55–70 厘米；窗台约在成年人腰至胸下，人站立可单手推开窗扇。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_WINDOW_LATTICE_Clip_04_EP01_CLIP04_a1_compare.png
  - 🟢 Clip_05 图片/Clip05_end.png（PROP_BADGE 都头腰牌） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约一掌高（12至16厘米），宽度略窄于成年男子手掌；可单手完整握持。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_BADGE_Clip_05_Clip05_end_compare.png
  - 🟢 Clip_05 图片/Clip05_first_a3.png（PROP_BADGE 都头腰牌） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约一掌高（12至16厘米），宽度略窄于成年男子手掌；可单手完整握持。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_BADGE_Clip_05_Clip05_first_a3_compare.png
  - 🟢 Clip_05 图片/EP01_CLIP05_a1.png（PROP_BADGE 都头腰牌） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约一掌高（12至16厘米），宽度略窄于成年男子手掌；可单手完整握持。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_BADGE_Clip_05_EP01_CLIP05_a1_compare.png
  - 🟢 Clip_05 图片/EP01_CLIP05_a2.png（PROP_BADGE 都头腰牌） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约一掌高（12至16厘米），宽度略窄于成年男子手掌；可单手完整握持。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_BADGE_Clip_05_EP01_CLIP05_a2_compare.png
  - 🟢 Clip_05 图片/Clip05_end.png（PROP_CAKE_POLE 炊饼担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_CAKE_POLE_Clip_05_Clip05_end_compare.png
  - 🟢 Clip_05 图片/Clip05_first.png（PROP_CAKE_POLE 炊饼担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_CAKE_POLE_Clip_05_Clip05_first_compare.png
  - 🟢 Clip_05 图片/Clip05_first_a3.png（PROP_CAKE_POLE 炊饼担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_CAKE_POLE_Clip_05_Clip05_first_a3_compare.png
  - 🟢 Clip_05 图片/EP01_CLIP05_a1.png（PROP_CAKE_POLE 炊饼担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_CAKE_POLE_Clip_05_EP01_CLIP05_a1_compare.png
  - 🟢 Clip_05 图片/EP01_CLIP05_a2.png（PROP_CAKE_POLE 炊饼担） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_CAKE_POLE_Clip_05_EP01_CLIP05_a2_compare.png
  - 🟢 Clip_05 图片/Clip05_end.png（PROP_STAIR_RAIL STAIR RAIL） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=扶手顶面距踏步前缘约 85–95 厘米，为成年人腰部高度；一手可自然包握，直棂间距均匀。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_STAIR_RAIL_Clip_05_Clip05_end_compare.png
  - 🟢 Clip_05 图片/Clip05_first_a3.png（PROP_STAIR_RAIL STAIR RAIL） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=扶手顶面距踏步前缘约 85–95 厘米，为成年人腰部高度；一手可自然包握，直棂间距均匀。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_STAIR_RAIL_Clip_05_Clip05_first_a3_compare.png
  - 🟢 Clip_05 图片/EP01_CLIP05_a1.png（PROP_STAIR_RAIL STAIR RAIL） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=扶手顶面距踏步前缘约 85–95 厘米，为成年人腰部高度；一手可自然包握，直棂间距均匀。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_STAIR_RAIL_Clip_05_EP01_CLIP05_a1_compare.png
  - 🟢 Clip_05 图片/EP01_CLIP05_a2.png（PROP_STAIR_RAIL STAIR RAIL） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=扶手顶面距踏步前缘约 85–95 厘米，为成年人腰部高度；一手可自然包握，直棂间距均匀。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_STAIR_RAIL_Clip_05_EP01_CLIP05_a2_compare.png
  - 🟢 Clip_06 图片/Clip06_first.png（PROP_DINING_TABLE DINING TABLE） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约长 120–140 厘米、宽 60–75 厘米、高 70–75 厘米；坐下时桌沿在腰上，两人对坐后中间仍有放置茶盏的空间。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_DINING_TABLE_Clip_06_Clip06_first_compare.png
  - 🟢 Clip_06 图片/EP01_CLIP06_a1.png（PROP_DINING_TABLE DINING TABLE） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约长 120–140 厘米、宽 60–75 厘米、高 70–75 厘米；坐下时桌沿在腰上，两人对坐后中间仍有放置茶盏的空间。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_DINING_TABLE_Clip_06_EP01_CLIP06_a1_compare.png
  - 🟢 Clip_06 图片/EP01_CLIP06_a2.png（PROP_DINING_TABLE DINING TABLE） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=约长 120–140 厘米、宽 60–75 厘米、高 70–75 厘米；坐下时桌沿在腰上，两人对坐后中间仍有放置茶盏的空间。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_DINING_TABLE_Clip_06_EP01_CLIP06_a2_compare.png
  - 🟢 Clip_06 图片/Clip06_first.png（PROP_DOORFRAME DOORFRAME） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=净宽约 75–85 厘米，净高约 180–190 厘米；成年人单人通行，横楣略高于头顶，门槛低于脚踝。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_DOORFRAME_Clip_06_Clip06_first_compare.png
  - 🟢 Clip_06 图片/EP01_CLIP06_a1.png（PROP_DOORFRAME DOORFRAME） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=净宽约 75–85 厘米，净高约 180–190 厘米；成年人单人通行，横楣略高于头顶，门槛低于脚踝。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_DOORFRAME_Clip_06_EP01_CLIP06_a1_compare.png
  - 🟢 Clip_06 图片/EP01_CLIP06_a2.png（PROP_DOORFRAME DOORFRAME） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=净宽约 75–85 厘米，净高约 180–190 厘米；成年人单人通行，横楣略高于头顶，门槛低于脚踝。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_DOORFRAME_Clip_06_EP01_CLIP06_a2_compare.png
  - 🟢 Clip_06 图片/Clip06_first.png（PROP_TEA_CUP TEA CUP） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=口径约 8–10 厘米，高约 5–7 厘米，可一手托住或以拇指与其余手指环持，整体明显小于成人掌宽。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_TEA_CUP_Clip_06_Clip06_first_compare.png
  - 🟢 Clip_06 图片/EP01_CLIP06_a1.png（PROP_TEA_CUP TEA CUP） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=口径约 8–10 厘米，高约 5–7 厘米，可一手托住或以拇指与其余手指环持，整体明显小于成人掌宽。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_TEA_CUP_Clip_06_EP01_CLIP06_a1_compare.png
  - 🟢 Clip_06 图片/EP01_CLIP06_a2.png（PROP_TEA_CUP TEA CUP） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=口径约 8–10 厘米，高约 5–7 厘米，可一手托住或以拇指与其余手指环持，整体明显小于成人掌宽。；/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/prop_shape_review/PROP_TEA_CUP_Clip_06_EP01_CLIP06_a2_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
