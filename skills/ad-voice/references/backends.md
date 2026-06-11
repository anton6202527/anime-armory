# ad-voice 后端接入（参考）

ad-voice 自带 `say`（macOS 占位）与 `estimate`（跨平台静音占位）。真后端各自产 wav 后登记，
逻辑与 n2d 同构但不复用其代码。

## 占位后端（无凭证也能跑时长）

- `--backend say`：macOS 内置 TTS（`say -v Tingting`）。中文偶发空音频 → 脚本自动降级静音占位并在 `时长清单.json` 标 `占位:true`。
- `--backend estimate`：纯静音，按中文约 4.5 字/秒估时。任何机器都能跑出时长清单。

## 真后端（conda env，权重在仓库外）

| 后端 | env | 用途 | 克隆 |
|---|---|---|---|
| CosyVoice | `cosyvoice` | 零样本/指令 TTS，中文强 | 喂参考音克隆需授权 |
| GPT-SoVITS | 自建 | 本地少样本克隆 | 需授权 |
| MiniMax / 火山 | 云 API | 商用音色、稳定 | 仿真人音色需授权 |

接入方式：用各自 CLI 把 `脚本/voiceover.txt` 逐句产到 `配音/line_NN.wav`，再用 ffprobe 实测时长写 `时长清单.json`（字段形状见 `voice_manifest.py`）。VO 旁白建议固定一个音色键（如 `VO`），代言人/对白各自一色，跨镜稳定。

## 合规

克隆/仿真人音色 = 强监管。`render_voice.py` 对克隆类后端硬性要求 `VOICE_CLONE_AUTHORIZED=1`。代言人真声、名人音色须有授权痕迹，投放前在 `合规/AI使用说明.md`（`ad-craft/ai_usage.py --voice-status` / `--talent-status`）留档。

## 时长清单.json schema（驱动镜头时长）

```json
{
  "kind": "ad_voice_manifest", "backend": "say", "total_seconds": 28.4,
  "has_placeholder": true,
  "lines": [
    {"idx": 1, "角色": "旁白", "文本": "又是被闹钟拖起来的一天？",
     "时长": 2.3, "start": 0.0, "end": 2.3, "gap_after": 0.25,
     "line_wav": "line_01.wav", "音色键": "VO", "voice_key": "say:Tingting#placeholder", "占位": true}
  ]
}
```
