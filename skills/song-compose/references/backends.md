# song-compose 后端接入

> 先云后本地。MVP 用 Suno 最快；本地主力候选 ACE-Step（Mac 可跑），先验证再定。

## compiler 与 prompt 组法

- **完整生产合同**：`compose_prompts/take_XX.md` 上半部保留 A&R brief、reference boundaries、chord sheet、topline notes、操作提示和挑版标准；这些内容不整份提交。
- **lyrics**：取 `词/lyrics.md` 的结构化歌词原文，保留 `[verse]/[chorus]` 等段标签，不摘要、不改写；`lyrics_sha256` 防止任务包与 manifest 漂移。
- **style/prompt**：`skills/song/_lib/song_prompt_compiler.py` 把 style seed + `song_brief.sonic_identity/emotional_arc/hook_deadline_seconds` 编译成整体声音字段，不把参考包、文件路径、权利说明或挑版清单拼进去。
- **后端字段映射**：Suno/Udio → `style + lyrics (+ title)`；ACE-Step → `prompt + lyrics + audio_duration`；DiffRhythm → `style_prompt + lyrics + duration`。以 `takes_manifest.json.takes[].submit_fields` 和 Markdown 的“后端编译提交字段”为准。
- **任务包**：用 `scripts/compose_song.py <写歌根> --backend <后端> --takes N --duration 秒` 生成 schema v2 manifest；外部生成后仍按 manifest 登记/挑版。

## Suno / Udio（云·最快）
- **web**：登录 → Custom 模式，只复制 take 的“后端编译提交字段”，将 lyrics/style/title 分别放到对应框 → 生成 → 下载 → `compose_song.py --register <文件> --take X`。
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
