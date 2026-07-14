---
kind: n2d_project_implementation_plan
version: 1
status: ready_for_human_gates
updated_at: 2026-07-14
---

# 《从变身少女开始斩妖除魔》实施与验收计划

## 当前结论

- 文本开发准备已完成：源书完整性审计、源理解合同、视觉竞品研究、风格合同、角色圣经、剧级一致性合同、P-1 五件套和首批拆集候选均已落盘。
- 长篇 `split_plan` 已安全迁移为 compact schema v3；计划文件缩小 92.53%，10 个 raw、拆集复核、进度文件及生产语义均由迁移收据证明未变。
- 付费图片、视频、声音和公开发布保持阻断：源文本权与改编权尚未确认；两张用户参考含水印且来源/后端使用权未确认。
- 不把当前机器 raw 当正式拆集。首批推荐第1–10集对应原著第1–18章，必须在边界人工签收后统一重建。

## 阶段与放行条件

| 阶段 | 交付 | 放行条件 | 当前状态 |
|---|---|---|---|
| G0 权利与边界 | compliance_manifest、参考图 manifest、同 IP 去重边界 | source_text/adaptation 有可核验证据；水印参考仍为 analysis_only | BLOCK |
| G1 P-1 开发 | series bible、改编策略、季弧、可制作性、试播绿灯 | creative 与 producer 对当前哈希分别签收 | 待人工签收 |
| G2 拆集 | 第1–10集章号/source-unit/钩子映射 | 用户/导演签收《_拆集复核.md》；按签收方案重建 raw 并生成 applied receipt | 待人工签收 |
| G3 剧本 | 第1–3集阶段1/2、table read、改编差异 | 每集承诺—阻碍—兑现—尾钩完整；150–210秒候选经实读确认 | 未开始 |
| G4 共享资产 | 风格锚、姜月初常态/妖化、百妖谱、横刀、核心场景 | 权利通过；两个主角形态各自完成 core_full 五角与当前像素收据 | BLOCK |
| G5 高风险样片 | 杀裴长青→斩虎、首次录谱、虎妖化、朱厌战 | 身份、动作因果、力量阶段、尺度、VFX与声音全部通过专项 gate | 未开始 |
| G6 第1集成片 | 完整声音/图/视频/合成/终审 | 所有核心 BLOCK 清零；占位音替换；无水印/竞品复制；合规与发布意图匹配 | 未开始 |
| G7 小批量 | 每批最多3集 | 第1集与高风险样片通过；每批 script/image/video/compose/review 留审点 | 未开始 |

## 立即执行顺序

1. 权利人确认源文本与改编授权范围；若存在既有《万妖图录传/那妖魔是姜大人》漫剧授权，写清本项目可使用与不可使用的资产边界。
2. 用户显式确认一次制作模式；当前推荐并已推断为“混合自动路由”，但推断值不能替代用户首选。
3. 用户批准 P-1 开发包与首批10集边界。批准只代表内容开发，不自动授予参考图上传、真人肖像、音乐、字体或公开发行权。
4. 用 `signoff.py` 由 creative 与 producer 两个职责签收当前 P-1 哈希；任何五件套或源设置变化都会使签收过期。
5. 按《脚本/_拆集复核.md》重建仍为 raw-only 的第1–10集，并保留旧/新 raw SHA、source unit 映射与边界实施收据。
6. 只先制作第1–3集文字链；table read 后锁实际集长。不得用加速念白解决超时。
7. 权利闸门解除后，先做姜月初常态与虎妖化五角，再做第1集完整链路与三类高风险视觉 clip；全部通过才放量。

## 核心验收矩阵

### 源书与拆集

