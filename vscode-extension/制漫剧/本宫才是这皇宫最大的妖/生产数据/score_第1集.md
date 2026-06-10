# n2d 自动审片评分

- 集：第1集
- 总分：72 / 100
- 阈值：85
- 状态：回流
- 生成时间：2026-06-09T12:10:19+00:00

## 维度

| 维度 | 权重 | 分数 | 状态 | block | warn | 回流 stage |
|---|---:|---:|---|---:|---:|---|
| 角色一致性 | 20 | 98 | 通过 | 0 | 0 | image |
| 服装一致性 | 12 | 100 | 通过 | 0 | 0 | image |
| 场景一致性 | 12 | 0 | 回流 | 19 | 0 | image |
| 字幕正确性 | 16 | 65 | 回流 | 1 | 0 | script_stage2 |
| 音画同步 | 16 | 63 | 回流 | 1 | 0 | compose |
| 节奏密度 | 12 | 65 | 回流 | 1 | 0 | script_stage2 |
| 风格一致性 | 12 | 100 | 通过 | 0 | 0 | image |

## 自动回流建议

- `image`：场景一致性；回 n2d-image 修场景定妆、光位锚或尾帧；必要时回 n2d-video 重出接缝 clip。
- `script_stage2`：字幕正确性、节奏密度；回 n2d-script 阶段2重跑 finalize_storyboard / 字幕重定时；必要时重出配音 manifest。；回 n2d-script 阶段2重切镜头时长曲线、补钩子/爽点/集尾 cliffhanger。；定位产物：脚本/第1集/字幕_中文.srt、脚本/第1集/字幕_英文.srt、脚本/第1集/storyboard.json
- `compose`：音画同步；回 n2d-compose 对齐配音轨、clip 时长、原生音轨策略；若时长源头错，回 n2d-script 阶段2。；定位镜头：Clip_00；定位产物：出视频/合成前必须换真实配音重定时、出视频/第1集/视频/Clip_00.mp4、合成/第1集

## 证据

### 角色一致性
- 锚点门(N3): block=0 warn=0 ok=0 skipped=True
- 脸(G1): block=0 warn=0 ok=0 skipped=True
- 片内时序(N2): block=0 warn=0 ok=0 skipped=True
- 跨集漂移机检不可用（insightface/cv2 缺失、identity_registry 缺失或机检跳过）——本集未核对跨集角色漂
- mechanical[一致性] 第1集: 脸部相似度度量已跳过（未装 face_recognition/insightface）——崩脸暂由人判清单覆盖；装库后跑 scripts/face_consistency.py 自动给每镜 vs 定妆锚点打分
### 服装一致性
- 服装配色(N1): block=0 warn=0 ok=0 skipped=False
### 场景一致性
- 场景(O2): block=0 warn=0 ok=0 skipped=False
- 接缝接力: block=0 warn=0 ok=0 skipped=False
- mechanical[尾帧] clip#1: need_endframe=true 但 endframe_png 缺失或文件不存在
- mechanical[尾帧] clip#2: need_endframe=true 但 endframe_png 缺失或文件不存在
- mechanical[尾帧] clip#3: need_endframe=true 但 endframe_png 缺失或文件不存在
- mechanical[尾帧] clip#4: need_endframe=true 但 endframe_png 缺失或文件不存在
- mechanical[尾帧] clip#5: need_endframe=true 但 endframe_png 缺失或文件不存在
- mechanical[尾帧] clip#6: need_endframe=true 但 endframe_png 缺失或文件不存在
- ...另有 16 条
### 字幕正确性
- mechanical[字幕] 第1集: 中英字幕条数不一致（中16/英0）——删镜未同步删 EN 块会逐条错位
- visual[subtitle_ocr]: block=0 warn=0 skipped=True
- visual[subtitle_ocr] 缺成片或中文字幕 SRT，字幕 OCR 跳过
### 音画同步
- mechanical[完整性] 第1集: 配音仍为占位音色（占位:true）——可用于出图 demo 的 rough timing；正式出视频/合成前必须换真实配音重定时
- mechanical[完整性] 第1集: 产物快照：配音句 16 · clip 0 · 成片 0
- visual[av_duration]: block=0 warn=0 skipped=True metrics={"final_sec": null, "srt_sec": 84.668, "storyboard_sec": 84.668, "voice_sec": 84.667982}
- visual[av_duration] 缺成片或 ffprobe 不可用，成片音画时长对账跳过
- visual[lip_sync]: block=0 warn=0 skipped=True
- visual[lip_sync] 缺视频 prompt，无法判断口型风险；可提供 lip_sync_第N集.json 接入外部检测
### 节奏密度
- visual[final_rhythm_density]: block=1 warn=0 skipped=False metrics={"clip_count": 20, "final_sec": 84.668, "hook_count": 2, "hook_interval_sec": 42.334, "shot_density_per_min": 14.173}
- visual[final_rhythm_density] 平均钩子间隔 42.3s > 30s，节奏密度阻断
### 风格一致性
- 风格(S1): block=0 warn=0 ok=0 skipped=True
- 糊/低质(N4): block=0 warn=0 ok=0 skipped=False
