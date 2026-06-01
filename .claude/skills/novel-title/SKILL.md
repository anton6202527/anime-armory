---
name: novel-title
description: Brainstorm 5–8 book title candidates for a novel project, ranked by 5-dim scoring (hook / platform-fit / character identity / anti-collision / memorability). Supports major Chinese web/comic-drama platforms (起点 / 番茄 / 晋江 / 抖音漫剧 / 红果 / 历史向 / 跨平台). Use when asked to 起书名, 测书名, 取书名, 想几个书名, 给个好名字, brainstorm book titles. Can be invoked standalone or by other novel-* skills (novel-spinoff Step 3, novel-expand, novel-condense). Triggers 起书名, 测书名, 取书名, 改书名, 书名候选, 取个名字.
---

# novel-title — 书名候选 + 平台对位评分

输入一个小说项目的**核心设定**（角色 / 类型 / 视角 / 目标平台），输出 5–8 个候选书名 + 5 维评分排名 + 推荐 + 备选 + 一句话定位。

可独立调用，也可被其他 skill 在内部某一步调起。

## 输入

至少需要：
- **目标平台**：起点 / 番茄 / 晋江 / 抖音漫剧 / 红果 / 历史向 / 跨平台
- **主角 / 核心人物名**（如有）
- **类型 / 钩子**（修真 / 都市 / 历史 / 同人外传 / 等）
- **可选**：用户已有的**暂定名**（作为候选 #0 一并打分）

## 工作流

1. **核对输入**：缺哪条问哪条。
2. **生成 5–8 个候选**：按 `references/title-patterns.md` 的配比（主推平台 2-3 + 跨平台稳健 1-2 + 高钩子尝试 1-2 + 保守雅名 0-1 + 用户暂定 0-1）。
3. **5 维评分**：钩子 / 平台契合 / 角色识别 / 抗撞名 / 可记忆性，各 1-5 分，满分 25。
4. **排表 + 推荐**：按总分降序；给一句话定位；标"我推" + "备选 A / B" + 弃用说明。
5. **用户选定**：用 AskUserQuestion 给前 4 名让用户选。
6. **回写**：
   - 如果项目目录已存在（被其他 skill 调起时），把书名写进项目 `_meta.json.title` 并在 `设定/书名候选.md` 留底。
   - 否则只在主对话报告。

## 输出

- `设定/书名候选.md`（如果有项目目录）—— 评分表 + 推荐 + 弃用说明
- 主对话报告：表格 + 推荐 + AskUserQuestion 让用户选

## 评分规则、平台命名习惯、配比要求

详见 `references/title-patterns.md`。

## 何时不用本 skill

- 用户已经定死了书名 → 不需要候选
- 项目还在第 0 / 1 步（连人物设定都没建）→ 太早；先把人物 / 设定卡建出来再回来取名

## 常见错误

| 错误 | 纠正 |
|---|---|
| 没问目标平台就拍 5 个候选 | 不同平台命名习惯差异极大；先问平台 |
| 5 个候选都同一类钩子 | 要覆盖 5 种钩子方向，对照评分才有意义 |
| 给的候选撞名严重 | 抗撞名是 5 维之一；明显撞名直接淘汰，不进表 |
| 被 spinoff 调起却没回写 _meta.json | 一定要更新 _meta.json.title，否则 export 时会回退到默认名 |
