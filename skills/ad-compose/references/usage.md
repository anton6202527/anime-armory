# ad-compose 用法与交付（参考）

## 自动 vs 操作者手工

| 步骤 | 状态 |
|---|---|
| 主片拼接 + end card + 字幕烧录 + 混音 + 响度归一 | **自动**（`compose.sh` 调 ffmpeg 出 MP4）|
| 多时长 cutdown | **自动**（`cutdown.py --render`，无 ffmpeg 时降级只出 plan）|
| 多比例 reframe | **自动**（`reframe.py --render`，无 ffmpeg 时降级只出滤镜串）|
| A/B 版本 | **操作者手工**（`deliver.py` 只给 expected_path，不代生成）|

## 脚本一览

| 脚本 | 作用 |
|---|---|
| `compose.sh <作品根> [比例] [字幕语言] [交付规格]` | 拼 clips（filter-concat 归一）+ 混 VO/音乐床 + 烧字幕 + 追加 end card + 响度归一 → `合成/成片_主片.mp4`(+`_loud.mp4`) |
| `endcard.py --out … (--size WxH \| --aspect 9:16) …` | 品牌包装片尾 PNG；尺寸按 `--size`/`--aspect` 推（不再写死 1920x1080），版式用实测文字高度堆叠 |
| `render_subs.py <srt> --out-dir … --png-input-base 1` | SRT → 字幕 PNG + `overlay_table.json` + `inputs.txt` + `vfilter.txt`（compose.sh 直接消费 vfilter）|
| `cutdown.py <作品根> --target 15s [--aspect 16:9] [--render]` | 多时长重剪规划（必保镜先占预算 + 权威时长源 + 缺失 block）；`--render` 实际出 MP4，带 pytest |
| `reframe.py --src WxH --target 9:16 [--crop-x/--crop-y] [--in … --render]` | 多比例 crop/pad 滤镜 + 焦点裁切；`--render` 实际出 MP4，带 pytest |
| `deliver.py <作品根> --mark-existing` | 读 `_进度.md` 交付矩阵，生成 delivery_plan（含可执行 `--render` 命令），并把已存在交付件回写 ✅ |

## 交付规格（响度归一）

按 `_设置.md` 的 `交付规格`，`compose.sh` 第 4 参数即此值，成片有音轨时**自动**跑 loudnorm：
- 平台默认：`-16 LUFS`，true peak `-1 dB`（抖音/快手/信息流）。
- 广电 TVC：`-23 LUFS`，true peak `-2 dB`。

```bash
# compose.sh 自动产出 合成/成片_主片_loud.mp4；如需单独跑：
ffmpeg -i 成片_主片.mp4 -af loudnorm=I=-16:TP=-1:LRA=11 -c:v copy 合成/成片_主片_loud.mp4
```

## 安全框

竖版/方版 reframe 会裁掉两侧；标题/logo/CTA 须在 title-safe（≈90%），主体/产品在 action-safe（≈93%）。出图出视频阶段已留余量。`reframe.py` 默认**中心裁切**（偏置主体会被裁掉，脚本会提示）；主体不在中心时用 `--crop-x/--crop-y` 指定归一焦点（0..1），裁切窗会对到主体并夹进画内。

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

## AI 使用披露（投放前必做）

`ad-craft/scripts/ai_usage.py` 记 AI 使用 + 授权（音乐/代言人/字体/素材）。

> AI 标识/水印不再由本流水线处理：ad-compose 出成片/交付件即收尾，不再生成可见 AI 标识/水印、不再调用任何 watermark skill。若投放地区/平台需要 AI 标识，由使用方在工具之外按当地法规自行处理。
