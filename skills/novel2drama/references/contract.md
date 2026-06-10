# novel2drama / n2d 机器契约

本文件是给人读的说明；脚本真值源在 `skills/common/n2d_contract.py`。任何阶段、列名、gate、manifest 字段变更，先改 contract，再让 SKILL.md 和脚本复述它。

## 1. 进度表 schema

`<作品根>/_进度.md` 是全作品进度 single source of truth。当前标准列：

```markdown
| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |
```

机器语义：

| 单元格 | 状态 |
|---|---|
| `✅` | 完成 |
| `⬜` / 空 | 未开始 |
| `N/M` | 部分完成；仅 `N >= M` 算完成 |
| `—` / `N/A` / `无` | 本集不适用，路由视为已满足 |

`raw` 是源文本展示列，不计入生产完成度。

## 2. 阶段图

阶段顺序由 `n2d_contract.STAGE_GRAPH` 定义：

| key | label | owner | progress columns | gate | 回退目标 |
|---|---|---|---|---|---|
| `source` | 源文本落档 | `n2d-script` | `raw` | - | `source` |
| `script_stage1` | 阶段1·剧本改编 | `n2d-script` | `剧本改编 / bgm / 封面` | - | `script_stage1` |
| `voice` | 角色配音 | `n2d-voice` | `配音` | - | `voice` |
| `script_stage2` | 阶段2·分镜设计 | `n2d-script` | `分镜设计 / 素材清单 / 字幕中 / 字幕英` | - | `script_stage2` |
| `image_prompt` | 出图prompt | `n2d-image` | `出图prompt` | `image` | `image_prompt` |
| `image` | 出图 | `n2d-image` | `出图` | `image` | `image` |
| `video_prompt` | 视频prompt | `n2d-video` | `视频prompt` | `video` | `video_prompt` |
| `video` | 图生视频 | `n2d-video` | `视频` | `video` | `video` |
| `compose` | 合成成片 | `n2d-compose` | `成片` | `compose` | `compose` |
| `review` | 审查验收 | `n2d-review` | - | `review` | `review` |

`skills/common/n2d_route.py` 从这张表派生旧的 `STAGES` 路由元组，供 `novel2drama/progress.py` 和 `n2d-progress/scan.py` 复用。不要再在别处手写另一张阶段表。

## 3. 制作模式

`_设置.md` 的 `制作模式` 是状态机变体，而不是散落规则：

| 模式 | 语义 |
|---|---|
| `配音先行` | 默认推荐。真实配音先出，实测时长驱动分镜、出图、出视频。 |
| `先出视频后配音` | demo 模式。先用占位/估算时长锁镜头，视频出齐后补真实配音；合成前若配音仍占位，路由会拦回 `n2d-voice`。 |

## 4. 每集 manifest

每集写 `脚本/第N集/manifest.json`。`progress.py set` 会在阶段回写时自动刷新；也可手动重建：

```json
{
  "kind": "n2d_episode_manifest",
  "schema_version": 2,
  "episode": "第1集",
  "stage": "all",
  "production_mode": "配音先行",
  "artifacts": [
    {
      "stage": "script_stage2",
      "path": "脚本/第1集/storyboard.json",
      "exists": true,
      "kind": "file",
      "sha256": "..."
    }
  ]
}
```

```bash
python3 skills/novel2drama/manifest.py <作品根> 第N集
python3 skills/novel2drama/manifest.py <作品根> 第N集 --stage video
```

manifest 是产物快照，不负责生成媒体。阶段脚本收尾时可以调用它，让后续 review/返工知道某一集当时依赖了哪些文件。

## 5. Gate 回滚输出

高风险阶段统一走：

```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image|video|compose|review
python3 skills/n2d-review/scripts/gate.py <作品根> 第N集 --stage video --json  # 调试/机器消费入口
```

JSON 输出保留旧字段：

```json
{"sev":"block","dim":"prompt","loc":"...","msg":"..."}
```

并追加结构化返工字段：

