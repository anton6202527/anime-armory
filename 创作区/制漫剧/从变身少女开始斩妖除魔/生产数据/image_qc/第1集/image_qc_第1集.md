# n2d Image QC（出图落档机检）

- episode: 第1集
- 总判定: **block** · 硬阻断 39（必须修） · 非阻断初筛 0 · 视觉降级 3
- 机检能力: **degraded** · 当前解释器: `/opt/homebrew/opt/python@3.14/bin/python3.14`
- 阶段跳转: **image** · 视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度
- 缺失/降级: insightface/onnxruntime/buffalo_l face embedding, 崩脸 G1, 接缝接力, 锚点门 N3
- 建议安装: 优先用 facefusion conda env：/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。

## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）
- 崩脸 G1: 🔴 block 39 · warn 0
- 发型 H1: 🟢 block 0 · warn 0
- 服装 N1: 🟢 block 0 · warn 0
- 场景 O2: 🟢 block 0 · warn 0
- 道具/特效 P2: 🟢 block 0 · warn 0
- 接缝接力: ⏭ 跳过（不可用）
- 锚点门 N3: ⏭ 跳过（锚点质量门已跳过（未装 insightface/cv2）——主参考是否单张清晰正脸暂由人判。）

## 角色脸定妆比对覆盖（硬闸）
- 🟢 已落档角色图 required 0 · covered 0 · missing 0 · pending 39 · precision degraded

## 本地贴脸修复禁用（硬闸）
- 🟢 未发现最新落档事件来自本地贴脸修复。

## 执行层 lint（逐镜 prompt）
- 🟢 15 镜已 lint · block 0 · warn 0

落档判定：**verdict=block** → 有硬阻断（崩脸/纯文生图/非法 CHAR_id），必须修复后重跑；**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。
