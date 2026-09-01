# skill 更新重制计划 — 第1集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅`
- 当前阶段：`image`
- 建议动作：`只重跑 gate/review` · `gate/review` → `image`
- 需要重制：否
- 重制策略：`最小`

## 当前生产缺口
- 当前待办：`出图返修`（出图 = `147/183`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅 第1集`
- 备注：image_qc=block，hard_blocks=67；先修复报告阻断并重跑 image_qc：/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/image_qc_第1集.md

## 图片质检环境与阶段跳转
- 机检能力：`degraded`
- 当前解释器：`/opt/homebrew/opt/python@3.14/bin/python3.14`
- 当前 image_qc：`verdict=block`，硬阻断 `67`，非阻断初筛 `24`，降级 `True`
- block 摘要：脸部覆盖缺失: 图片/Clip03_first.png | 脸部覆盖缺失: 图片/EP01_CLIP03_a1.png | 脸部覆盖缺失: 图片/EP01_CLIP03_a2.png
- 当前应停在/回退：`image` — 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 建议安装：优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/image_qc_第1集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：⚠️ 必需执行锚缺失 0/15 Clip；缺尾帧声明 0 Clip；缺 PNG 文件 24 个（普通镜不设默认三帧；backend=`None`）
- **图片一致性**：⚠️ hard_blocks=67（verdict=`block`，精度 `degraded`）

## 备注
- 帧策略合同未达标：必需执行锚缺失 0 个 Clip，缺尾帧声明 0 个 Clip，已声明但 PNG 不存在 24 个。普通镜不设默认三帧；这里只报告 E1/R1-R3/显式 opt-in 或尾帧真缺口。回 n2d-script 跑 `anchor_planner.py <作品根> 第1集 --write` 补齐声明，再回 n2d-image 出 `_mid/_aK/_end` 帧。；缺文件样例：出图/第1集/图片/EP01_CLIP05_a1.png, 出图/第1集/图片/EP01_CLIP05_a2.png, 出图/第1集/图片/Clip05_first_a3.png, 出图/第1集/图片/EP01_CLIP06_a1.png
- 图片一致性存在硬阻断（image_qc verdict=block，hard_blocks=67）：见 `/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产数据/image_qc/第1集/image_qc_第1集.md`，崩脸/服装/场景/接缝需重出受影响镜。
