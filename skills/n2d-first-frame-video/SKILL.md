---
name: n2d-first-frame-video
description: 独立的画布首帧图生视频工作台，从上传、画布选择或生成的首帧中提取可见约束，设计主体动作、镜头运动与环境变化，输出可续跑的视频生成任务并登记验收。Use when a user clicks 首帧图生视频, 首帧生成视频, image-to-video from first frame, or needs the LibTV-style first frame → motion design → video generation flow. This top-level skill must not import, invoke, or depend on n2d-video, mv-video, ad-video, or any series implementation.
---

# n2d-first-frame-video

把“首帧图生视频”作为独立三步工作台执行，不进入任何系列状态机。

## 独立边界

- 只运行本目录 `scripts/first_frame_video.py`，只依赖 Python 标准库。
- 不 import、调用或复制任何系列的视频 runner、router、gate 或设置。
- 可参考其它 skill 的运动设计与连续性经验，但本 skill 拥有自己的 schema、job、状态和验收。
- 对外只交付 JSON、首帧和视频文件；无后端也必须产出可续跑 job 包。

## 工作流

### 1. 选择首帧

接受本地上传、当前画布选择或 AI 生成结果。真实文件必须绑定路径与 SHA-256；缩略图和占位不可标为就绪。

### 2. 设计运动

从首帧描述主体动作、表情变化、镜头运动、景深、环境变化、时间节奏和禁止变化项。运动 prompt 以可执行变化为主，不复述整张图的静态细节。

### 3. 生成与验收

1. 选择具体视频模型、渠道、比例、分辨率、时长和数量。
2. `prepare` 生成绑定首帧 SHA 的 job；真实付费提交前确认。
3. 输出视频后记录文件与 SHA，并核对开头与首帧连续、身份稳定、动作合理、无突变。
4. 只有真实输出且 `review=accepted` 才完成。

## AI 代理交互节点

- 自动把“让她回头、镜头推进”等自然语言拆成主体、镜头、环境三层运动。
- 运动意图含糊时只询问最关键的动作或镜头取向。
- 付费提交、覆盖已验收视频或切换模型时停下确认。

## 命令

```bash
python3 skills/n2d-first-frame-video/scripts/first_frame_video.py init \
  --source first-frame.png --output shot.first-frame-video.json

python3 skills/n2d-first-frame-video/scripts/first_frame_video.py prepare \
  shot.first-frame-video.json --write

python3 skills/n2d-first-frame-video/scripts/first_frame_video.py validate \
  shot.first-frame-video.json
```

字段与完成条件见 [first-frame-video-schema.md](references/first-frame-video-schema.md)。
