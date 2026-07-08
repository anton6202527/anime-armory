# mv-image QC（出图落档机检）

- 总判定: **review** · 硬阻断 0（主角脸崩，必须重抽） · 非阻断初筛 0 · 视觉降级 1
- 机检能力: **degraded** · 当前解释器: `/opt/homebrew/opt/python@3.14/bin/python3.14`
- 阶段跳转: **image** · 视觉质检为降级结果，正式进 mv-video 前需补依赖重跑或逐项人审确认
- 缺失/降级: insightface/onnxruntime/buffalo_l face embedding, 主角脸漂移 G1
- 建议安装: 在可装重依赖的 conda env（如 facefusion）跑：python -m pip install pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') 预热/下载模型。

## 像素机检（主角脸=硬阻断，主色=非阻断初筛）
- 主角脸漂移 G1: 🟢 block 0 · warn 0
- 主色漂移 palette: 🟢 block 0 · warn 0
  - 主角 floor=None 自标定=False 模式=pillow_fallback
  - palette_anchor=[[242, 245, 240], [31, 37, 40], [47, 127, 132], [111, 143, 175], [215, 162, 74], [60, 170, 170], [60, 90, 200], [235, 235, 235], [35, 35, 40]] 阈值=110.0
  - note: 未装 insightface——脸漂移降级为 Pillow 基础机检（仅查 图存在/可解码/分辨率/清晰度，不做人脸相似度、不臆造相似度分）；主角脸是否同人仍需人判兜底。

## 锚点句落地 lint（逐 clip prompt）
- 🟢 5 clip 已 lint · warn 0

## 禁用本地身份像素修复检查
- 🟢 无事件账本（/Users/wesley/learn/anime-armory/创作区/制MV/仗剑下山/生产数据/production_events.jsonl）

落档判定：**verdict=block** → 主角脸崩（崩脸/图损坏），必须重抽后重跑；**verdict=review** → 只有主色/锚点等非阻断初筛或视觉降级时不挡 mv-video（按阶段跳转补依赖/复核）；**verdict=ok** → 放行。主色与锚点是像素初筛/确定性 lint，非硬失败（MV 筛选宽容铁律）。

## 人审放行
- scope: 20s demo excerpt only；正式 3min MV 必须补 full face QC。
- notes: 现有 5 张首帧/定妆图已人工并排检查，一致性可支持 demo；镜头10手/剑细节正式版需重审。
