# ad-compose 用法与交付（参考）

## 自动 vs 操作者手工

这里的“自动”指**已通过 compose gate 且高风险 effect 已获批准后的确定性执行**，不代表 compose runner 自批。普通模板、字幕、规格、cutdown 选择可采用 `_设置.md` 推荐值继续；外部付费、覆盖既有交付件、机械裁切风险接受、公开发布和最终签收仍是硬边界。ad-image/ad-video 的 v2 阶段预算包不会自动授权本阶段。

| 步骤 | 状态 |
|---|---|
| 主片拼接 + end card + 字幕烧录 + 混音 + 响度归一 | **自动**（`compose.sh` 调 ffmpeg 出 MP4）|
| 多时长 cutdown | **自动**（`cutdown.py --render`，无 ffmpeg 时降级只出 plan）|
| 多比例 placement adaptation | **先决策再执行**：原生模式输出制作指令；仅已批准 `mechanical_reframe` 自动调用 `reframe.py --render` |
| A/B 版本 | **操作者手工**（`deliver.py` 只给 expected_path，不代生成）|

## 脚本一览

| 脚本 | 作用 |
|---|---|
| `compose.sh <作品根> [比例] [字幕语言] [交付规格]` | gate → HDR/混色源预检 → 拼 clips + 混音/字幕 + 按需 end card + BT.709 标签/响度归一 |
| `endcard.py --out … (--size WxH \| --aspect 9:16) …` | 品牌包装片尾 PNG；尺寸按 `--size`/`--aspect` 推（不再写死 1920x1080），版式用实测文字高度堆叠 |
| `render_subs.py <srt> --out-dir … --png-input-base 1` | SRT → 字幕 PNG + `overlay_table.json` + `inputs.txt` + `vfilter.txt`（compose.sh 直接消费 vfilter）|
| `cutdown.py <作品根> --target 15s [--render]` | 先选镜，再从主片 trim/concat；claim 镜与对应 disclosure 镜按 ID 原子保留 |
| `ad-craft/scripts/render_profile.py <作品根>` | 编译唯一 `source_generation`/`master_render` 比例、分辨率、FPS 与 upscale 事实 |
| `ad-craft/scripts/placement_adaptation.py <作品根>` | 逐交付件选择 placement-native 模式或具名批准的机械路径并校验证据；制作完成后用 `--record-execution <id> --actual-mode … --input … --output … --executed-by …` 签实际执行收据 |
| `reframe.py … [--focus-plan plan.json]` | 仅执行已批准的 `mechanical_reframe`；固定/分时焦点裁切是底层能力，不构成交付批准 |
| `rendered_text_qc.py <作品根> --init-plan` | 从最终交付件抽取文字帧；OCR/对比度只定位，具名人确认精确文字、对比度、时长、遮挡 |
| `asr_consistency.py <作品根> [--run-asr]` | voiceover → 实际 VO → 字幕 → 最终音轨四路对账，关键文案精确匹配 |
| `provenance_qc.py <作品根>` | 逐最终文件实测 C2PA/容器隐式标识，或验证绑定当前 SHA 的外部探测回执 |
| `deliver.py <作品根> --mark-existing [--run-asr]` | 写入 render profile/adaptation refs，把两者 block 汇入 plan，再生成 delivery/rendered text/ASR/provenance/accessibility QC；全部 0 block 才回写 ✅ |

## 交付规格（响度归一）

按 `_设置.md` 的 `交付规格`，`compose.sh` 第 4 参数即此值，成片有音轨时**自动**跑 loudnorm：
- 平台默认：内部数字投放母版 `-16 LUFS`、true peak `-1 dBTP`；不是各平台统一官方值，客户/平台书面规格优先。
- 广电 TVC：按 EBU R128 节目响度建议 `-23 LUFS`、true peak `-1 dBTP`；若播出机构另有交付规范，以其书面规范为准。
- 自定义：不得静默沿用 -16；先在 `brief.delivery_profiles.自定义` 写 `loudness_lufs/true_peak_db/source/checked_at/approved_by`，缺任一项 compose 与 delivery QC 都 block。

```bash
# 目标从 ad-craft contract 读取；delivery_qc 对最终文件再次实测，不以“跑过 loudnorm 命令”代替验收。
```

## 安全框

跨比例交付默认只生成 placement adaptation 计划。原生 reedit/variant 按逐镜带 `source_path(s)` 的 shot plan 重构，签收时重复 `--input` 覆盖全部绑定源素材；只有具名批准、当前 placement 安全区证据、逐镜 focus plan 与必要风险签收齐全时才允许 `mechanical_reframe`。`reframe.py` 的中心/焦点裁切只是底层工具行为，不能单独证明该版本可交付；交付 QC 还会核 `placement_adaptation_receipts/<id>.json` 的 actual mode、输入/输出 SHA、profile SHA、当前 plan/item digest 与 native 源素材集合。

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
python3 skills/ad/ad-compose/deliver.py "<作品根>" --mark-existing
```

## AI 使用披露（投放前必做）

`ad-craft/scripts/ai_usage.py` 记 AI 使用 + 授权（音乐/代言人/字体/素材）。

随后完成 `locale_matrix.json`、`release_variant_manifest.json`、`campaign_readiness.json` 与 `compliance_manifest.json`；AI 来源标识和商业/付费合作披露分别由发布方实际执行并逐交付件回写当前 SHA 证据，未完成不能通过最终 review。
