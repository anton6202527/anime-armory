# skill 更新重制计划 — 第3集

- 作品根：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人`
- 当前阶段：`image`
- 建议动作：`只重跑 gate/review` · `gate/review` → `image`
- 需要重制：否
- 重制策略：`最小`

## 当前生产缺口
- 当前待办：`出图返修`（出图 = `17/17`）
- 建议 skill：`n2d-image`
- 建议命令：`n2d-image /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第3集`
- 备注：image_qc=block，hard_blocks=38；先修复报告阻断并重跑 image_qc：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/image_qc_第3集.md

## 图片质检环境与阶段跳转
- 机检能力：`degraded`
- 当前解释器：`/opt/homebrew/opt/python@3.14/bin/python3.14`
- 当前 image_qc：`verdict=block`，硬阻断 `38`，非阻断初筛 `14`，降级 `True`
- block 摘要：prompt lint:  镜头 1（`EP03_CLIP01` · 众人跪求的假大人 · ensemble_blocking）：打斗/动作镜含清晰正脸/frontal portrait 倾向，容易把拆招拍成看镜头摆拍；改为可辨三分之二侧脸/侧脸/背身侧轮廓，并明确不与主镜头对视。 | prompt lint:  镜头 3（`EP03_CLIP03` · 黑衣赤纹换装 · dialogue_shot_reverse）：正向 prompt 写了「黑衣」类服饰/形态，但资产身份注册层绑定 `CHAR_01/“囚途残损态”` （asset_key=CHAR_01__囚途残损态）没有对应服饰定妆。换装/形态变体必须新建独立 `CHAR_xx/形态`、wardrobe_profile 和 reference_group，禁止复用其它服饰状态参考。 | prompt lint:  镜头 5（`EP03_CLIP05` · 马队急停试探 · ensemble_blocking）：打斗/动作镜含清晰正脸/frontal portrait 倾向，容易把拆招拍成看镜头摆拍；改为可辨三分之二侧脸/侧脸/背身侧轮廓，并明确不与主镜头对视。
- 当前应停在/回退：`image` — 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 建议安装：优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。
- 报告：`/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/image_qc_第3集.md`

## 健康检测（源/三帧/图片/契约继承）
- **源小说**：✅ 源未变动
- **帧策略合同**：✅ 达标（需执行锚 4 Clip；普通镜模式=risk_only）
- **图片一致性**：⚠️ hard_blocks=38（verdict=`block`，精度 `degraded`）
- **契约继承**：— 未校验（缺 inherit_contract 报告，先跑 n2d-video `inherit_contract.py`）

## 备注
- image_qc 硬阻断已将当前生产阶段从 `video_prompt` 拉回 `image`；先做 n2d-image 返修并重跑 image_qc，不进入下游。
- 图片一致性存在硬阻断（image_qc verdict=block，hard_blocks=38）：见 `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/image_qc_第3集.md`，崩脸/服装/场景/接缝需重出受影响镜。
- 出图→出视频视觉契约继承尚未校验：缺 `/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/contract_inheritance_第3集.json`。先跑 `python3 skills/n2d-video/scripts/inherit_contract.py <作品根> 第3集`，校验参考帧契约（色调/光位锚/轴线视线/角色状态演进/景别）+ 文字 prompt 是否从出图侧正确传到出视频侧、命名角色镜是否锁脸、出图绑定的场景/道具/特效资产是否丢失，再出视频。
