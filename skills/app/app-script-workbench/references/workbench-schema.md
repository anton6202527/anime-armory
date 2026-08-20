# Script workbench schema

`app-script-workbench/v1` 是画布脚本工作台自己的交换格式，不是 `n2d-script` 的
`storyboard.json`。改名前的 `n2d-script-workbench/v1` 与中间命名
`app-n2d-script-workbench/v1` 只作为兼容输入读取，下次写回时迁移。

## 顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema` | string | 固定为 `app-script-workbench/v1` |
| `skill` | string | 固定为 `app-script-workbench` |
| `title` | string | 脚本标题 |
| `global_style` | string | 合成全部镜头提示词的风格前缀 |
| `style_locked` | boolean | 首次合成提示词后持久锁定全局风格 |
| `steps` | object | `shots/assets/prompts` 三步状态 |
| `shots` | array | 可编辑镜头行 |
| `assets` | array | 角色、场景、道具资产卡 |

## 镜头

每个 `shots[]` 必须有稳定 `id`，以及 `duration / visual / scale / lighting / dialogue / sound / camera / final_prompt / color`。`duration` 必须在 5–15 秒之间；修改除 `color` 外的任何字段后清空 `final_prompt`。

## 资产

每个 `assets[]` 必须有 `id / kind / name / description / prompt / status / source`。

画布可同时保留 `attachmentId / nodeId / imageUrl / mimeType / error`。这些字段是跨刷新、跨设备证明真实图片来源的证据，CLI 归一化时必须原样保留，不能只留下抽象状态。

- `kind`: `character | scene | prop`
- `status`: `pending | generating | ready | failed`
- `source`: `none | ai | canvas | upload`

`ready` 只表示工作台已有可引用图片；必须至少存在 `attachmentId`、`nodeId` 或受支持的 `imageUrl`，否则不得写 `ready`。

## 三步状态

- `shots`: 镜头数组非空且必填字段齐全时为 `done`。
- `assets`: 所有保留资产均为 `ready` 时为 `done`。
- `prompts`: 所有镜头 `final_prompt` 非空时为 `done`。

状态只能取 `pending | active | done`。批量生视频按钮要求三步全部为 `done`。
