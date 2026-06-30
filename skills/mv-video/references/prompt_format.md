# mv-video jobs manifest + 卡点定时长 + 运镜映射

## 真值源
- `分镜/clip_plan.json`：clip 时长、首帧路径、尾帧需求、转场、continuity 的源头，由 `mv-plan` 生成。
- `出视频/jobs_manifest.json`：每个 clip 跑几版、prompt 文件、已登记 take、评分、selected_take 的源头，由 `scripts/video_jobs.py` 生成/维护。
- `分镜/timeline_manifest.json`：最终合成顺序和 selected video 路径，由 `mv-plan` 创建、`video_jobs.py --select` 同步。
- `mv-video/references/action_knowledge.md`：动作家族、动作峰值、转场母题的知识库。`clip_plan.json` 中的 `action_family/action_peak/visual_motif/transition_motif` 应从这里选，不临场泛写“炫酷”。

## clip 任务格式（按 clip_plan + beatgrid 规划）
```markdown
## Clip_001（段落 chorus · 时长 1.6s · @0:48-0:49.6）
**首帧**：出图/段落/图片/Clip_001.png
**尾帧**（`need_end_frame=true` 时必用，平台支持双帧走 frames2video）：出图/段落/图片/Clip_001_end.png（mv-image 出的尾帧=下一 clip 首帧构图）
**卡点**：起 0:48(downbeat) → 止 0:49.6(下一downbeat)
**歌词/情绪钩子**：{本 clip 对应歌词词组 / 情绪点 / 爽点}
**转场**：{动作切 / 视线切 / 闪白 / 遮挡擦镜 / 光效切 / 硬切 / 空镜缓冲}
**动作家族**：{performance_pose / expressive_walk / dance_hit / dance_sharp / dance_fluid / dance_street / performance_vocal / camera_whip / orbit_reveal / prop_sync / vfx_burst / environment_motion / mirror_split / silhouette_action}
**力量等级**：{Level 1-10}
**动作峰值**：{对齐 beat/downbeat 的秒点，或相对于 clip 开始的秒点，如 0.8s (relative)}
**空间/轴线锁**：{视线看向镜头 / 运动方向画左至画右 / 保持双脚接触地面}
**视觉母题**：{主角身份锚点 / 主色 / 本段反复符号}
**转场母题**：{闪白 / 遮挡擦镜 / whip pan / match action / match color / particle bridge / mirror fracture / shadow cut}
**need_end_frame**：true/false。
**continuity**：
- start_state：直接抄上一 clip 的 `end_state`
- action：{人物动作 + 力量等级}
- end_state：{给下一 clip 承接的结尾姿态}
- constraints：{角色定妆、服装发型、主色调、空间轴线锁}
- negative：{不要换脸、不要换衣、不要瞬移、不要生成文字/logo、不要生成原生人声}
### 视频 prompt（中文，目标=即梦/可灵/Seedance）
continuity:
  start_state: {start_state}
  action: {action}
  end_state: {end_state}
  constraints: {constraints}
  negative: {negative}
人物运动：{动作链}；动作家族：{action_family}；力量等级：{energy_level}；表情；
镜头运动：{快推/环绕/轻甩 + 速度}；
空间/轴线锁：{eyeline_lock / movement_vector}；
动态细节：发丝、衣摆、光斑或环境粒子随动作幅度产生物理惯性偏移；
卡点约束：动作峰值/击中点对齐 {action_peak_relative}；
转场母题：{transition_motif}；
衔接约束：开头承接 continuity.start_state，只执行 continuity.action，保持 continuity.constraints，避开 continuity.negative；
声音约束：无对白、无旁白、不要生成原生人声；
（末尾按平台拼风格词）

### 平台参数：模型/时长/帧率/画幅/**分辨率·帧率·质量档(由 出视频规格 档定)**/image2video 强度
```

> **分辨率/帧率/质量档/跑几版由 `出视频规格` 三档预算统一决定**（见 SKILL「出视频规格」节）：预算充足=1080p·30fps·高质量档·多跑挑稳，预算一般（默认）=720p·24-30fps·标准档·关键镜2版/普通镜1版，预算不够=720p·24fps·省积分档·全1版。**每次开跑前念一行告知当前规格档**（首次问一次记入 `_设置.md`，之后沉默沿用但仍告知，用户随时可改）。CLI 调用据此加 `--resolution`/`--fps`（flag 名以平台为准）。

