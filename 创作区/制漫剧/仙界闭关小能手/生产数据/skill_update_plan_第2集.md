# skill 更新重制计划 — 第2集

- 作品根：`/Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手`
- 当前阶段：`script_stage2`
- 建议动作：`重制` · `script_stage1` → `script_stage2`
- 需要重制：是
- 重制策略：`最小`
- 变动 skill：n2d, n2d-dashboard, n2d-review, n2d-script

## 变动文件
- `skills/n2d-dashboard/scripts/dashboard.py`
- `skills/n2d-review/scripts/consistency_charter.py`
- `skills/n2d-review/scripts/face_consistency.py`
- `skills/n2d-review/scripts/gate.py`
- `skills/n2d-review/scripts/gate_core.py`
- `skills/n2d-review/scripts/gates/backend.py`
- `skills/n2d-review/scripts/gates/consistency.py`
- `skills/n2d-review/scripts/gates/contract.py`
- `skills/n2d-review/scripts/gates/face.py`
- `skills/n2d-script/SKILL.md`
- `skills/n2d-script/references/打斗分镜.md`
- `skills/n2d/_lib/image_backend_adapter.py`
- `skills/n2d/_lib/n2d_const.py`
- `skills/n2d/_lib/settings.py`
- `skills/n2d/_lib/style_policy.py`

## 当前生产缺口
- 当前待办：`阶段2·分镜设计（原生音画·脚本时长定稿）`（分镜设计 = `⬜`）
- 建议 skill：`n2d-script`
- 建议命令：`n2d-script /Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手 第2集  (原生音画脚本时长定稿)`
- 备注：原生音画模式：配音列不作为硬前置，按 storyboard.json clips[].duration 定稿分镜与字幕节奏。

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手" --episodes 2 --rerun-from script_stage1 --scope "skill 更新后重制到 script_stage2" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-script /Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手 第2集`

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
