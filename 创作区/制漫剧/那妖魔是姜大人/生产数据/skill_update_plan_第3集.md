# skill 更新重制计划 — 第3集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`script_stage1`
- 建议动作：`重制` · `script_stage1` → `script_stage1`
- 需要重制：是
- 重制策略：`最小`
- 变动 skill：n2d, n2d-review, n2d-script

## 变动文件
- `skills/n2d-review/SKILL.md`
- `skills/n2d-review/scripts/gate.py`
- `skills/n2d-review/scripts/gates/consistency.py`
- `skills/n2d-review/scripts/gates/contract.py`
- `skills/n2d-review/scripts/spectacle_motion_measure.py`
- `skills/n2d-review/scripts/spectacle_video_qc.py`
- `skills/n2d-review/scripts/video_semantic_runner.py`
- `skills/n2d-script/SKILL.md`
- `skills/n2d-script/validate_storyboard_contract.py`
- `skills/n2d/Q&A.md`
- `skills/n2d/SKILL.md`
- `skills/n2d/_lib/n2d_route.py`
- `skills/n2d/_lib/n2d_visual_styles.py`
- `skills/n2d/_lib/settings.py`
- `skills/n2d/progress.py`
- `skills/n2d/references/architecture.md`
- `skills/n2d/references/contract.md`
- `skills/n2d/references/制作模式与视频路由.md`
- `skills/n2d/references/选择点与偏好.md`
- `skills/n2d/run.py`

## 当前生产缺口
- 当前待办：`阶段1·剧本改编`（剧本改编 = `⬜`）
- 建议 skill：`n2d-script`
- 建议命令：`n2d-script /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第3集`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" --episodes 3 --rerun-from script_stage1 --scope "skill 更新后重制到 script_stage1" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-script /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第3集`

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
