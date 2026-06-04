# 声音克隆 + 人声分离

## 参考音频要求
≥10s（30-60s 更佳）、目标角色单人声、BGM 越小越好、mp3/wav、≤20MB。

## 人声分离（参考带 BGM 时）
demucs（首次需 `pip install --user demucs soundfile`）：
    python3 -m demucs --two-stems=vocals -o <out> <input.wav>
产物 <out>/htdemucs/<name>/vocals.wav。再 loudnorm/silenceremove 规整后作参考。

## MiniMax 复刻
source 凭证后：
    python3 voice_clone.py <参考音频> <自定义voiceID(字母开头≥8位)>
得 voice_id → 填 MM_SHEN=<voiceID>（或对应角色 env）重生该角色。

## GPT-SoVITS / CosyVoice（本地·质量更高）
见 backends.md 的本地服务搭建；零样本传 ref音频+ref文本即可，微调需 1min+ 干净音。
