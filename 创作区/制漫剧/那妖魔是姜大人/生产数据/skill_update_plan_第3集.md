# skill 更新重制计划 — 第3集

- 作品根：`/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`image`
- 建议动作：`只重跑 gate/review` · `gate/review` → `image`
- 需要重制：否
- 重制策略：`最小`

## 当前生产缺口
- 当前待办：`出图`（出图 = `⬜`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第3集`

## 图片质检环境与阶段跳转
- 机检能力：`degraded`
- 当前解释器：`/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 当前 image_qc：`verdict=review`，硬阻断 `0`，非阻断初筛 `1`，降级 `True`
- block 摘要：reference_slot_gate: 道具/场景 PROP_尸场物资包 引用槽位未绑定真实产物：出图/共享/图片/定妆_道具_尸场物资包.png 不存在 | 长线剧（第3集）仍用无持久主体后端（codex）逐镜参考图派生，且核心/常驻角色缺 native subject / Face Lock / face_embedding / LoRA：姜月初(CHAR_01/囚犯初醒态)、姜月初(CHAR_01/镇魔司伪装态)。production 长线第3集起这不是建议项，会跨集累积脸漂；请先注册原生主体、启用 face_embedding，或对核心角色完成 LoRA 后再付费出图。【G-I1 推荐升档】长线默认起点应为可注册主体 ID（②·先于 LoRA）：可灵主体库 / 即梦角色库 / Seedream Universal Reference（注册一次按 ID 跨镜跨集引用）；或对核心角色训 LoRA。hero/反复崩脸角色可叠 max-lock 栈：主体 ID + PuLID(脸保真) + 低强度角色 LoRA(~0.6) + ControlNet。在 n2d-image 选择点 `生图模型` 带此推荐向用户摆「换后端=整集重做定妆的一致性税」知情权衡，不私自写死后端。
- 当前应停在/回退：`image` — 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 建议安装：优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。
- 报告：`/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/image_qc_第3集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **三帧契约**：✅ 达标（10 Clip 全有锚帧/豁免）
- **图片一致性**：✅ 无硬阻断（verdict=`review`，精度 `degraded`）
