# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **review** · 硬阻断 0（必须修） · 非阻断初筛 1 · 视觉降级 1
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 阶段跳转: **video** · full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video

## 本集图片命名空间（硬闸）
- 🟢 当前 prompt 声明目标 44 张；未声明 live Clip PNG 0 张
- note: 本集图片目录不存在。

## 人工逐图拒收（硬闸）
- 🟢 active rejects 0 · review `/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/human_image_review.json`

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🟢 block 0 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 人体解剖 N5: 🟢 block 0 · warn 0
- 接缝接力: ⏭ 跳过（无 /Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/图片——出图后再跑接缝机检。）
- 锚点门 N3: 🟢 block 0 · warn 0

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 0 · covered 0 · missing 0 · pending 35 · precision full

## 核心角色五角 turnaround（逐视图 hash 收据硬闸）
- 🟢 checked forms 3 · pending/stale receipts 0 · contract `front/three_quarter/side/rear_three_quarter/back`
- 像素头顶/脚底/中心线/身高与脸框只作 WARN 级可复算证据；硬条件仅是当前 PNG 的逐视图 pass 收据。

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟡 13 镜已 lint · block 0 · warn 1
  - 🟡 多视图对齐初筛异常 CHAR_04/常态：视平线不齐：three_quarter(0.09) vs rear_three_quarter(0.64)，跨视图脸中心高度差 56%>6%；比例不一：three_quarter 脸高是 side 的 4.94 倍（>1.35），不是同距离同景别的定妆板——像素几何是可复算启发式证据，按 B10 只报 WARN；最终以逐视图、当前 hash 绑定的人审收据为准。

## 高风险道具禁形/尺寸逐图复核（硬闸）
- total 9 · pending 0 · confirmed 9
- 确认文件: `/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/prop_shape_confirmations.json`
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_断刀.png（PROP_断刀 断刀） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/prop_shape_review/PROP_断刀_shared_primary_定妆_道具_断刀_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_翻覆囚车.png（PROP_翻覆囚车 翻覆囚车） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/prop_shape_review/PROP_翻覆囚车_shared_primary_定妆_道具_翻覆囚车_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_道具_虎首.png（PROP_虎首 虎首） 禁形=现代物件、文字水印、结构漂移、数量漂移；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/prop_shape_review/PROP_虎首_shared_primary_定妆_道具_虎首_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_特效_百妖谱.png（VFX_百妖谱 百妖谱） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/prop_shape_review/VFX_百妖谱_shared_primary_定妆_特效_百妖谱_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_特效_百妖谱金色古卷面板.png（VFX_系统面板 百妖谱金色古卷面板） 禁形=AI生成可读文字、现代手机UI、随机蓝色科幻屏、乱码文字；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/prop_shape_review/VFX_系统面板_shared_primary_定妆_特效_百妖谱金色古卷面板_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_特效_道行反噬.png（VFX_道行反噬 道行反噬） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/prop_shape_review/VFX_道行反噬_shared_primary_定妆_特效_道行反噬_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_特效_道行灌注.png（VFX_道行灌注 道行灌注） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇、双刃剑轮廓、第二条锋刃、中心对称剑脊、第二把实体武器；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/prop_shape_review/VFX_道行灌注_shared_primary_定妆_特效_道行灌注_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_特效_黑妖血.png（VFX_黑妖血 黑妖血） 禁形=随机改色、遮挡主体脸、现代科幻UI、过度血腥猎奇；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/prop_shape_review/VFX_黑妖血_shared_primary_定妆_特效_黑妖血_compare.png
  - 🟢 shared_primary 出图/共享/图片/定妆_武器_横刀.png（WEAPON_01 横刀） 禁形=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把刀；尺寸=None；/Users/wesley/learn/anime-armory/创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/image_qc/第1集/prop_shape_review/WEAPON_01_shared_primary_定妆_武器_横刀_compare.png

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
