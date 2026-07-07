# skill 更新重制计划 — 第1集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`review`
- 建议动作：`重制` · `compose` → `review`
- 需要重制：是
- 重制策略：`最小`
- 变动 skill：n2d, n2d-compose, n2d-review

## 变动文件
- `skills/n2d-compose/compose.sh`
- `skills/n2d-review/scripts/mechanical_check.py`
- `skills/n2d/scripts/pilot_check.py`

## 当前生产缺口
- 当前待办：`审查验收`（验收 = `⬜`）
- 建议 skill：`n2d-review`
- 建议命令：`n2d-review /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `67`，降级 `False`
- block 摘要：本集分镜/出图 prompt 引用了未登记的资产标记 `VFX_百妖谱金光`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。 | 出视频/第1集/视频/Clip_02_看见虎妖尸身_part1.mp4 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：豁免（后端 `deferred_auto_route` 不支持≥3帧·能力门控）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）
- **契约继承**：✅ 已继承（verdict=`pass`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" --episodes 1 --rerun-from compose --scope "skill 更新后重制到 review" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-compose /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集`

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 三帧契约豁免：路由后端 deferred_auto_route 不支持≥3帧（能力门控自动豁免），本集不强制中段锚帧。
