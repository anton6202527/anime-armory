# Audio video schema

`app-audio-video/v1` 完全由该独立 skill 维护。改名前的
`n2d-audio-video/v1` 与中间命名 `app-n2d-audio-video/v1` 只作为兼容输入读取，
下次 `prepare --write` 时迁移为新命名空间。

## 核心字段

- `steps.audio / plan / generation`：三步状态。
- `audio.path / sha256 / format / duration / analysis_mode`：真实输入与分析精度。
- `timeline[]`：`id / start / end / energy / visual / cut`。
- `visual.style / subject / camera / reference_path / reference_sha256 / forbidden`。
- `generation.model / channel / aspect_ratio / resolution / count`。
- `job.audio_sha256 / timeline_sha256 / prompt / status`。
- `output.path / sha256 / review / beat_sync_notes`。

非 WAV 输入无法用标准库读取时长时，`analysis_mode=unavailable` 且 `audio` 步保持 active；用户或适配后端补充真实时长后才能 `prepare`。
