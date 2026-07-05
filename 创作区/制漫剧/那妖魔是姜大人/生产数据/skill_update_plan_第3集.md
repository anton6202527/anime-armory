# skill 更新重制计划 — 第3集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`image`
- 建议动作：`重制` · `image_prompt` → `image`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：默认沿用（定妆照/场景照 PNG 复用，重制只覆盖本集分镜帧）
- 变动 skill：n2d-image

## 变动文件
- `skills/n2d-image/scripts/codex_image_runner.py`

## 当前生产缺口
- 当前待办：`出图`（出图 = `40/116`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第3集`

## 图片质检环境与阶段跳转
- 机检能力：`degraded`
- 当前解释器：`/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `1`，降级 `True`
- block 摘要：逐镜参考规划有 24 条行动项未确认落实（无持久主体 ID 后端×大变化镜 10 镜）：镜头 EP03_CLIP01、EP03_CLIP02、EP03_CLIP03、EP03_CLIP04、EP03_CLIP05、EP03_CLIP06、EP03_CLIP07、EP03_CLIP08…。请按 reference_plan_第3集.md 把补拍/多样参考/控制网/升档落进 出图/第3集/prompt/01_分镜出图.md 后再付费出图；不能让参考规划停在侧车文件里。若已完成人审落实，请写结构化 `生产数据/reference_plan_application_第3集.json`（kind=n2d_reference_plan_application, accepted=true, reviewer, plan_sha256, prompt_path, prompt_sha256, applied_action_count, applied_evidence）。当前落实证据状态：plan_sha256 与当前 reference_plan 不一致。 建议升 LoRA：CHAR_01/囚犯初醒态。 | 长线剧（第3集）仍用无持久主体后端（codex）逐镜参考图派生，且核心/常驻角色缺 native subject / Face Lock / face_embedding / LoRA：姜月初(CHAR_01/囚犯初醒态)、姜月初(CHAR_01/镇魔司伪装态)。production 长线第3集起这不是建议项，会跨集累积脸漂；请先注册原生主体、启用 face_embedding，或对核心角色完成 LoRA 后再付费出图。【G-I1 推荐升档】长线默认起点应为可注册主体 ID（②·先于 LoRA）：可灵主体库 / 即梦角色库 / Seedream Universal Reference（注册一次按 ID 跨镜跨集引用）；或对核心角色训 LoRA。hero/反复崩脸角色可叠 max-lock 栈：主体 ID + PuLID(脸保真) + 低强度角色 LoRA(~0.6) + ControlNet。在 n2d-image 选择点 `生图模型` 带此推荐向用户摆「换后端=整集重做定妆的一致性税」知情权衡，不私自写死后端。
- 当前应停在/回退：`image` — 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 建议安装：优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。
- 报告：`/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/image_qc_第3集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：✅ 达标（10 Clip 全有锚帧/豁免）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `degraded`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" --episodes 3 --rerun-from image_prompt --scope "skill 更新后重制到 image·复用共享定妆库·只重出本集分镜帧" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-image /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第3集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第3集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库默认沿用：本次变更未命中定妆库生产规则（标准三视图/角色一致性/资产注册/LoRA），`出图/共享/图片/` 的定妆照/场景照 PNG 与 identity_registry 复用不重出，重制范围只覆盖本集分镜帧。n2d-image 共享先行硬闸门会跳过已 ✅ 的共享 PNG，直接以其为参考重出分镜。
