# 运镜视觉参考库

本目录是 n2d 系列的出视频运镜参考库，原始来源为用户提供且已确认可公开再分发的运镜动画。23 个大体积 animated WebP 使用内容寻址 R2 保存，本线只保留结构化真值、轻量首帧和五帧 contact sheet；`n2d-script` 的导演运镜 sidecar 与 `n2d-video` 的视频 prompt 不依赖网络即可运行。

机器可读真值源是 [`manifest.json`](manifest.json)：它把 23 个视觉参考的英文名、别名、slot、风险等级、适用场景、prompt 模板、本地预览/contact sheet 与远端 URL/bytes/SHA-256 统一登记；`skills/n2d/_lib/n2d_const.py` 会启动时读取它并扩展 `CAMERA_MOVE_LEXICON`。

## 视觉素材分层

- `_preview/`：轻量首帧，供 Desktop 快速预览。
- `_contact/`：按时间均匀抽取的五帧拼图，供 agent/视觉模型离线理解运动方向和构图变化；这是默认视觉校准入口。
- R2 animated WebP：只有需要判断完整运动节奏、轨迹或镜头速度时才按需下载；对象以内容 SHA-256 命名，下载时同时校验声明字节数与 SHA-256，缓存位于仓库外用户缓存。
- 断网或下载失败不是主流程 blocker：继续使用 `manifest.json + _contact/`。

```bash
python3 skills/n2d/scripts/camera_reference.py list
python3 skills/n2d/scripts/camera_reference.py show dolly_in --json
python3 skills/n2d/scripts/camera_reference.py fetch dolly_in --json
python3 skills/n2d/scripts/camera_reference.py self-check
```

## 使用原则

- 写视频 prompt 时，先从本目录选择最贴合剧情功能的一种运镜，再补速度、方向、起幅和落幅。
- prompt 里仍写结构化字段：`镜头运动：{运镜词}；速度={缓慢/匀速/快速/急速}；方向={...}；起止={...}`。
- 运镜只服务本镜张力，不替代人物动作。近景大表情、对白反打和身份高风险镜头优先用固定、轻微推近或低幅跟拍。
- 复杂运镜（滚筒旋转、盘旋、无人机、第一视角）只在剧情需要空间奇观、眩晕、追逐或飞行时使用；人物身份不稳时先降级为保真拍法。
- 暂无视觉参考的新条目仍可用于 prompt/gate：甩镜、急推变焦、急拉变焦、焦点转移、摇臂揭示、稳定器跟拍、低机位贴地跟拍、前景遮挡揭示、顶视俯拍、载具跟拍；以及后续扩充的 半环绕/弧线、穿越运镜、FPV俯冲、贴地飞掠、反射揭示、荷兰角、顶部旋转俯拍、探针穿越微距、机身固定(snorricam)、越肩推镜、变速坡道、甩入定格、一镜到底、鸟瞰俯降、仰角英雄推。后续若补图，只需在同目录放媒体并更新 `manifest.json.media`。

## 图片索引

| 远端动画文件 | 结构化运镜词 | prompt 适用场景 |
|---|---|---|
| `固定镜头.webp` | 固定机位 | 对白、反打、屏幕/面板、近景表演、身份高风险镜头 |
| `镜头前推.webp` | 推镜头 | 逼近、压迫、揭示、聚焦人物情绪或物证 |
| `镜头后移.webp` | 拉镜头 | 退场、孤独、余韵、从人物释放到场景关系 |
| `变焦推进.webp` | 变焦推进 | 不改变机位的视觉逼近、压迫或信息聚焦 |
| `变焦拉远.webp` | 变焦拉远 | 不改变机位的疏离、暴露空间或情绪释放 |
| `柯克变焦.webp` | 柯克变焦 | 眩晕、真相冲击、心理失衡；慎用于近脸 |
| `镜头左摇.webp` | 摇镜头 | 横向揭示、跟随视线、由一方摇到另一方 |
| `镜头右摇.webp` | 摇镜头 | 横向揭示、跟随视线、由一方摇到另一方 |
| `镜头上摇.webp` | 摇镜头 | 从人物/道具揭示到高处威胁、天空、巨物 |
| `镜头下摇.webp` | 摇镜头 | 从高处压迫落到人物、道具或地面证据 |
| `镜头左移.webp` | 移镜头 | 平移跟随、横向调度、保持轴线的空间移动 |
| `镜头右移.webp` | 移镜头 | 平移跟随、横向调度、保持轴线的空间移动 |
| `镜头上升.webp` | 升降 | 建立空间层级、权力关系、从人物抬到全景 |
| `镜头下降.webp` | 升降 | 从环境压到人物、降临感、压迫或落地 |
| `环绕拍摄.webp` | 环绕 | 爽点、高光、人物气场展示；身份高风险时低幅使用 |
| `盘旋抬升.webp` | 盘旋抬升 | 奇观、飞行、空间揭示、战场/大场面升格 |
| `盘旋下降.webp` | 盘旋下降 | 降临、锁定目标、从奇观落到冲突中心 |
| `高空航拍.webp` | 无人机航拍 | 定场、大场面、路线、地理关系 |
| `无人机.webp` | 无人机航拍 | 飞行、追逐、空间穿梭、场景巡航 |
| `跟随拍摄.webp` | 跟拍 | 追逐、行走、打斗跟随、角色行动代入 |
| `第一视角.webp` | 第一视角 | 主观视角、追逐、探索、角色被卷入事件 |
| `手持拍摄.webp` | 手持晃动 | 紧张、混乱、逃跑、临场感；身份高风险时控制幅度 |
| `滚筒旋转.webp` | 滚筒旋转 | 失控、坠落、眩晕、空间翻转；慎用，必要时拆镜 |

## n2d 接入点

- 机器真值：`skills/n2d/references/运镜/manifest.json`。
- 活词典：`skills/n2d/_lib/n2d_const.py` 的 `CAMERA_MOVE_LEXICON`，启动时从 manifest 合并别名、新词条和媒体引用。
- 归一化：`skills/n2d/_lib/n2d_logic.py::normalize_camera_move()`。
- sidecar：`skills/n2d/n2d-script/scripts/director_camera_plan.py`。
- 视频 prompt 包：`skills/n2d/n2d-video/scripts/prompt_pack.py`。
