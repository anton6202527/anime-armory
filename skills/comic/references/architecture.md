# comic 架构与 MVP 口径

## 设计结论

漫画线应该以 `panel/格` 为最小生产单位，而不是以视频镜头为单位。镜头强调时间、运动和音画，漫画强调阅读顺序、版面节奏、留白、气泡位置和单格信息密度。

源本不是硬前置。更稳的源头结构是：

- `story_bible`：世界观、角色、关系、题材承诺、画风。
- `chapter_outline`：本话目标、冲突、转折、收束、钩子。
- `panel_script.json`：逐格叙事功能、画面、角色、台词、旁白、拟声词。
- `name_board.json`：传统ネーム/缩略分镜，先定页流、格子轻重、翻页钩子、气泡优先级和原稿安全框。
- `layout.json`：页或条漫分段、每格坐标、阅读顺序、气泡占位。
- `finishing_plan.json`：墨线、黑场、网点/灰阶、效果线、漫符和手绘拟声词计划。

完整小说适合做“源本改漫画”，但原创漫画可以直接从蓝图和分话大纲开始。已有对白脚本也可以直接转为分格脚本。

## 推荐流程

1. 源本/点子/脚本进入 `源本/`，写 `_meta.json` 记录来源和权利状态。
2. `comic-script` 产 `设定库/story_bible.md`、`脚本/第N话/分话大纲.md`、`panel_script.json`。
3. `comic-name` 产 `排版/第N话/name_board.json` 和 SVG 缩略分镜，把传统漫画的ネーム层前置。
4. `comic-layout` 产 `排版/第N话/layout.json`，决定页漫或条漫、阅读方向、格子比例、气泡占位，并继承 name board 的原稿安全框、页侧、翻页钩子和气泡优先级。
5. `comic-finishing` 产 `出图/第N话/finishing/finishing_plan.json`，把墨线、黑场、网点/灰阶、效果线、漫符和拟声词画法写成出图可消费的契约。
6. `comic-image` 先补 `出图/共享/` 角色、场景、道具参考，再产逐格 prompt/job 包和图像登记；job 必须消费 `panel_script.json` 的视觉一致性契约（角色完整性、视线目标、场景布局、光位/冷暖、轴线视线）和 `finishing_plan.json` 的传统原稿契约。
7. `comic-compose` 根据 `layout.json`、面板图和 `lettering.json` 嵌字，导出页面图、长图和 manifest。
8. `comic-review` 审阅读顺序、遮挡、文字密度、角色一致性、传统工艺层、改编取舍、平台规格，再生成返修清单。

## MVP 边界

轻量 MVP 只要求跑通“文档契约 + 目录骨架 + 进度扫描 + 导出 manifest/可选长图”。

必须有：

- `comic` 总调度与项目初始化脚本。
- `comic-progress` 只读进度扫描脚本。
- `comic-script`、`comic-name`、`comic-layout`、`comic-finishing`、`comic-image`、`comic-compose`、`comic-review` 的 SKILL.md 交付契约。
- `comic-compose/scripts/export_longstrip.py`：读取 layout 和面板图，写导出 manifest；安装 Pillow 时可选渲染单张长图，显式设置分段高度时才切分。

MVP 之后继续增强：

- 自动出图后端适配层。
- 更强像素级角色/场景一致性机检（当前已有共享参考、视觉契约、风格/角色并排报告和启发式指纹；后续可接 VLM/人脸 embedding/深度布局检测，但不得降低现有 gate）。
- 更强传统原稿审美机检：版面流向、黑白灰价值、网点密度、效果线方向和拟声词融入度可逐步从 warn 升级为项目可选硬闸。
- 大规模批跑、更新影响扫描、投放数据回灌。
- 富交互排版 UI。

## 长图策略

默认不要只输出一张超高长图。推荐同时输出：

- `排版/第N话/pages/`：页漫或审查分页。
- `排版/第N话/长图/longstrip.webp`；显式分段时输出 `part_001.webp` 等分段长图。
- `排版/第N话/export_manifest.json`：记录图片顺序、尺寸、缺失、导出参数。

这样更容易适配移动端、平台上传限制和局部返修。

## 文字策略

不要让图像模型直接生成中文台词正文。推荐：

- 面板图只画无字画面和低细节留白区域；不要把对白气泡、空白气泡、旁白框或文字框烘焙进图像。
- 台词、旁白、拟声词进入 `lettering.json`。
- 项目 `_设置.md` 的 `文字语言` 默认 `中文`，可选 `英文`、`中上英下`、`英上中下` 或 `自定义语言(...)`。
- 合成阶段用 SVG、HTML canvas 或 Pillow 渲染文字，再贴到页面或长图。

这样中文更清晰，错字可改，审稿和本地化也更容易。
