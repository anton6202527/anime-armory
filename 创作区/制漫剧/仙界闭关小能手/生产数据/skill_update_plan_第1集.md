# skill 更新重制计划 — 第1集

- 作品根：`/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手`
- 当前阶段：`image`
- 建议动作：`重制` · `image_prompt` → `image`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：默认沿用（定妆照/场景照 PNG 复用，重制只覆盖本集分镜帧）
- 需刷新 gate/QC：是（image）
- 变动 skill：n2d, n2d-image, n2d-review

## 变动文件
- `skills/n2d-image/scripts/codex_image_runner.py`
- `skills/n2d-image/scripts/image_qc.py`
- `skills/n2d-review/scripts/consistency_charter.py`
- `skills/n2d-review/scripts/gate.py`
- `skills/n2d-review/scripts/gates/backend.py`
- `skills/n2d-review/scripts/gates/consistency.py`
- `skills/n2d-review/scripts/gates/contract.py`
- `skills/n2d-review/scripts/gates/face.py`
- `skills/n2d/_lib/image_backend_adapter.py`

## 当前生产缺口
- 当前待办：`出图`（出图 = `⬜`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手 第1集`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：豁免（后端 `None` 不支持≥3帧·能力门控）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手" --episodes 1 --rerun-from image_prompt --scope "skill 更新后重制到 image·复用共享定妆库·只重出本集分镜帧" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-image /Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手 第1集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手" 第1集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库默认沿用：本次变更未命中定妆库生产规则（标准三视图/角色一致性/资产注册/LoRA），`出图/共享/图片/` 的定妆照/场景照 PNG 与 identity_registry 复用不重出，重制范围只覆盖本集分镜帧。n2d-image 共享先行硬闸门会跳过已 ✅ 的共享 PNG，直接以其为参考重出分镜。
- 三帧契约豁免：路由后端 None 不支持≥3帧（能力门控自动豁免），本集不强制中段锚帧。
