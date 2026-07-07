---
name: comic
description: 画漫画生产线总调度。Use when the user wants to create a comic, manga, manhua, webtoon, long-scroll comic, panel script, page layout, comic art prompts, character consistency, shared references, lettering, export, batch panel generation, rerolling panels, or adapt a source story or idea into comics. It initializes or inspects projects under 创作区/画漫画, reads _进度.md, and routes to comic-script, comic-layout, comic-identity, comic-image, comic-batch, comic-compose, comic-review, or comic-progress. Triggers 画漫画, 漫画, 条漫, 页漫, 分格, 分镜, 故事板, panel, storyboard, 定妆, 脸漂, 角色一致性, 嵌字, 气泡, 长图, 漫画出图, 漫画批跑, 重抽漫画格, comic.
---
> 规模统计：Skill 数 10 | SKILL.md 总行数 723 | 目录文本总行数 8008

# comic — 画漫画生产线总调度

把一个故事源、点子或已有脚本做成可发布的漫画。产物落在 `创作区/画漫画/作品名/`，最小闭环是：源本/企划 → 漫画脚本 → 页面/条漫排版 → 出图包 → 面板图 → 嵌字合成 → 审查。

comic 是总调度，不直接替代阶段 skill。它负责定位作品根、读 `_进度.md`、解释流程、初始化轻量项目骨架，并把下一步路由给 `comic-script` / `comic-layout` / `comic-identity` / `comic-image` / `comic-batch` / `comic-compose` / `comic-review` / `comic-progress`。

详细结构见 `references/architecture.md`；选择点和私有偏好见 `references/选择点与偏好.md`；基础视觉风格候选见 `references/视觉风格候选.md`。

## 输入模式

不要强制要求先写完整小说。comic 支持三种入口：

- `源本改漫画`：已有小说、故事梗概、口述稿、短剧本或世界观资料，先做改编取舍。
- `原创漫画`：只有题材、主角、爽点或画面想法，先建立故事蓝图和角色设定，不要求散文源本。
- `脚本改漫画`：已有对白/场景脚本，直接转为分话大纲和分格脚本。

漫画的主真值不是 clip，而是 `panel/格`。推荐层级是：

```
话 chapter -> 页 page 或 scroll_segment -> 格 panel
```

## 偏好

本线不写死平台、模型、画幅或导出格式。先读项目 `_设置.md`；缺失时读用户私有全局默认；仍缺失时首次询问并写回 `_设置.md`。合规、不可逆、会产生费用的步骤每次重新确认。

核心选择点：`输入模式`、`漫画形态`、`阅读方向`、`目标平台`、`基础视觉风格`、`风格锚`、`页面尺寸`、`单话分段高度`、`生图模型`、`生图渠道`、`参考一致性策略`、`定妆级别`、`年龄形态继承`、`角色一致性硬闸`、`文字语言`、`嵌字方式`、`导出格式`、`发行地区`、`合规用途`。具体说明见 `references/选择点与偏好.md`。

## 项目骨架

```
创作区/画漫画/作品名/
├── _进度.md / _设置.md / _meta.json
├── 源本/                    原始故事、梗概或脚本
├── 设定库/                  story_bible、角色卡、场景卡、道具卡、style_guide
├── 脚本/第1话/              分话大纲.md、panel_script.json
├── 排版/第1话/              layout.json、lettering.json、pages/、长图/
├── 出图/共享/               identity_registry、角色/场景/道具参考与 prompt 包
├── 出图/第1话/panels/       每格图像
└── 生产数据/                manifest、审查报告、导出记录
```

初始化：

```bash
python3 skills/comic/scripts/init_project.py "创作区/画漫画/作品名" --title 作品名 --mode 原创漫画
```

若已有源文件：

```bash
python3 skills/comic/scripts/init_project.py "创作区/画漫画/作品名" --title 作品名 --mode 源本改漫画 --source path/to/source.md
```

## 阶段路由

| 阶段 | skill | 产物 |
|---|---|---|
| 调度/立项 | `comic` | `_设置.md`、`_进度.md`、`_meta.json`、目录骨架 |
| 漫画脚本 | `comic-script` | `分话大纲.md`、`panel_script.json`、角色/场景/道具设定草案 |
| 页面排版 | `comic-layout` | `layout.json`，含 page/scroll_segment/panel 坐标、阅读顺序、气泡占位 |
| 一致性资产 | `comic-identity` | `identity_registry.json`、共享锚点、引用绑定、重抽计划 |
| 出图包/出图 | `comic-image` | 逐格 prompt/job 包、真实参考图入参、`panels/*.png` 登记 |
| 流程批跑 | `comic-batch` | 从当前前沿调用阶段脚本；出图阶段支持多抽、重抽指定格和候选归档 |
| 嵌字/导出 | `comic-compose` | `lettering.json`、页面图、长图、导出 manifest |
| 审查 | `comic-review` | 阅读顺序、文字遮挡、角色一致性、源本改编、导出规格问题清单 |
| 进度 | `comic-progress` | 只读扫描 `_进度.md`，给下一步建议 |

## 调度规则

- 用户给作品根或 `_进度.md`：先跑 `comic-progress` 或直接读 `_进度.md`，再按当前前沿路由。
- 用户只有故事点子：用本 skill 初始化 `原创漫画`，下一步 `comic-script`。
- 用户给源本、小说、梗概或剧本：初始化 `源本改漫画` 或 `脚本改漫画`，下一步 `comic-script`。
- 用户问“长图怎么出 / 怎么嵌字”：路由 `comic-compose`。
- 用户问“画面图怎么生成 / prompt 怎么写”：路由 `comic-image`。
- 用户问“角色不像 / 换脸 / 定妆 / 共享参考 / 出图一致性”：路由 `comic-identity`；修完后再回 `comic-image` 重抽受影响格。
- 用户确认了预算和覆盖范围，要求“批量出图 / 抽到满意为止 / 重抽几格 / 继续推进”：路由 `comic-batch`。
- 用户问“是不是能发 / 读起来顺不顺”：路由 `comic-review`。

## 核心原则

- 源本可选，故事蓝图和分格脚本必需。
- 面板图尽量不直接生成台词；台词、旁白、拟声词通过 `lettering.json` 后期嵌字，`文字语言` 默认中文，可选英文或中英双语上下排版，保证清晰、可改、可审。
- 默认按长线连载口径做角色定妆：常驻角色进入批量生产前补专门定妆和多视图；短 demo 才显式改成锚点过渡。
- 用户提供的定型图必须写入 `identity_registry.json` 的角色 DNA / 禁漂移项；同一角色的少年、成年、受伤、觉醒、换装等形态只允许继承性变化，不得换脸或换画风。需要高一致性长线口径时，`comic-review` 把风格锚、年龄形态继承和多视图缺口作为硬闸。
- 长图默认导出单张和 manifest；发布平台要求固定高度时再按 `单话分段高度` 或平台规则切分。
- 出图阶段只产 job 包和登记结果，不假设某个后端一定可用；具体模型和渠道来自 `_设置.md` 与阶段确认。
- 每个推进阶段完成后回写 `_进度.md`，只读阶段不得回写。

## 不做什么

- 不把漫画项目硬绑定到完整小说源本。
- 不把视频镜头逻辑直接套到漫画分格。
- 不在生成图像里直接烘焙正文台词，除非用户明确选择且愿意承担返工成本。
- 不替用户自动执行付费出图或覆盖已发布导出物。
