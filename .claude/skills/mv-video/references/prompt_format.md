# mv-video clip 表 + 卡点定时长 + 运镜映射

## clip 表（按段落 + beatgrid 规划）
```markdown
## Clip NN（段落 chorus · 时长 1.6s · @0:48-0:49.6）
**首帧**：出图/段落/chorus_主角高光.png
**卡点**：起 0:48(downbeat) → 止 0:49.6(下一downbeat)
### 视频 prompt（中文，目标=即梦/可灵/Seedance）
人物运动：{动作链}；表情；
镜头运动：{快推/环绕/轻甩 + 速度}；   ← 由段落/张力决定
动态细节：{发丝/光斑/衣摆/雾…}；
（末尾按平台拼风格词）
### 平台参数：模型/时长/帧率/画幅/image2video 强度
```

## 卡点定 clip 时长（核心）
- 读 `节拍/beatgrid.json` 的 `downbeats[]`（小节首秒）。
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

## 生视频
- 同一 MV 全程同一视频 AI（防风格跳）。首帧=mv-image PNG（图生视频锁一致性）。
- 每 clip 可跑 2 版挑脸/运动稳的；废片归 `common/废料/出视频/`。
- 爽点 clip 的关键帧对齐某个 downbeat，供 mv-compose 卡点。

## 自查
- [ ] clip 时长来自 beatgrid（非等长）？
- [ ] 副歌碎切、verse 缓？
- [ ] 运镜服务段落/张力？
- [ ] 三件套齐？总时长≈歌长？
