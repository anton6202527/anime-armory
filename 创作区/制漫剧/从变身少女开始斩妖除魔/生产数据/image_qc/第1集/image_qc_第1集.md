# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **block** · 硬阻断 5（必须修） · 非阻断初筛 0 · 视觉降级 1
- 机检能力: **full** · 当前解释器: `/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 阶段跳转: **image** · image_qc 有硬阻断，需修复/重抽受影响镜头后重跑

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
- 🔴 checked forms 3 · pending/stale receipts 5 · contract `front/three_quarter/side/rear_three_quarter/back`
- 像素头顶/脚底/中心线/身高与脸框只作 WARN 级可复算证据；硬条件仅是当前 PNG 的逐视图 pass 收据。
  - 🔴 CHAR_01/常态 three_quarter `出图/共享/图片/定妆_CHAR_01__常态_45度.png`：core_view_png_missing
  - 🔴 CHAR_01/常态 side `出图/共享/图片/定妆_CHAR_01__常态_侧.png`：core_view_png_missing
  - 🔴 CHAR_01/常态 rear_three_quarter `出图/共享/图片/定妆_CHAR_01__常态_后45度.png`：core_view_png_missing
  - 🔴 CHAR_01/常态 back `出图/共享/图片/定妆_CHAR_01__常态_背.png`：core_view_png_missing
  - 🔴 CHAR_01/常态 turnaround `出图/共享/图片/定妆_CHAR_01__常态_三视图.png`：core_turnaround_board_receipt_missing_or_stale

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🔴 13 镜已 lint · block 5 · warn 0
  - 🔴 核心档逐视图收据缺失/过期 CHAR_01/常态 three_quarter（出图/共享/图片/定妆_CHAR_01__常态_45度.png）：core_view_png_missing；必须对当前 PNG 写 verdict=pass、reviewer、reviewed_at、png_sha256 后才能 finalize。
  - 🔴 核心档逐视图收据缺失/过期 CHAR_01/常态 side（出图/共享/图片/定妆_CHAR_01__常态_侧.png）：core_view_png_missing；必须对当前 PNG 写 verdict=pass、reviewer、reviewed_at、png_sha256 后才能 finalize。
  - 🔴 核心档逐视图收据缺失/过期 CHAR_01/常态 rear_three_quarter（出图/共享/图片/定妆_CHAR_01__常态_后45度.png）：core_view_png_missing；必须对当前 PNG 写 verdict=pass、reviewer、reviewed_at、png_sha256 后才能 finalize。
  - 🔴 核心档逐视图收据缺失/过期 CHAR_01/常态 back（出图/共享/图片/定妆_CHAR_01__常态_背.png）：core_view_png_missing；必须对当前 PNG 写 verdict=pass、reviewer、reviewed_at、png_sha256 后才能 finalize。
  - 🔴 核心档逐视图收据缺失/过期 CHAR_01/常态 turnaround（出图/共享/图片/定妆_CHAR_01__常态_三视图.png）：core_turnaround_board_receipt_missing_or_stale；必须对当前 PNG 写 verdict=pass、reviewer、reviewed_at、png_sha256 后才能 finalize。

落档判定：**verdict=block** → 有硬阻断（崩脸/人体解剖N5铁证/纯文生图/非法 CHAR_id/缺高风险人体合约），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
