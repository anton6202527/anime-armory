# Script workbench v3 schema

`app-script-workbench/v3` 是画布故事制作的独立真值格式，不是任何系列的 storyboard。
旧 `app-script-workbench/v1/v2`、`n2d-script-workbench/v1` 与中间命名
`app-n2d-script-workbench/v1` 均为 legacy schema alias，仅用于迁移兼容读取，不是正式 skill 名称或新状态格式；迁移保留路径、SHA、job 和旧回执作
可恢复证据，但旧 `accepted/complete` 一律 fail closed：最多降级为 `machine_complete`，
必须重新取得符合 v3 的真人回执。

## 一个状态

顶层 `state` 是唯一工作流状态：

- `draft`：镜头、最终提示词或真实资产尚未齐备。
- `ready`：当前 authoring 已可生成、重生成或合成。
- `running`：绑定当前内容哈希的 job 正在排队或执行。
- `needs_revision`：当前 job 失败、结果被拒或 QC 阻断。
- `blocked`：硬合规、预算或外部能力闸门阻断。
- `machine_complete`：全部机器产物与 QC 已齐，但还缺最终真人母版验收。
- `complete`：唯一完成谓词全部成立。

`state` 由脚本计算，不接受 UI、模型或人工直接晋升。旧版的 `steps` 在 v3 中不持久化；
界面可以从字段派生阶段进度，但不得把它当第二套状态机。

## 一个内容哈希

`content_sha256` 是 authoring 版本的唯一根哈希。先提取以下字段，再用
`JSON.stringify` 等价规则编码：对象 key 递归排序、UTF-8、`ensure_ascii=false`、紧凑分隔符
`,`/`:`、禁止 NaN/Infinity，最后做 SHA-256。

- `title / global_style / acceptance_policy / delivery_spec`
- `shots[]` 的顺序及除 `color` 外全部制作字段
- `assets[]` 的 `id/kind/name/description/prompt/sha256`

排除 `state/content_sha256/jobs/results/master/qc_receipt/completion`、时间戳、错误、运行进度、
画布布局和 UI 颜色。路径或节点 ID 改变但资产字节 SHA 不变时不会制造新内容版本。

任何 authoring 字段变化都重算根哈希，并把旧 job、结果、母版、QC 收据标为 `stale`。
全局风格可编辑；编辑风格与编辑镜头一样创建新内容版本，不再永久锁死。

## Authoring 字段

- `shots[]`：`id/duration/visual/scale/lighting/dialogue/sound/camera/final_prompt/color`；
  `duration` 为 5–15 秒，顺序就是最终剪辑顺序。
- `assets[]`：`id/kind/name/description/prompt/status/source/sha256`，可附
  `path/attachmentId/nodeId/imageUrl/mimeType/error`。`machine_complete/accepted` 必须同时有 64 位内容 SHA 和
  可持久来源；仅 `blob:` URL 不算跨刷新证据。本地 `path` 的当前字节必须匹配 SHA。
- `delivery_spec`：`container/mime_type/aspect_ratio/resolution/require_audio`。
- `acceptance_policy`：`delegated | human`，默认 `delegated`；它只控制自动化策略，不降低真人验收硬边界。

`delegated` 只允许制作代理依据真实文件和 QC 推进到 `machine_complete`，不得签
`accepted/complete`。图片 `accepted` 与最终母版 `complete` 始终要求具名真人回执。

## 运行证据

### `jobs[]`

每项至少有 `id/kind/input_sha256/status`，镜头任务另带 `shot_id`。`kind` 为
`asset_image | shot_image | shot_video | master`；`status` 为
`draft | ready | queued | running | succeeded | failed | cancelled | blocked | stale`。
job 是运行证据，不是第二个项目状态。

### `results[]`

每个最终采用的镜头视频记录：

- `shot_id / input_sha256 / path / sha256`
- `review: pending | machine_complete | accepted | rejected | stale`
- `machine_receipt`：可由 delegated agent 签 `pass`，绑定内容 SHA、输出 SHA、checks 与 blocks。
- `acceptance_receipt`：仅真人签收；除内容/输出 SHA、criteria/blocks 外，必须有具名
  `reviewer_name`、带时区 `reviewed_at` 与 `confirmation`（`kind=current_artifact_bytes`、
  同一 artifact SHA、`current_pixels_reviewed=true`、`decision=accept`、非空 statement）。

`machine_complete` 必须绑定当前根哈希、当前真实视频字节与机器检查；delegated 回执不能伪装真人接受。

### `master` 与 `qc_receipt`

`master` 用 `status/input_sha256/path/sha256/mime_type/duration` 记录最终母版；只有真实文件的
当前字节 SHA 匹配时才可为 `machine_complete`。

`qc_receipt` 用 `verdict/reviewer_kind/content_sha256/master_sha256/checks/blocks` 记录最终 QC；
`pass` 必须同时绑定当前内容哈希与母版 SHA、checks 非空且 blocks 为空，并必须提供
`receipt_path/receipt_sha256`。Python 执行端会重新读取 `receipt_path` 的当前文件字节并核对
`receipt_sha256`；浏览器端必须保存等价的 durable byte verification，路径或 SHA 字符串本身
不构成通过证据。`final_acceptance_receipt` 与上面的真人回执同构，
必须精确绑定当前内容哈希和当前母版 SHA；机器 QC 不等于最终接受。

## 唯一完成谓词

`completion.definition` 固定为 `app-script-workbench/final-master/v2`。只有同时满足以下全部
条件，脚本才派生 `state=complete`：

1. 镜头制作字段、最终提示词、交付规格完整；所有保留资产均绑定当前真实内容 SHA。
2. 每张保留资产图片均有当前真实字节和严格真人 current-pixel receipt；每个保留镜头至少有
   一个绑定当前哈希与真实字节的 `machine_complete` 视频。
3. 没有绑定当前哈希且仍 queued、running 或 blocked 的 job。
4. `master` 绑定当前内容哈希，真实母版字节 SHA 匹配。
5. `qc_receipt=pass`，同时绑定当前内容哈希和母版 SHA，且没有任何 block。
6. `final_acceptance_receipt=accepted`，由具名真人带时区显式确认并绑定当前母版精确 SHA。

`complete` 命令只检查这个谓词；缺任何证据即非零退出并列出 gaps，不补假文件、不伪造签收。
