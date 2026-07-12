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
| `compose.sh <作品根> [比例] [字幕语言] [交付规格]` | gate → HDR/混色源预检 → 拼 clips + 混音/字幕 + 按需 end card + BT.709 标签/响度归一 |
| `endcard.py --out … (--size WxH \| --aspect 9:16) …` | 品牌包装片尾 PNG；尺寸按 `--size`/`--aspect` 推（不再写死 1920x1080），版式用实测文字高度堆叠 |
| `render_subs.py <srt> --out-dir … --png-input-base 1` | SRT → 字幕 PNG + `overlay_table.json` + `inputs.txt` + `vfilter.txt`（compose.sh 直接消费 vfilter）|
| `cutdown.py <作品根> --target 15s [--render]` | 先选镜，再从主片 trim/concat；claim 镜与对应 disclosure 镜按 ID 原子保留 |
| `reframe.py … [--focus-plan plan.json]` | 固定或分时焦点裁切；动态主体可按镜头移动裁切窗 |
| `rendered_text_qc.py <作品根> --init-plan` | 从最终交付件抽取文字帧；OCR/对比度只定位，具名人确认精确文字、对比度、时长、遮挡 |
| `asr_consistency.py <作品根> [--run-asr]` | voiceover → 实际 VO → 字幕 → 最终音轨四路对账，关键文案精确匹配 |
| `provenance_qc.py <作品根>` | 逐最终文件实测 C2PA/容器隐式标识，或验证绑定当前 SHA 的外部探测回执 |
| `deliver.py <作品根> --mark-existing [--run-asr]` | 先写当前 plan，再生成 delivery/rendered text/ASR/provenance/accessibility QC；全部 0 block 才回写 ✅ |

## 交付规格（响度归一）

按 `_设置.md` 的 `交付规格`，`compose.sh` 第 4 参数即此值，成片有音轨时**自动**跑 loudnorm：
- 平台默认：内部数字投放母版 `-16 LUFS`、true peak `-1 dBTP`；不是各平台统一官方值，客户/平台书面规格优先。
- 广电 TVC：按 EBU R128 节目响度建议 `-23 LUFS`、true peak `-1 dBTP`；若播出机构另有交付规范，以其书面规范为准。
- 自定义：不得静默沿用 -16；先在 `brief.delivery_profiles.自定义` 写 `loudness_lufs/true_peak_db/source/checked_at/approved_by`，缺任一项 compose 与 delivery QC 都 block。

```bash
# 目标从 ad-craft contract 读取；delivery_qc 对最终文件再次实测，不以“跑过 loudnorm 命令”代替验收。
```

## 安全框

竖版/方版 reframe 会裁掉两侧；标题/logo/CTA 须在 title-safe（≈90%），主体/产品在 action-safe（≈93%）。出图出视频阶段已留余量。`reframe.py` 默认**中心裁切**（偏置主体会被裁掉，脚本会提示）；主体不在中心时用 `--crop-x/--crop-y` 指定归一焦点（0..1），裁切窗会对到主体并夹进画内。

title/action safe 是内部构图辅助，不是平台证据。最终按 `platform_pack.placement_specs` 逐个版位消费当前模板；只有平台级截图不能 release-ready。

## SDR 色彩、最终文字、无障碍与 provenance

- 默认内部母版为 SDR BT.709 / yuv420p / tv range / progressive。`compose_preflight.py` 发现 HDR、BT.2020 或混合色彩源时要求 `brief.color_management.mode=explicit_conversion` 和转换/监看证据，不能静默重贴标签。
- `delivery_qc` 验最终每件的色彩元数据；`rendered_text_qc` 在最终像素上逐条绑定字幕/CTA/价格/claim/法律声明的抽帧哈希和具名证据。
- `accessibility_qc` 按项目目标验字幕、逐个有意义非语言音频事件，以及 WCAG 2.2 A/AA 所需媒体替代/音频描述；自动阅读速度、对比度和闪烁仍是定位快筛。
- `provenance_qc` 不读取“preserve”口号当证据；它检查实际文件，外部回执也必须写工具、时间、批准人、可查询证据和当前媒体 SHA。

## 接缝（与 storyboard.transition 对应）

| transition | 处理 |
|---|---|
| 硬切 | concat 裸拼（默认）|
| 微溶解 | 局部 `xfade=duration=0.15` |
| 跳切（有意） | 不溶解，保留冲击 |
| 缺空镜 | 报警，不伪造 |

## 多版本交付落档

每出一个交付件，在所有最终媒体 QC 通过后更新 `_进度.md` 交付版本矩阵对应行的 `状态=✅` 和 `成片路径`：
- 主片 → `合成/成片_主片.mp4`
- cutdown 15s → `合成/cutdown/成片_15s.mp4`
- 竖版 9:16 → `合成/多比例/成片_9x16.mp4`

推荐用：

```bash
python3 skills/ad-compose/deliver.py "<作品根>" --mark-existing
```

## AI 使用披露（投放前必做）

`ad-craft/scripts/ai_usage.py` 记 AI 使用 + 授权（音乐/代言人/字体/素材）。

随后完成 `locale_matrix.json`、`release_variant_manifest.json` 与 `compliance_manifest.json`；平台声明/标识由发布方实际执行并逐交付件回写当前 SHA 证据，未完成不能通过最终 review。
