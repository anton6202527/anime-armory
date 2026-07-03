# song-compose 后端接入

> 先云后本地。MVP 用 Suno 最快；本地主力候选 ACE-Step（Mac 可跑），先验证再定。

## prompt 组法（通用）
- **lyrics**：取 `词/lyrics.md` 的结构化歌词（保留 `[verse]/[chorus]` 段标签，多数模型认）。
- **style**：取 `创作蓝图.md` 的 曲风 + 情绪 + 平台，拼成一句英文/中文 style（如 "国风流行, 女声, 抒情, 抖音, 90s, key of Am"）。
- **任务包**：优先用 `scripts/compose_song.py <写歌根> --backend <后端> --takes N --duration 秒` 生成 `歌/compose_prompts/take_XX.md` 和 `歌/takes_manifest.json`；每个后端都按该 manifest 登记/挑版。

## Suno / Udio（云·最快）
- **web**：suno.com 登录 → Custom 模式，按 `歌/compose_prompts/take_XX.md` 把歌词贴 lyrics 框、style 贴 style 框 → 生成 → 下载 mp3/wav → `compose_song.py --register <文件> --take X`。
- **API**（若有 `SUNO_API_KEY`）：端点形态随版本变，调用前核对官方文档；拿到音频后仍用 `compose_song.py --register` 登记，不绕过 manifest。

## ACE-Step v1.5（本地·主力候选，Mac CoreML）
```bash
git clone https://github.com/ace-step/ACE-Step && cd ACE-Step
pip install -e .            # Mac: 走 MPS/CoreML
# headless 生成（具体 flag 以仓库 README 为准）
acestep --lyrics "$(cat 词/lyrics.md)" --prompt "<style>" --duration 120 --out take_01.wav
```
- 出歌后 `compose_song.py <写歌根> --register take_01.wav --take 1`；试听评分后 `--select take_01` 定稿。需要分离人声时再用 `place_song.py <写歌根> 歌/song.wav --split` 或 demucs。
- 速度/质量先在 Mac 实测（像 LoRA 那样验证再定主力）。

## DiffRhythm 2（本地·扩散，偏 CUDA）
- pip + 权重；出整首快；Mac 支持弱，优先 ACE-Step。

## 合法性
- 演唱音色：自有 / 授权 / 合成；**克隆真人歌手嗓需授权**（2026 WMG×Suno / UMG×Udio opt-in）。未授权拒做。
- 商用前确认所选平台/模型的商用条款。
