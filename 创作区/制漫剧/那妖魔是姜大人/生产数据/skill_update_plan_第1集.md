# skill 更新重制计划 — 第1集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`review`
- 建议动作：`重制` · `image_prompt` → `review`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：需复核（变更命中定妆库生产规则：skills/n2d-image/SKILL.md）
- 需刷新 gate/QC：是（image）
- 变动 skill：n2d, n2d-compose, n2d-dashboard, n2d-image, n2d-review

## 变动文件
- `skills/n2d-compose/compose.sh`
- `skills/n2d-dashboard/scripts/dashboard.py`
- `skills/n2d-image/SKILL.md`
- `skills/n2d-image/scripts/codex_image_runner.py`
- `skills/n2d-image/scripts/derive_makeup_pack.py`
- `skills/n2d-image/scripts/image_prompt_pack.py`
- `skills/n2d-image/scripts/image_qc.py`
- `skills/n2d-image/scripts/vlm_verify.py`
- `skills/n2d-review/SKILL.md`
- `skills/n2d-review/scripts/backends/presence_owlv2.py`
- `skills/n2d-review/scripts/consistency_audit.py`
- `skills/n2d-review/scripts/consistency_ledger.py`
- `skills/n2d-review/scripts/gate.py`
- `skills/n2d-review/scripts/mechanical_check.py`
- `skills/n2d-review/scripts/motion_quality_consistency.py`
- `skills/n2d-review/scripts/resident_presence.py`
- `skills/n2d-review/scripts/scene_consistency.py`
- `skills/n2d-review/scripts/video_semantic_runner.py`
- `skills/n2d/scripts/audience_experience.py`
- `skills/n2d/scripts/failure_taxonomy.py`
- `skills/n2d/scripts/preventive_contracts.py`
- `skills/n2d/scripts/release_verdict.py`
- `skills/n2d/scripts/stop_loss.py`

## 当前生产缺口
- 当前待办：`审查验收`（验收 = `⬜`）
- 建议 skill：`n2d-review`
- 建议命令：`n2d-review /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `32`，降级 `False`
- block 摘要：接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 | CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚
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
python3 skills/n2d-batch/scripts/queue.py plan "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" --episodes 1 --rerun-from image_prompt --scope "skill 更新后重制到 review" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-image /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第1集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库需复核（非默认沿用）：本次变更命中定妆库生产规则（skills/n2d-image/SKILL.md）。先按最新规则复核、必要时重出共享定妆/场景，再用 `python3 skills/n2d-image/scripts/asset_impact.py <作品根> <改动的定妆资产>` 级联出引用它、需跟着重出的本集分镜。
- 三帧契约豁免：路由后端 deferred_auto_route 不支持≥3帧（能力门控自动豁免），本集不强制中段锚帧。
- 图片一致性报告已过期（image_qc 之后出图被重生成，inputs_fingerprint 失配）：当前结论不可信，先重跑 `python3 skills/n2d-image/scripts/image_qc.py <作品根> 第1集` 再据此判断。
- 契约继承报告已过期（生成后出图/出视频 prompt 又改了，inputs_fingerprint 失配）：`inherited` 结论不可信，先重跑 `python3 skills/n2d-video/scripts/inherit_contract.py <作品根> 第1集` 再判。
