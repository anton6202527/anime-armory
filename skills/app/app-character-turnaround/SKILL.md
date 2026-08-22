---
name: app-character-turnaround
description: 独立的画布角色三视图工作台，从单张角色参考图或角色描述提取身份约束，生成正面、侧面、背面一致的角色设定图任务包，并登记人工验收结果。Use when a user clicks 角色三视图, asks for 正侧背设定图, character turnaround, 三视图角色设定, or needs the LibTV-style source image → identity brief → three-view generation flow. This top-level skill must not import, invoke, or depend on comic-identity, n2d-identity, or any other series skill.
---

# app-character-turnaround

把“角色三视图”作为一条独立、可暂停、可复核的画布工作流执行。只处理本次角色参考与自己的 `*.character-turnaround.json`，不读写任何系列项目状态。

## 独立边界

- 只运行本目录 `scripts/turnaround.py`，只依赖 Python 标准库。
- 不 import、调用或复制 `skills/n2d/`、`skills/comic/` 等系列运行时。
- 可以学习其它 skill 的角色一致性原则，但字段、状态、脚本和产物必须在本目录自洽。
- 如用户之后进入其它生产线，只交付已确认 JSON 和图片文件；缺少交接不影响本 skill。

## 工作流

### 1. 选择角色图

1. 接受本地上传、当前画布图片或 AI 生成候选。
2. 有真实文件时记录规范路径、SHA-256 与来源；没有真实像素时保持 `source.status=pending`。
3. 不把占位缩略图标成已就绪。

### 2. 完善角色设定

从参考图与描述自动提取角色名称、脸型五官、发型发色、体型、服装、配饰和不得漂移项，并保存为可编辑默认。身份约束必须是可见事实，不只写“保持一致”；只有来源互相冲突或缺失项会实质改变角色身份时，才停问一个关键问题。

### 3. 生成与验收三视图

1. 用 `prepare` 生成正面、左侧面、背面三个视角的独立 prompt 和统一 job 包。
2. 把具体生成模型与访问渠道分列；无后端时仍保存 job 包，不宣称已生成。
3. 真实付费提交由宿主在阶段开始时消费已有授权；同一输入 SHA、模型、渠道、数量和费用上限内连续生成三视图，不逐视图重复确认。创建/扩大授权、授权过期或任一绑定变化时才停。
4. 生成后逐视图登记文件与 SHA-256，并人工核对脸、发型、服装、体型、配饰和比例。
5. 机器生成只到 `machine_complete`；三张分别读取当前文件并核 SHA，且都有具名真人、带时区、精确绑定当前图片字节的 current-pixel receipt 后才能完成。

## AI 代理交互节点

- 参考图不清楚时只追问最影响身份的一项；其余先生成可编辑草案。
- 自动把自然语言角色描述拆成结构化身份约束，不让用户手工拼 prompt。
- 创建/扩大/失效的付费授权、覆盖已验收视图或更换已绑定模型时停下确认；有效授权包内不逐视图打断。

## 命令

```bash
python3 skills/app/app-character-turnaround/scripts/turnaround.py init \
  --name "角色名" --source reference.png --output role.character-turnaround.json

python3 skills/app/app-character-turnaround/scripts/turnaround.py prepare \
  role.character-turnaround.json --write

python3 skills/app/app-character-turnaround/scripts/turnaround.py validate \
  role.character-turnaround.json

python3 skills/app/app-character-turnaround/scripts/turnaround.py accept \
  role.character-turnaround.json --reviewer "具名审核人" \
  --statement "我已逐张查看三张当前图片并接受这些确切字节" \
  --confirm-current-pixels --write
```

`accept` 是一次显式真人动作，但会为正面、侧面、背面分别写三张独立回执；runner/agent 不得代填 reviewer 或 confirmation。

字段与完成条件见 [turnaround-schema.md](references/turnaround-schema.md)。验证失败时保留原文件并报告字段路径；不得用空文件、占位图或 `accepted` 文案伪装完成。
