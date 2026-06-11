---
name: ad-voice
description: 拍广告 第3阶段·VO配音 — 把 脚本/voiceover.txt（旁白/台词）转成 AI 配音：逐句音频 + 整轨 vo.wav + 时长清单.json（每句实测时长，驱动下游镜头时长；逐句记 voice_key 音色键供跨镜对账）。多后端可插拔（CosyVoice/GPT-SoVITS/MiniMax/火山 真后端 + macOS say / estimate 占位）。克隆真人嗓需 VOICE_CLONE_AUTHORIZED=1 硬闸门。ad-* 自包含，不复用 n2d-voice。Use when asked to 广告配音/VO/旁白配音/生成配音/时长清单 for a 拍广告 project. Triggers 广告配音, VO, 旁白, 配音, 时长清单, voice_key, voiceover, 声音克隆, ad-voice.
---

# ad-voice — 拍广告 · VO 配音（音频先行）

把 `脚本/voiceover.txt` 转成 **逐句音频 + 整轨 `vo.wav` + `时长清单.json`**。`时长清单.json` 的**每句实测时长驱动分镜镜头时长**（与 n2d「配音先行」同构）——`ad-script` 分镜 pass 读它定镜头长度。

**自包含**：不复用 `n2d-voice`，逻辑各写各的。

## 偏好（私有）

按 `../_偏好约定.md` 读 `<作品根>/_设置.md`。涉及：`配音后端`、`音乐来源`（VO 与音乐床混音在 `ad-compose`）。声音克隆是**合规点**，每次确认授权。

## 后端

| 后端 | 说明 |
|---|---|
| `say` | macOS 内置 TTS 占位（中文可能空音频→自动降级静音占位并告警）|
| `estimate` | 跨平台静音占位，按字数估时（无任何 TTS 也能把时长跑出来）|
| CosyVoice / GPT-SoVITS / MiniMax / 火山 | 真后端，各自 CLI 产 wav 后登记（见 `references/backends.md`）|

```bash
python3 skills/ad-voice/render_voice.py "<作品根>" --backend say        # 占位
python3 skills/ad-voice/render_voice.py "<作品根>" --backend estimate    # 跨平台占位
```

产物：`配音/line_NN.wav` + `配音/vo.wav` + `配音/时长清单.json`。

## 合规硬闸门

- **克隆真人嗓 / 仿真人音色**：需 `VOICE_CLONE_AUTHORIZED=1`（肖像+声音授权，2026 opt-in），否则拒做。代言人真声需授权痕迹（`ad-craft/ai_usage.py` 记 `--talent-status`）。
- **占位不等于成品**：`时长清单.json.has_placeholder=true` 时，下游 `ad-image`/`ad-video` 可先按占位时长推画面做 demo，但**正式定稿前必须用真 VO 复跑**（音画才准），`ad-compose` 对占位会提醒。

## 广告专有要点

- **VO + 音乐床混合驱动**：广告节奏常由 VO 与音乐床共同决定；VO 时长是镜头长度的硬锚，音乐床节奏点在 `ad-script` 时间轴标注、`ad-compose` 混音时对齐。
- **voice_key 跨镜对账**：逐句记实际音色键（旁白一色、代言人一色），二期 `ad-review` 据此查"同一旁白换了声"。

## 测试

```bash
cd skills/ad-voice && python3 test_voice_manifest.py
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 拿占位配音当成品直接合成 | 占位只为跑通时长/demo；正式片用真 VO 复跑 |
| 未授权克隆真人/代言人声音 | 须 `VOICE_CLONE_AUTHORIZED=1` + 授权痕迹，否则拒做 |
| 配音前就锁镜头时长 | 镜头时长由本阶段实测 VO 驱动（ad-script 分镜 pass 回跑）|