```json
{
  "return_to_stage": "video_prompt",
  "rerun_scope": "先修尾帧、视频 prompt、导演一致性契约或缺失 PNG，再重跑 video gate；未过 gate 不出视频。",
  "affected_artifacts": ["脚本/第N集/storyboard.json", "出视频/第N集/prompt", "出视频/第N集/视频"]
}
```

后续自动化只读这些字段做最小重跑范围；人类报告仍读 `msg`。

## 6. 跨阶段契约字段

`storyboard.json` 是分镜设计后的机器契约源：

- `visual_contract` 必含：`色调基线 / 场景光位锚 / 场景轴线视线 / 角色状态演进 / 景别阶梯`
- `style_contract` 必含：`风格名 / 视觉基调 / 镜头与构图 / 光色策略 / 运动边界 / 风格禁忌`
- 旧项目 `cinematic_contract` 兼容通过：`摄影基调 / 镜头焦段 / 光源动机 / 色彩策略 / 运镜边界 / 真实感禁忌`
- 每个 `clips[]` 的 `continuity` 必含：`start_state / action / end_state / constraints / negative / transition / need_endframe`
- 非最终 Clip 默认 `need_endframe=true`；豁免必须写 `endframe_exempt_reason`

出图、出视频、review 都只能继承这些字段并细化，不能各自另写一套真值。

`style_contract` 的目标是把用户选择的基础视觉风格从形容词变成生产约束。风格由 `_设置.md` 的 `基础视觉风格` 与 `设定库/global_style.md` 派生，不由 skill 正文写死：

```json
{
  "style_contract": {
    "风格名": "国漫写实",
    "视觉基调": "东方幻想国漫，角色比例略理想化，场景和服装材质写实，高细节但不照片化",
    "镜头与构图": "保留影视景别和轴线；可用更强剪影、广角压迫和法术特写，但不随机变透视",
    "光色策略": "青灰为主，烛火金只在情绪转折处强调；强光来自月光、烛火、符阵或兵器反光",
    "运动边界": "慢推、固定、跟摇为主；爽点可短促环绕或轻甩，禁止无理由飞行镜头",
    "风格禁忌": ["欧美脸漂移", "页游塑料盔甲", "随机霓虹", "过度磨皮", "背景像贴图", "低幼Q版"]
  }
}
```

markdown 层新产物继承标题固定为「本集基础视觉风格契约」。`gate.py --stage image|video` 会阻断 storyboard 缺 `style_contract`、出图总览缺「本集基础视觉风格契约」、出视频总览缺「本集基础视觉风格契约」。旧标题「本集真实电影感契约」只作兼容。

## 7. 契约治理：invariant vs contested（阶段0）

契约是双刃剑——它让管线稳，也会**把仍在争论的设计决策硬化成既成事实**，给它们虚假权威、抬高演进成本。治理原则（见 `docs/n2d-原则变更提案-契约治理与一致性占位.md` 提案一）：

- **每个契约项分两类**：`invariant`（已定不变量，可硬化进 BLOCK gate / "必须"措辞）vs `contested`（待决原则，**只能进 choice point，不得新增 BLOCK / "只能·不可选"措辞**）。
- **真值源**：`skills/common/n2d_contract.py` 的 `CONTESTED`（当前标注，**零消费·零行为变化**）+ `INVARIANT_NOTE`。
- **当前 contested 三项**：① 生图后端垄断（"图必须 Codex"）② 占位驱动付费生成（"先出视频后配音"）③ 基础视觉风格（写实电影感只是预选，风格必须 derive from `基础视觉风格` + `global_style.md`）。其中③已落地为选择点 + `style_contract`；旧 `cinematic_contract` 兼容。

## 8. 版本治理：bump 必带迁移（P1.4·待补）

`CONTRACT_VERSION` 现为 **2**。`style_contract` 是向后兼容新增字段：gate 仍接受旧 `cinematic_contract`，所以本次不 bump schema；下次触碰旧故事板/总览时顺手迁到 `style_contract`。原则：`CONTRACT_VERSION` 每升一级须配 `migrate_v{N}_to_v{N+1}(work_root)`，路由/进度脚本检测 `schema_version` 落后即提示。**版本号不配迁移函数等于没版本号**。
