# mv-video Q&A

## Q1: MV 系列如何保证 clip 之间衔接顺畅？

A: MV 的 clip 衔接强调"视觉身份一致 + 卡点落点准 + 动作/视线/道具可切"。因此每个 MV clip 必须增加 `continuity` 字段，并同时读取相邻 clip、`beatgrid.json`、段落张力和歌词钩子。

每个 clip 必填 5 个字段：

- `start_state`：承接上一 clip 末尾/本 clip 首帧的人物姿态、站位、视线、道具状态、场景状态。
- `action`：本 clip 内唯一主动作链，动作峰值或镜头冲击点对齐指定 beat/downbeat。
- `end_state`：给下一 clip 承接的结尾姿态、视线方向、画面重心、道具特写、光效或空镜落点。
- `constraints`：角色定妆、服装发型、主色调、光线、天气、道具、背景布局、轴线/屏幕方向在同段落内保持一致。
- `negative`：不要换脸、不要换衣、不要新增人物、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要生成原生人声。

MV 版落地规则：

1. `clip 时长` 仍由 `beatgrid.json` 决定，不因为连续性改成等长。
2. `action` 的峰值对齐 beat/downbeat，尤其副歌高光、拔剑、回眸、光效爆点。
3. 同一段落尽量保持角色、服装、主色调、场景光线一致；跨段落可以换场景，但角色定妆和核心道具保持。
4. 接不住时优先用动作切、视线切、道具特写、光效切、遮挡擦镜、空镜缓冲，不要让视频模型硬做复杂连续动作。
5. 视频模型生成原生音频一律禁止，音乐和歌词字幕由 `mv-compose` / `mv-lyric-sync` 使用原歌轨统一处理。

本规则已写入：

- `skills/mv/mv-video/SKILL.md`
- `skills/mv/mv-video/references/prompt_format.md`

## Q2: 一键式流程怎样处理选择、预算和人审？

A: mv 当前没有完整 `mv-batch` / supervisor。项目初始化后，外层 agent 消费 `mv/run.py next --json`，可自动串联免费确定性 helper 并路由到已有 `mv-*` skill；导航层不代替 provider 提交或人审。缺 `_进度.md` 时，当前 setup card 是 legacy 占位且命令不完整，必须先显式运行 `init_project.py --title ... --out ... --song-timing ...`，不能直接执行该 card。

- 外层 agent 看到最终音频时应显式传入并写回 `先传音乐`，只有企划/歌词草稿时显式传入 `后配歌曲`；底层 init CLI 不自行推断，未传参数仍采用兼容默认 `先传音乐`。其它普通缺项采用推荐值、写回 `_设置.md` 后继续。
- 实际调用层若已有与当前 input/model/channel/scope/cost 精确绑定且有效的阶段预算包，余量内不逐图、逐 clip 重复确认；缺失、扩大、过期或合同变化才结构化停止。
- 当前像素、当前视频 take、timing/picture lock、最终母版验收，以及版权/肖像/品牌合规和不可逆发布/覆盖仍是硬边界，不能用代理推荐冒充。
