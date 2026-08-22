# First-frame video schema

`app-first-frame-video/v2` 完全由该独立 skill 维护。旧 `app-first-frame-video/v1` 与改名前的
`n2d-first-frame-video/v1` 与中间命名 `app-n2d-first-frame-video/v1`
只作为兼容输入读取；旧 accepted 降为 `machine_complete` 并保留旧证据。

## 核心字段

- `steps.frame / motion / generation`：`pending | active | done`。
- `frame.path / sha256 / description`：真实首帧与可见事实。
- `motion.subject / camera / environment / pacing / forbidden`：分层运动合同。
- `generation.model / channel / duration / aspect_ratio / resolution / count`：模型与渠道分列。
- `job.source_sha256 / prompt / status`：绑定当前首帧的提交任务。
- `output.path / sha256 / review / acceptance_receipt`：当前真实结果、机器完成与真人验收。

`prepare` 只把 `job.status` 置为 `ready`。机器只能写 `machine_complete`。`generation=done` 还要求
脚本读取当前输出并核 SHA，以及具名真人、带时区、精确绑定 input/output SHA 的
`current_artifact_bytes` 回执；`accept-output` 提供可审计写入动作。
