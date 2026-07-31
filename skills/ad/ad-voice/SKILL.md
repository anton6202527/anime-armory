---
name: ad-voice
description: 拍广告 第3阶段·VO配音 — 把 voiceover.txt 转成逐句音频 + vo.wav + 时长清单.json，并自动产 voice_qc.json（ffprobe/ffmpeg 实测逐句/整轨时长、可读性、非静音与峰值；voice_key 跨镜对账）。多后端可插拔，say/estimate 只作 rough 占位；克隆真人嗓需 VOICE_CLONE_AUTHORIZED=1。ad-* 自包含。Use when asked to 广告配音/VO/旁白配音/生成配音/时长清单 for a 拍广告 project. Triggers 广告配音, VO, 旁白, 配音, 时长清单, voice_key, voiceover, 声音克隆, ad-voice.
---

# ad-voice — 拍广告 · VO 配音（音频先行）

把 `脚本/voiceover.txt` 转成 **逐句音频 + 整轨 `vo.wav` + `时长清单.json`**。`时长清单.json` 的**每句实测时长驱动分镜镜头时长**，`ad-script` 分镜 pass 读它定镜头长度。

**自包含**：只使用 ad-voice 自己的脚本、references 和产物契约。

## 偏好（私有）

按 `../skills/ad/ad-craft/references/选择点与偏好.md` 读 `<作品根>/_设置.md`。涉及：`配音后端`、`音乐来源`（VO 与音乐床混音在 `ad-compose`）。声音克隆是**合规点**，每次确认授权。

## 后端

| 后端 | 说明 |
|---|---|
| `say` | macOS 内置 TTS 占位（中文可能空音频→自动降级静音占位并告警）|
| `estimate` | 跨平台静音占位，按字数估时（无任何 TTS 也能把时长跑出来）|
| CosyVoice / GPT-SoVITS / MiniMax / 火山 | 真后端，各自 CLI/API 产 `line_01.wav..line_NN.wav` 后用 `--from-dir` 登记（见 `references/backends.md`）|
| EdgeTTS 自定义 | `render_edgetts.py` 生成非克隆合成音色逐句 WAV，再用 `--from-dir` 登记；网络可用时适合无授权参考音的 demo/样片 |

```bash
python3 skills/ad/ad-voice/render_voice.py "<作品根>" --backend say        # 占位
python3 skills/ad/ad-voice/render_voice.py "<作品根>" --backend estimate    # 跨平台占位
python3 skills/ad/ad-voice/render_voice.py "<作品根>" --backend CosyVoice --from-dir "<真实逐句wav目录>"
python3 skills/ad/ad-voice/render_edgetts.py "<作品根>" --voice zh-CN-XiaoxiaoNeural
python3 skills/ad/ad-voice/render_voice.py "<作品根>" --backend EdgeTTS --from-dir "<作品根>/配音/edgetts_lines"
```

产物：`配音/line_NN.wav` + `配音/vo.wav` + `配音/时长清单.json` + `配音/voice_qc.json`。成片后另由本 skill 的 `asr_consistency.py` 生成 `合成/asr_consistency.json` + `asr_receipts.json`，把批准 VO、实际 VO、字幕和最终音轨绑定到各自 SHA；外部预转写也必须记录媒体 SHA、transcript SHA、引擎/模型和时间，不能拿手填 txt 冒充实际 ASR。

真后端不能静默降级：选择 `CosyVoice/GPT-SoVITS/MiniMax/火山/自定义` 但没有 `--from-dir` 时必须阻断，不能自动写静音占位并假装跑过正式配音。`--from-dir` 目录必须包含和 `voiceover.txt` 行数一致的 `line_01.wav..line_NN.wav`。**重跑保护**：占位合成对「文件在 + 文本 hash 未变 + 音色键未变」的行直接复用不重合成（`--force` 全量重跑）；`--from-dir` 导入遇到目标已存在且内容不同时，先把旧文件落 `.bak` 再覆盖，绝不静默覆盖真 VO；`时长清单.json` 原子写。登记后自动跑 `voice_qc.py`：ffprobe 对账逐句/整轨实测时长，ffmpeg 检查非静音与峰值；正式模式要求 full precision，失败不回写完成。compose 统一重采样到 48 kHz，输入非 48 kHz 会 WARN 而不是伪称源文件合格。

```bash
python3 skills/ad/ad-voice/voice_qc.py "<作品根>"
python3 skills/ad/ad-voice/asr_consistency.py "<作品根>" --run-asr --asr-model large-v3
python3 skills/ad/ad-craft/scripts/stage_acceptance.py "<作品根>" --stage voice
```

**收尾**：回写 `_进度.md` VO配音 ✅（占位后端 say/estimate 标 ⏳rough），提示下一步 `ad-script` **分镜 pass**（用实测时长定镜头长度）。

## 合规硬闸门

- **克隆真人嗓 / 仿真人音色**：闸门按**实际是否克隆**触发（传 `--ref`/`--clone`、有参考音 env `*_REF_*`、或请求具体代言人/名人 `--voice-id`），需 `VOICE_CLONE_AUTHORIZED=1`（肖像+声音授权，2026 opt-in），否则拒做。默认嗓（无参考音/不指定 voice_id）即便真后端也不拦；后端名归一后比对，`cosyvoice-v2`/`XTTS`/`fishspeech` 等变体不绕过。代言人真声另需授权痕迹（`ad-craft/ai_usage.py` 记 `--talent-status`）。
- **占位不等于成品**：`时长清单.json.has_placeholder=true` 时，下游 `ad-image`/`ad-video` 可先按占位时长推画面做 demo，但**正式定稿前必须用真 VO 复跑**（音画才准），`ad-compose` 对占位会提醒。

## 广告专有要点

- **VO + 音乐床混合驱动**：广告节奏常由 VO 与音乐床共同决定；VO 时长是镜头长度的硬锚，音乐床节奏点在 `ad-script` 时间轴标注、`ad-compose` 混音时对齐。
- **voice_key 跨镜对账**：逐句记实际音色键（旁白一色、代言人一色），`ad-review` 已会阻断“同一角色/旁白跨句换 voice_key”。

## 测试

```bash
cd skills/ad/ad-voice && python3 -m pytest test_voice_manifest.py test_voice_qc.py test_asr_consistency.py
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 拿占位配音当成品直接合成 | 占位只为跑通时长/demo；正式片用真 VO 复跑 |
| 未授权克隆真人/代言人声音 | 须 `VOICE_CLONE_AUTHORIZED=1` + 授权痕迹，否则拒做 |
| 配音前就锁镜头时长 | 镜头时长由本阶段实测 VO 驱动（ad-script 分镜 pass 回跑）|
| 有 WAV 就把 VO 标完成 | 还需 `voice_qc.json` full precision、非静音、逐句/整轨时长可对账 |
