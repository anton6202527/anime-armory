# Script workbench schema

`n2d-script-workbench/v1` 是画布脚本工作台自己的交换格式，不是 `n2d-script` 的 `storyboard.json`。

## 顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema` | string | 固定为 `n2d-script-workbench/v1` |
| `skill` | string | 固定为 `n2d-script-workbench` |
| `title` | string | 脚本标题 |
| `global_style` | string | 合成全部镜头提示词的风格前缀 |
| `steps` | object | `shots/assets/prompts` 三步状态 |
| `shots` | array | 可编辑镜头行 |
| `assets` | array | 角色、场景、道具资产卡 |

## 镜头

每个 `shots[]` 必须有稳定 `id`，以及 `duration / visual / scale / lighting / dialogue / sound / camera / final_prompt / color`。`duration` 为正数；修改除 `color` 外的任何字段后清空 `final_prompt`。

## 资产

每个 `assets[]` 必须有 `id / kind / name / description / prompt / status / source`。

- `kind`: `character | scene | prop`
- `status`: `pending | generating | ready | failed`
- `source`: `none | ai | canvas | upload`

`ready` 只表示工作台已有可引用图片；没有真实图片时不得写 `ready`。

## 三步状态

- `shots`: 镜头数组非空且必填字段齐全时为 `done`。
- `assets`: 所有保留资产均为 `ready` 时为 `done`。
- `prompts`: 所有镜头 `final_prompt` 非空时为 `done`。

状态只能取 `pending | active | done`。批量生视频按钮要求三步全部为 `done`。
