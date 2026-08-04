---
name: n2d-script-workbench
description: 独立的画布故事脚本工作台，把故事梗概或剧情片段整理成可编辑镜头表、角色/场景/道具资产清单和最终视频提示词，并导出批量视频任务。Use when a user clicks 故事脚本生成, 脚本生成器, 确认镜头, 准备资产, 合成提示词, 一键生成所有资产, 批量生视频, or asks to reproduce/operate the LibTV-style three-step script workbench. This skill is canvas-oriented and must not import, invoke, or depend on n2d-script.
---

# n2d-script-workbench

把画布中的“故事脚本生成”作为一条独立、可暂停、可编辑的三步工作流执行。不要调用 `n2d-script`，也不要读取它的脚本、合同或项目进度。

## 独立边界

- 只读用户本轮提供或画布引用的故事、角色、图片和视频。
- 把状态写入自己的 `*.script-workbench.json`，不修改 n2d 的 `_进度.md`。
- 只运行本目录 `scripts/workbench.py`；不得 import `skills/n2d/n2d-script` 或其它生产线实现。
- 如需进入完整制漫剧生产线，只把已确认的工作台 JSON 作为用户显式选择的文件交接；缺少交接不影响本 skill 使用。

## 工作流

### 0. 生成脚本结果

1. 读取故事梗概、剧情片段和画布引用。
2. 生成标题、全局风格、镜头、角色、场景和道具候选。
3. 用 `scripts/workbench.py init` 归一化为工作台 JSON。
4. 在画布创建结果节点；节点只显示标题、三步状态和“打开脚本节点”。

### 1. 确认镜头

- 展示镜号、时长、画面描述、景别、光影氛围、对白/旁白、音效、运镜、最终提示词和操作。
- 允许逐格编辑；内容变化后将该镜头的最终提示词置为待重新合成。
- 行菜单仅提供颜色标记与删除；允许底部新增镜头。
- 在用户确认前不生成图片或视频。

### 2. 准备资产

- 按角色、场景、道具分组展示资产卡。
- 每张卡支持选择图片、AI 生成、本地上传、跳转节点、清除图片和删除。
- 单项生成弹框提供 `AI生成 / 从当前画布选择 / 本地上传` 三个页签。
- 批量生成弹框允许逐项勾选和编辑提示词，并显示模型、画质、分辨率、比例、预计成本和生成数量。
- 生成动作涉及真实付费后端时，每次都在提交前让用户确认；没有后端时保留可续跑 job 包。

### 3. 合成提示词

- 将全局风格与镜头的景别、画面、光影、对白、音效和运镜合成为最终提示词。
- 支持一键合成全部、查看单镜头、编辑、复制和重新合成。
- 全部镜头完成后才启用批量生视频；批量动作创建独立视频任务节点，不直接宣称已有视频。

## AI 代理交互节点

- 故事语义不完整时，只问一个能改变镜头结果的关键问题；其余按合理默认继续。
- 资产提示词和最终镜头提示词由代理自动补齐，不要求用户复制脚本命令。
- 任何真实积分、付费生成、覆盖已有资产或批量视频提交都必须停下确认。

## 状态与验证

按 [workbench-schema.md](references/workbench-schema.md) 维护数据。常用命令：

```bash
python3 skills/n2d-script-workbench/scripts/workbench.py init \
  --input story.json --output story.script-workbench.json

python3 skills/n2d-script-workbench/scripts/workbench.py compose \
  story.script-workbench.json --write

python3 skills/n2d-script-workbench/scripts/workbench.py validate \
  story.script-workbench.json
```

验证失败时保留原文件，报告缺失字段和具体镜头/资产 id；不要用空字符串伪装完成。
