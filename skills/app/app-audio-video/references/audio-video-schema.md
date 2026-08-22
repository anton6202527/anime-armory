# Audio video schema

`app-audio-video/v2` 完全由该独立 skill 维护。旧 `app-audio-video/v1` 与改名前的
`n2d-audio-video/v1`、中间命名 `app-n2d-audio-video/v1` 均为 legacy alias，仅用于迁移兼容读取，不是正式 skill 名称，
迁移时旧 accepted 降为 `machine_complete` 并保留旧证据。

## 核心字段

- `steps.audio / plan / generation`：三步状态。
- `audio.path / sha256 / format / duration / analysis_mode`：真实输入与分析精度。
- `timeline[]`：`id / start / end / energy / visual / cut`。
- `visual.style / subject / camera / reference_path / reference_sha256 / forbidden`。
- `generation.model / channel / aspect_ratio / resolution / count`。
- `job.audio_sha256 / timeline_sha256 / prompt / status`。
- `output.path / sha256 / review / acceptance_receipt / beat_sync_notes`。

非 WAV 输入无法用标准库读取时长时，`analysis_mode=unavailable` 且 `audio` 步保持 active；用户或适配后端补充真实时长后才能 `prepare`。
机器只能写 `machine_complete`。完成还要求脚本读取当前视频并核 SHA，以及具名真人、带时区、
绑定 audio/timeline/output SHA 的 `current_artifact_bytes` 回执；`accept-output` 提供可审计写入动作。
