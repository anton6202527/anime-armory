# ad-voice 后端接入（参考）

ad-voice 自带 `say`（macOS 占位）与 `estimate`（跨平台静音占位）。真后端各自产 wav 后登记，
时长清单与 voice_key 对账逻辑由 ad-voice 自己维护。

## 占位后端（无凭证也能跑时长）

- `--backend say`：macOS 内置 TTS（`say -v Tingting`）。中文偶发空音频 → 脚本自动降级静音占位并在 `时长清单.json` 标 `占位:true`。
- `--backend estimate`：纯静音，按中文约 4.5 字/秒估时。任何机器都能跑出时长清单。

## 真后端（conda env，权重在仓库外）

| 后端 | env | 用途 | 克隆 |
|---|---|---|---|
| CosyVoice | `cosyvoice` | 零样本/指令 TTS，中文强 | 喂参考音克隆需授权 |
| GPT-SoVITS | 自建 | 本地少样本克隆 | 需授权 |
| MiniMax / 火山 | 云 API | 商用音色、稳定 | 仿真人音色需授权 |
| EdgeTTS 自定义 | `uvx edge-tts` | 无 key 的合成音色逐句 WAV；适合无授权参考音时先出非克隆 VO 样片 | 非克隆；正式投放前仍需确认服务/平台授权 |

接入方式：用各自 CLI/API 把 `脚本/voiceover.txt` 逐句产成 `line_01.wav..line_NN.wav`，再用 `render_voice.py --backend <真后端> --from-dir <目录>` 登记到项目 `配音/`，由 ad-voice 统一 ffprobe 实测时长、拼 `vo.wav`、写 `时长清单.json`（字段形状见 `voice_manifest.py`）。VO 旁白建议固定一个音色键（如 `VO`），代言人/对白各自一色，跨镜稳定。

真后端缺 `--from-dir` 时必须硬退出，不允许静默回退到静音/估算占位；否则 `finalize_storyboard` 会把占位时长误当成正式时长焊进镜头。

无授权参考音但需要先跑通真 VO 时，可用：

```bash
python3 skills/ad-voice/render_edgetts.py "<作品根>" --voice zh-CN-XiaoxiaoNeural
python3 skills/ad-voice/render_voice.py "<作品根>" --backend EdgeTTS --from-dir "<作品根>/配音/edgetts_lines"
```

## 合规

克隆/仿真人音色 = 强监管。`render_voice.py` 的硬闸门按**实际是否在克隆**判定（不按后端名固定集合）：
传了 `--ref`/`--clone`、给了参考音 env（`*_REF_*`，`*_TEXT` 逐字稿除外）、或请求具体代言人/名人 `--voice-id`（云端商用后端的指定音色）时，须 `VOICE_CLONE_AUTHORIZED=1`，否则拒做。
默认嗓（不喂参考音、不指定 voice_id）即便是真后端也无需授权；占位后端 `say`/`estimate` 永不触发。
后端名做归一（小写、去连字符/下划线）后再比对，`cosyvoice-v2` / `Cosy_Voice` / `XTTS` / `fishspeech` 等变体不会绕过。
代言人真声、名人音色还须有授权痕迹，投放前在 `合规/AI使用说明.md`（`ad-craft/ai_usage.py --voice-status` / `--talent-status`）留档。

## 时长清单.json schema（驱动镜头时长）

权威字段（ad-script finalize / ad-review 依赖）：顶层 `has_placeholder` == any(line `占位`)；
每句 `idx`/`role`/`text`/`seconds`/`占位`/`voice_key`（附带 `start`/`end`/`gap_after`/`line_wav`/`音色键`）。

```json
{
  "kind": "ad_voice_manifest", "backend": "say", "total_seconds": 28.4,
  "has_placeholder": true,
  "lines": [
    {"idx": 1, "role": "旁白", "text": "又是被闹钟拖起来的一天？",
     "seconds": 2.3, "start": 0.0, "end": 2.3, "gap_after": 0.25,
     "line_wav": "line_01.wav", "音色键": "VO", "voice_key": "say:Tingting#placeholder", "占位": true}
  ]
}
```
