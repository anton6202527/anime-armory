# n2d 媒体选择性刷新计划 — 第2集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 集：`第2集`
- 图片 targets：（无）
- 视频 targets：Clip_01, Clip_04, Clip_06
- 原则：media_refresh 只生成计划，不做审片/质检判定；保留或重制结论必须来自已有 gate/QC/review findings 或显式人工输入。

## 职责边界
- media_refresh 只生成选择性刷新计划和候选执行顺序，不直接判定图片/视频好坏。
- 无证据规则：没有 findings 或人工判定时，media_refresh 只能列出复核步骤；不得把 target 判为坏/可用，也不得无条件排入重制。
- 不得把 --image/--video/--target 传入值直接解释为坏目标
- 不得在没有 gate/QC/review findings 或人工判定时无条件排入重制
- 不得替代 n2d-review 或 n2d 各 gate/QC 的审片职责

## 判定来源
- 已有 gate/QC/review findings（含 severity、return_to_stage、affected_shots/artifacts 等结构化定位）
- 审片人或用户显式点名的坏图/坏视频、可沿用目标及原因
- 缺文件、路径不存在、manifest 无法追踪等可确定的文件完整性事实

## 证据驱动的保留/重制标准

### 可保留
- finding 或人工判定显示身份/服装/场景/画风锚点可识别，未漂移到影响连续性
- finding 或人工判定显示轻微构图、表情、背景细节或审美偏差不影响下游叙事/卡点/字幕表达
- gate/QC 显示分辨率、画幅、安全区、时长和元数据满足本线非阻断要求
- review/gate 显示合规、授权（改编权/肖像/声音克隆）不存在 block

### 可排重制
- finding、人工判定或文件完整性事实显示目标文件缺失、路径未登记、无法被下游 manifest/job/timeline 追踪
- finding 或人工判定显示人物脸/核心服装/关键场景漂移，或与参考/定妆不再是同一资产
- gate/QC/review finding 显示视频动作、节奏、时长、接缝、首尾帧、视觉契约继承出现 block
- finding 显示使用了过期 prompt、后端混用或未授权逆向路径，导致本线最新 gate 不可放行

## 已有报告证据（逐 target 预判）
- image_qc：ok（`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/image_qc_第2集.json`）
- contract_inheritance：ok（`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/contract_inheritance_第2集.json`）
  - `Clip_01` → **no_evidence** · （无命中 finding）
  - `Clip_04` → **no_evidence** · （无命中 finding）
  - `Clip_06` → **no_evidence** · （无命中 finding）

## 按最新 skill 的流程
- n2d-update: 先按最新 skill 快照生成 bounded plan，重制上界不超过本集当前阶段。
- n2d-image: 收集 image_qc/dashboard gate/n2d-review findings 或人工判定；media_refresh 不自行判坏。
- n2d-video: 收集 video gate/QC/n2d-review findings 或人工判定；只有证据确认 block 才排 video 返工。
- n2d-dashboard/n2d-review: 如发生重制，必须回 gate/review，确认像素一致性、接缝和合规闭环。

## 执行顺序
1. shell
```bash
python3 skills/n2d-update/scripts/update_plan.py check "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第2集 --write-plan --regen-mode 严审刷新
```
2. shell
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第2集 --stage video  # 预检：收集现有视频 gate/QC 证据
```
3. AI agent：只在 video gate/QC/n2d-review findings 或显式人工输入确认这些视频 target 不符合最新 prompt/QC/review 标准时，才执行：`python3 skills/n2d-batch/scripts/queue.py plan "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" --episodes 2 --rerun-from video --affected-shot "Clip_01" --affected-shot "Clip_04" --affected-shot "Clip_06" --scope "媒体刷新·证据确认后重出视频" --max-concurrency 1 --max-retries 1`；没有证据时保留为待复核，不排队。
4. AI agent：如果上一步已经排队并由 n2d-batch/对应 stage skill 实际完成视频重出，再执行验收：`python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第2集 --stage video`；若只是生成队列计划，不能把这一步当成已验收。

## 备注
- 已有报告里无命中 finding 的 target（无证据≠已合格，需人工确认或补跑对应 gate）：Clip_01、Clip_04、Clip_06
- 本计划只生成选择性刷新流程，不直接调用生图/生视频后端，也不替代审片/质检。
- 执行前必须引用 gate/QC/review findings 或显式人工输入；未列入 targets 的图片/视频默认不动。
- 没有证据时只推进复核步骤，不把 target 归类为坏/能用，也不无条件排入重制。
- 如发生重制，必须回到 n2d-review/gate，不能只看生成是否成功。
