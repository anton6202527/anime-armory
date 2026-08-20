# First-frame video schema

`app-first-frame-video/v1` 完全由该独立 skill 维护。改名前的
`n2d-first-frame-video/v1` 与中间命名 `app-n2d-first-frame-video/v1`
只作为兼容输入读取，下次 `prepare --write` 时迁移为新命名空间。

## 核心字段

- `steps.frame / motion / generation`：`pending | active | done`。
- `frame.path / sha256 / description`：真实首帧与可见事实。
- `motion.subject / camera / environment / pacing / forbidden`：分层运动合同。
- `generation.model / channel / duration / aspect_ratio / resolution / count`：模型与渠道分列。
- `job.source_sha256 / prompt / status`：绑定当前首帧的提交任务。
- `output.path / sha256 / review`：真实结果与人工验收。

`prepare` 只把 `job.status` 置为 `ready`。`generation=done` 需要输出路径、输出 SHA 和 `review=accepted`。
