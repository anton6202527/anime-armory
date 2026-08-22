# Character turnaround schema

`app-character-turnaround/v2` 是该独立 skill 的状态格式。旧 `app-character-turnaround/v1` 与改名前的
`n2d-character-turnaround/v1`、中间命名 `app-n2d-character-turnaround/v1`
均为 legacy alias，仅用于迁移兼容读取，不是正式 skill 名称；旧 accepted 降为 `machine_complete` 并保留旧证据，绝不自动完成。

## 顶层

| 字段 | 说明 |
|---|---|
| `schema` / `skill` | 固定版本与 skill 名 |
| `title` | 工作台标题 |
| `steps` | `source / identity / generation` 三步状态 |
| `source` | `status / kind / path / sha256` |
| `character` | 名称、可见身份事实和不得漂移项 |
| `generation` | 模型、渠道、比例、分辨率、统一负向约束 |
| `views` | `front / left_profile / back` 三个视角 |

## 完成条件

- `source=done`：存在真实参考路径与 SHA-256，或明确使用纯描述模式且角色身份字段齐全。
- `identity=done`：`name`、`face`、`hair`、`body`、`outfit` 非空。
- `generation=done`：脚本真实读取 front / left_profile / back 三个当前文件并核 SHA；三张各自
  有具名真人、带时区、绑定 source/view/output SHA 的 `current_artifact_bytes` 回执。

视图状态为 `pending | ready | machine_complete | accepted | rejected | stale`；步骤状态为
`pending | active | done`。`prepare` 只创建 job；`accept` 一次真人动作会逐张核字节并写三张独立回执。
