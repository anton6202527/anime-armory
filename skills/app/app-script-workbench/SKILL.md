---
name: app-script-workbench
description: 独立的画布故事制作工作台，把故事整理成可编辑镜头与资产，并在同一画布持续生成、返修、质检和合成为最终母版。Use when a user asks for 故事脚本生成, 画布二次创作, 一键生成所有资产/镜头, 批量生视频, 画布成片, or final master from the canvas. This canvas skill owns its v3 state/hash/completion contract and must not depend on a series implementation.
---

# app-script-workbench

把画布作为从故事到最终母版的独立制作工作台。唯一业务真值是当前
`*.script-workbench.json`：一个 `state`、一个 `content_sha256`、一个完成定义。

## 独立边界

- 只运行本目录 `scripts/workbench.py`，不读取、import 或调用任何系列实现、`_进度.md` 或私有合同。
- 对外只以文件、JSON job/receipt 和真实媒体交接；缺后端时仍保留绑定当前哈希的 job 包。
- 画布布局、临时进度、时间戳和 UI 颜色不是业务真值，不进入内容哈希。

## 默认执行

1. 从故事和画布引用生成镜头、资产候选与交付规格，运行 `init`。
2. 自动补齐资产提示词和镜头最终提示词；资产必须绑定真实来源与内容 SHA-256。
3. 所有 job 都绑定当前 `content_sha256`，依次生成资产、镜头视频、母版并登记真实输出。
4. 制作代理可依据真实文件与 QC 把镜头视频推进到 `machine_complete`，但不得签 `accepted`；每张保留图片必须由具名真人查看当前像素，回执精确绑定当前文件 SHA。
5. 母版与 QC 通过后先到 `machine_complete`；只有具名真人对当前母版作带时区、精确绑定字节 SHA 的最终显式验收，唯一完成谓词才允许 `state=complete`。

用户编辑镜头、顺序、风格、资产内容或交付规格时，重新计算内容哈希并自动把旧
job、结果、母版与 QC 标为 `stale`。全局风格不再永久锁死；修改风格就是一次可追溯的新版本。

## 停点

- 普通创作选择按推荐方案继续；语义缺口只问一个确实会改变成片的问题。
- 已授权预算包内的普通生成和机器检查不逐项暂停；delegated 证据只能到 `machine_complete`。
- 逐图当前像素验收与最终母版验收是硬边界；不得由 agent 自动填写 human receipt。
- 仅硬合规、超出预算包、不可逆发布或覆盖已验收母版时暂停确认；不得用确认绕过 SHA/QC 完成条件。

## 命令

完整字段和完成谓词见 [workbench-schema.md](references/workbench-schema.md)。

```bash
python3 skills/app/app-script-workbench/scripts/workbench.py init \
  --input story.json --output story.script-workbench.json
python3 skills/app/app-script-workbench/scripts/workbench.py compose story.script-workbench.json --write
python3 skills/app/app-script-workbench/scripts/workbench.py status story.script-workbench.json --write
python3 skills/app/app-script-workbench/scripts/workbench.py validate story.script-workbench.json
python3 skills/app/app-script-workbench/scripts/workbench.py complete story.script-workbench.json --write
```

`complete` 只验收现有证据，不生成或伪造收据。验证失败时保留原文件并报告具体路径。
