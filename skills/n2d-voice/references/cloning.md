# 声音克隆 + 人声分离

## ⛔ 合规闸门（每次确认 · non-negotiable）
声音克隆**只能**用于：① 本人嗓 / ② 已获**明确授权**的他人嗓 / ③ 纯合成音色。
- 复刻真人歌手/演员/公众人物声音需本人书面授权（2026 opt-in）；未授权复刻属违规，禁止。
- 这是项目约定里的「合规/不可逆」点——即使 `_设置.md` 记过偏好，**每次仍重确认来源**，不沉默沿用。
- 脚本侧已落地（**两条克隆路径都硬闸门**）：`voice_clone.py`（MiniMax 复刻）必须显式 `VOICE_CLONE_AUTHORIZED=1`；`render_voice.py` 走**零样本后端且喂了参考音**（任一 `<PREFIX>_REF_*`）时同样要求 `VOICE_CLONE_AUTHORIZED=1`，否则停止——不再只是打印提示。用默认嗓（不喂参考音）不算克隆，无需授权。
- 配音成片用于投放时，叠加 AI 合规标识水印（见 n2d-watermark skill），不可去除。

## 参考音频要求
≥10s（30-60s 更佳）、目标角色单人声、BGM 越小越好、mp3/wav、≤20MB。

## 人声分离（参考带 BGM 时）
demucs（首次需 `pip install --user demucs soundfile`）：
    python3 -m demucs --two-stems=vocals -o <out> <input.wav>
产物 <out>/htdemucs/<name>/vocals.wav。再 loudnorm/silenceremove 规整后作参考。

## MiniMax 复刻
source 凭证后（须先确认参考音来源合规，显式声明授权）：
    VOICE_CLONE_AUTHORIZED=1 python3 voice_clone.py <参考音频> <自定义voiceID(字母开头≥8位)>
得 voice_id → 填 MM_SHEN=<voiceID>（或对应角色 env）重生该角色。

## GPT-SoVITS / CosyVoice（本地·质量更高）
见 backends.md 的本地服务搭建；零样本传 ref音频+ref文本即可，微调需 1min+ 干净音。
