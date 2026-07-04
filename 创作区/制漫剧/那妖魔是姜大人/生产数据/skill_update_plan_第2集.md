# skill 更新重制计划 — 第2集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`video`
- 建议动作：`重制` · `script_stage1` → `video`
- 需要重制：是
- 重制策略：`最小`
- 共享定妆库：默认沿用（定妆照/场景照 PNG 复用，重制只覆盖本集分镜帧）
- 变动 skill：n2d, n2d-image, n2d-review, n2d-script

## 变动文件
- `skills/n2d-image/scripts/image_prompt_pack.py`
- `skills/n2d-review/scripts/gate.py`
- `skills/n2d-review/scripts/gates/contract.py`
- `skills/n2d-script/validate_storyboard_contract.py`
- `skills/n2d/_lib/n2d_visual_styles.py`

## 当前生产缺口
- 当前待办：`图生视频`（视频 = `⬜`）
- 建议 skill：`n2d-video`
- 建议命令：`n2d-video /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第2集`

## 图片质检环境与阶段跳转
- 机检能力：`full`
- 当前解释器：`/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `8`，降级 `False`
- block 摘要：第2集 含高风险/含角色路由（Clip_01、Clip_02、Clip_03、Clip_04、Clip_05、Clip_06）但缺 `设定库/model_routes_baseline.json`。第2集起必须先用打样集 `n2d-model-router --write-baseline` 建立 shot_type→primary 后端基线，否则跨集自然路由可能换后端导致脸质感、运动质感和画风漂移。 | 生视频后端「dreamina」（渠道 Dreamina，执行后端 dreamina）缺少本次官方 API/CLI 刷新证据：refresh evidence is 1 day(s) old。正式付费出视频前必须实时查官方文档/本机 CLI 或 API help，确认单 Clip 上限、首尾/多帧能力、原生音画/口型、身份绑定、分辨率/价格/额度和输出 schema，再记录刷新证据：`python3 skills/n2d/_lib/video_backend_adapter.py record-refresh <作品根> --backend "dreamina" --channel "Dreamina" --source "<官方文档或CLI/API证据>" --note "<本次能力结论>"`。证据文件：创作区/制漫剧/那妖魔是姜大人/生产数据/video_backend_capabilities/dreamina__via_dreamina.json。未刷新不得开跑，避免旧 API 或能力误判造成整集返工。
- 当前应停在/回退：`video` — full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video
- 建议安装：无需补装
- 报告：`/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/image_qc_第2集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：✅ 达标（10 Clip 全有锚帧/豁免）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `full`）
- **契约继承**：✅ 已继承（verdict=`pass`）

## 执行步骤
1. `queue_bounded_rerun`
```bash
python3 skills/n2d-batch/scripts/queue.py plan "/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" --episodes 2 --rerun-from script_stage1 --scope "skill 更新后重制到 video·复用共享定妆库·只重出本集分镜帧" --max-concurrency 1 --max-retries 1
```
2. `manual_alternative`：排队后由 n2d-batch runner 或对应 stage skill 执行返工；不要同时手工运行阶段命令，避免队列账本与实际产物分叉。 手工替代路径仅在不使用 batch 时执行：`n2d-script /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第2集`
3. `verify_after_image_regen`
   - 运行条件：仅在 n2d-batch/阶段 skill 已实际完成图片重出后运行；只生成队列计划时不要当作已验收。
```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate "/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人" 第2集 --stage image  # 重出图后验像素一致性（含 image_qc）
```

## 备注
- 真正执行前先看 diff/计划；涉及出图/出视频/配音/合成等付费或不可逆步骤时必须再次确认。
- 共享定妆库默认沿用：本次变更未命中定妆库生产规则（标准三视图/角色一致性/资产注册/LoRA），`出图/共享/图片/` 的定妆照/场景照 PNG 与 identity_registry 复用不重出，重制范围只覆盖本集分镜帧。n2d-image 共享先行硬闸门会跳过已 ✅ 的共享 PNG，直接以其为参考重出分镜。