- 相邻重复章名折叠后唯一章节数为819；章号1–830，缺708–717与808；本地源疑似连载中，不能宣称完结全本。
- 2026-07-14 核验的[番茄公开页](https://fanqienovel.com/page/7544766518324644889)已显示约199.4万字、887章（页面更新到2026-07-13）；本地副本止于章号830，属于滞后快照。首批第1–18章不受影响，但进入本地末端窗口前必须重新取得有权使用的最新源并跑 source drift/增量理解，不能从公开页面抓取正文补洞。
- 首批10集只覆盖原著第1–18章；第19–20章作为下一窗口开场。
- 每个边界保存左右 raw SHA、source unit 起止、语义决定和可追责 reviewer；改边界必须有 applied receipt。
- 第1集不得切断“杀裴长青取道行→斩虎→妖血录谱”；第18章单列为身份审判/入司集。

### 人物与多视图

- 姜月初常态和虎妖化是两个独立 `core_full` form，各需 front / three_quarter / side / rear_three_quarter / back、turnaround、全身服装锚、脸/表情锚。
- 五角不能是同图改名、镜像、重编码或软链；除文件 SHA 外还检查解码像素与当前 PNG 绑定的人审收据。
- 常态固定黑发、非金瞳、无虎纹、玄黑赤纹劲装、横刀；妖化才允许血红发、金色竖瞳、手腕至肩臂赤虎纹。
- 用户参考图只贡献冷白清丽骨相、高马尾、黑赤金/水墨志怪的抽象方向；白衣巨毫、金属肩饰、海报卷轴布局、标题、Logo、水印均不得复制。

### 视觉与动作

- 全剧基底为国漫写实人物、粗粝唐代边塞材质、竖屏电影化镜头；百妖谱显化才进入黑墨/朱砂/克制金光副风格。
- 百妖谱固定“妖血为墨→摹影→染朱→点睛→能力反馈”，每镜只承担主要阶段。
- 横刀长度、刀格、缠柄、刀鞘与握法跨镜连续；动作必须有起势、接触、结果和伤势承接。
- 多主体、暗光、血雾、侧背与极端表情属于高风险镜，先补参考或拆层，不以删角色/删剧情规避。

### 声音、字幕与成片

- 剧级真值见 `设定库/series_consistency.json`：canonical name、语域、禁词、字幕安全区、-16 LUFS目标与-1 dBTP峰值。
- 姜月初为十八岁外显女性声线、冷静克制；现代男性意识通过表演和短内心句表达，不做夸张变声笑料。
- 不使用真人克隆；若以后改用参考音，必须另做 opt-in 授权与证据。
- 最终合成不得保留占位音；字幕、台词、镜头时长与最终音轨 SHA 必须一致。

### 合规与去重

- `rights.source_text` 或 `rights.adaptation` 为 unknown 时，内部用途也不得进入付费共享资产或逐集媒体生成。
- 带水印、pending、`backend_upload_allowed=false` 的参考不得进入任何图生图、视频、训练或后端附件。
- 同 IP 市场样本只用于识别观众预期和主动去重，不复制脸、造型、镜头、海报、标题字、Logo、音乐或新增设定。
- 发布前另行确定目标平台/地区，复核字体授权、AI显式/隐式标识、内容分级、备案和平台人工终审。

## 复验命令

```bash
python3 skills/n2d-settings/scripts/settings_cli.py audit "创作区/制漫剧/从变身少女开始斩妖除魔"
python3 skills/n2d-script/scripts/source_language.py "创作区/制漫剧/从变身少女开始斩妖除魔" --json
python3 skills/n2d-script/scripts/boundary_review.py check "创作区/制漫剧/从变身少女开始斩妖除魔" 1-10 --json
python3 skills/n2d-script/scripts/development_pack.py "创作区/制漫剧/从变身少女开始斩妖除魔" check --json
python3 skills/n2d/scripts/series_consistency.py "创作区/制漫剧/从变身少女开始斩妖除魔" 第1集 --phase script --json
python3 skills/n2d-compliance/scripts/compliance.py "创作区/制漫剧/从变身少女开始斩妖除魔" --check --stage image --json
python3 skills/n2d/run.py next "创作区/制漫剧/从变身少女开始斩妖除魔" 第1集 --json
```

预期现状：source/settings/series consistency 通过；boundary 与 P-1 因人工签收待办阻断；compliance 因 source_text/adaptation 未确认阻断。任何出现“内部用途自动豁免”或“共享资产绕过合规”都视为 skill 回归失败。