## 卡点定 clip 时长（核心）
- 由 `mv-plan` 读取 `节拍/beatgrid.json` 的 `downbeats[]`（小节首秒）并写入 `clip_plan.json`；mv-video 只消费，不重新拆时间线。
- **副歌**：每个 downbeat（或半小节）切一刀 → clip 短（碎切，强节奏）。
- **verse**：2-4 拍一切 → clip 长（缓）。
- clip 时长 = 该段相邻卡点之差；**全曲 clip 时长之和 ≈ 歌长**（mv-compose 会校验）。

## 段落/张力 → 运镜
| 段落 | 张力 | 运镜 | clip 时长 |
|---|---|---|---|
| intro | 克制 | 固定/极缓推 | 长 |
| verse | 叙事 | 缓推/跟 | 中长 |
| pre-chorus | 蓄力 | 渐快推近 | 中→短 |
| chorus | 爆发 | 快推/环绕/轻甩 | 短(碎切) |
| bridge | 反转 | 换机位/大运动 | 中 |
| outro | 释放 | 缓拉远/定格 | 长 |

## continuity 派生规则（MV 版）
- `start_state`：**抄上一 clip 的 `end_state`**（同一句，不重写）；若是段落第一条，取本 clip 首帧描述 + 段落视觉锚点。
- `action`：取本 clip 的主动作链，并把动作峰值、眼神落点、拔剑/转身/抬手/光效爆点对齐 `beatgrid` 的 beat/downbeat；副歌动作短促，verse 动作完整。
- `end_state`：服务下一 clip 的首帧、歌词钩子和转场方式。接不住时停在手部道具、衣摆、背影、光效、门帘、山影等可切画面重心。**`need_end_frame=true` 时，end_state 必须与 mv-image 出的尾帧 `_end.png` 一致，并把它设为本 clip 尾帧做双帧引导。**
- `constraints`：同一段落继承角色定妆、服装发型、主色调、光线、天气、道具、背景布局、轴线/屏幕方向；跨段落可换场景，但角色定妆和核心道具保持。
- `negative`：默认写入"不要换脸、不要换衣、不要新增人物、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要生成原生人声"；人脸/手部/多人镜按风险追加"不要脸部抖动/不要手指变形/不要多人脸错乱"。

## 常用衔接做法
- **动作切**：上一 clip 结尾停在动作完成前后一拍，下一 clip 从同方向继续或切道具特写。
- **视线切**：上一 clip 让人物看向画外，下一 clip 承接被看的物体/风景/敌人/远山。
- **光效切/闪白**：副歌 or 强 downbeat 可用光效爆点遮掩场景切换，但不要每条都用。
- **遮挡擦镜**：衣袖、剑光、前景树枝、烟雾横过画面，用于接不上时补缝。
- **空镜缓冲**：verse/outro 用云、山、灯、雨、脚步、手部等 0.5-2s 镜头缓冲。

## 生视频 / 登记 / 挑版
- 同一 MV 全程同一生视频模型/渠道策略（防风格跳）。首帧=mv-image PNG（图生视频锁一致性）。
- 每 clip 跑几版挑脸/运动稳由 `出视频规格` 档统一定（充足=关键镜2-3版·普通镜2版；一般=关键镜2版·普通镜1版；不够=全1版）；废片归 `common/废料/出视频/`。
- 爽点 clip 的关键帧对齐某个 downbeat，供 mv-compose 卡点。
- 外部/网页生成视频后必须登记：`video_jobs.py --register <file> --clip Clip_001 --take 1`。
- 多版评分后挑版：`video_jobs.py --score ...`，再 `--select Clip_001 --take 1`；挑版会复制到 `出视频/视频/Clip_001.mp4` 并同步 timeline。

## 自查
- [ ] clip 时长来自 `clip_plan.json`（非等长）？
- [ ] 副歌碎切、verse 缓？
- [ ] 运镜服务段落/张力？
- [ ] continuity 五字段齐，且读取了上一/下一 clip 与 beatgrid 落点？
- [ ] 接力：start_state 抄了上一 clip 的 end_state（没自己重写）？标 `need_end_frame=true` 的接缝已让 mv-image 出 `_end.png` 并用首尾双帧？
- [ ] 每个外部 take 都已登记，最终 selected_take 已同步 timeline？
- [ ] 三件套齐？总时长≈歌长？
