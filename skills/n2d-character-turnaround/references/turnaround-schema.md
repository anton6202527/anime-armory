# Character turnaround schema

`n2d-character-turnaround/v1` 是该顶层 skill 的独立状态格式。

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
- `generation=done`：三个视图都有真实输出路径与 SHA-256，且 `review=accepted`。

视图状态为 `pending | ready | accepted | rejected`；步骤状态为 `pending | active | done`。`prepare` 只创建 job，不改变真实输出状态。
