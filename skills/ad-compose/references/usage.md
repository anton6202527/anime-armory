# ad-compose 用法与交付（参考）

## 脚本一览

| 脚本 | 作用 |
|---|---|
| `compose.sh <作品根> [比例]` | 拼 clips + 混 VO/音乐床 + 追加 end card → `合成/成片_主片.mp4` |
| `endcard.py` | 品牌包装片尾 PNG（品牌色 + logo + slogan + CTA 胶囊），Pillow |
| `render_subs.py` | SRT → 字幕 PNG + overlay 时间表（无 libass）|
| `cutdown.py <作品根> --target 15s` | 多时长重剪规划（按镜头优先级保骨架），带 pytest |
| `reframe.py --src WxH --target 9:16` | 多比例 crop/pad 滤镜计算，带 pytest |
| `deliver.py <作品根> --mark-existing` | 读 `_进度.md` 交付矩阵，生成 delivery_plan，并把已存在交付件回写 ✅ |

## 交付规格（响度归一）

按 `_设置.md` 的 `交付规格`：
- 平台默认：`-16 LUFS`，true peak `-1 dB`（抖音/快手/信息流）。
- 广电 TVC：`-23 LUFS`，true peak `-2 dB`。

```bash
ffmpeg -i 成片_主片.mp4 -af loudnorm=I=-16:TP=-1:LRA=11 -c:v copy 合成/交付/成片_主片_loud.mp4
```

## 安全框

竖版/方版 reframe 会裁掉两侧；标题/logo/CTA 须在 title-safe（≈90%），主体/产品在 action-safe（≈93%）。出图出视频阶段已留余量；reframe 用 `crop` 居中裁切，主体偏置时改 `crop` 的 x/y 偏移。

## 接缝（与 storyboard.transition 对应）

| transition | 处理 |
|---|---|
| 硬切 | concat 裸拼（默认）|
| 微溶解 | 局部 `xfade=duration=0.15` |
| 跳切（有意） | 不溶解，保留冲击 |
| 缺空镜 | 报警，不伪造 |

## 多版本交付落档

每出一个交付件，更新 `_进度.md` 交付版本矩阵对应行的 `状态=✅` 和 `成片路径`：
- 主片 → `合成/成片_主片.mp4`
- cutdown 15s → `合成/cutdown/成片_15s.mp4`
- 竖版 9:16 → `合成/多比例/成片_9x16.mp4`

推荐用：

```bash
python3 skills/ad-compose/deliver.py "<作品根>" --mark-existing
```

## AI 标识 + 披露（投放前必做）

1. `ad-watermark` 打 AI 标识（可见 + 元数据，只加不去）。
2. `ad-craft/scripts/ai_usage.py` 记 AI 使用 + 授权（音乐/代言人/字体/素材）。
