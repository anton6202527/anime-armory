# mv-image QC（出图落档机检 · MV 版，对标 n2d-image image_qc）

- 总判定: **review** · 硬阻断 0（主角脸崩，必须重抽） · 非阻断初筛 0 · 视觉降级 1
- 机检能力: **degraded** · 当前解释器: `/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- 阶段跳转: **image** · 视觉质检为降级结果，正式进 mv-video 前需补依赖重跑或逐项人审确认
- 缺失/降级: 主色漂移 palette
- 建议安装: 在可装重依赖的 conda env（如 facefusion）跑：python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。

## 像素机检（主角脸=硬阻断，主色=非阻断初筛）
- 主角脸漂移 G1: 🟢 block 0 · warn 0
- 主色漂移 palette: ⏭ 跳过（视觉蓝图/设置里未找到 palette_anchor 主色——主色漂移机检跳过（不臆测主色）。）
  - 主角 floor=0.5 自标定=False 模式=insightface
  - note: 视觉蓝图/设置里未找到 palette_anchor 主色——主色漂移机检跳过（不臆测主色）。

## 锚点句落地 lint（逐 clip prompt）
- ⏭ 跳过（缺 分镜/clip_plan.json——先跑 mv-plan 再 lint 锚点。）
- note: 缺 分镜/clip_plan.json——先跑 mv-plan 再 lint 锚点。

落档判定：**verdict=block** → 主角脸崩（崩脸/图损坏），必须重抽后重跑；**verdict=review** → 只有主色/锚点等非阻断初筛或视觉降级时不挡 mv-video（按阶段跳转补依赖/复核）；**verdict=ok** → 放行。主色与锚点是像素初筛/确定性 lint，非硬失败（MV 筛选宽容铁律）。
