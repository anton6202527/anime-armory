---
name: mv-lyric-sync
description: 制 MV 卡拉 OK 字幕与正式对齐签收：用 WhisperX 将已知歌词映射为字符时间戳，生成 ASS/LRC，并以当前 hash 绑定的歌声声学证据或具名逐行听审验收。Use when asked to 卡拉OK字幕 / 歌词对齐 / 字符级时间戳 / 生成LRC/ASS / 对齐报告. Triggers 卡拉OK, 歌词字幕, 歌词对齐, 字符级对齐, LRC, ASS字幕, 对齐报告, mv-lyric-sync.
---

# mv-lyric-sync — 卡拉 OK 字幕（制 MV 线）

把 `词/lyrics.md` 的已知歌词强制对齐到最终 `歌/song.*` 或 vocals stem，生成 `字幕/karaoke.ass`、`字幕/lyrics.lrc` 与 schema 5 `字幕/alignment_report.json`。本阶段是条件阶段：仅当项目同时关闭字幕与演唱口型时可跳过。

## 不变量

- `character_coverage_ratio` 只回答“歌词字符是否取得时间戳”，不是声学置信度。schema 5 不写 `alignment_confidence`。
- 保留 WhisperX 的 char/word raw score，但报告固定标记 `calibrated=false`、`singing_specific=false`、`acceptance_eligible=false`；它们不能自行放行。
- 首次生成只产 `acceptance.status=pending`，退出码为 3，且不推进 `_进度.md`。检查产物后必须另跑一次正式签收。
- 正式签收严格二选一：当前 hash-bound 的歌声/逐音素声学证据，或具名完整逐行 listening review。任一输入、ASS、LRC 或报告前置内容变化都会使签收失效。
- 低文本覆盖不是放行开关：必须先提供覆盖每个弱行的 corrections（master 时间秒）和完整校正版 ASS/LRC，再走上述二选一签收。
- 对齐音频不是 master 时，先自动以 ffmpeg 解码后的多窗口相关性验证并换算 stem→master offset/drift；验证不了就阻断。也可提供具名、带 notes 的显式 offset/drift 声明。

声学证据、corrections 和绑定字段见 [references/alignment-evidence-schema.md](references/alignment-evidence-schema.md)。

## 依赖与偏好

```bash
pip install whisperx
```

首次执行前读 `<作品根>/_设置.md`；缺失时按 MV 线的设置流程补齐。相关选择点是字幕语言、卡拉 OK 样式、强制对齐引擎。最终歌曲尚未就位时停下，不得用 rough 音频伪造正式收据。

## 两步 CLI

生成待签收时间轴：

```bash
python3 skills/mv/mv-lyric-sync/scripts/align.py <作品根> --lang zh --device cpu
python3 skills/mv/mv-lyric-sync/scripts/align.py <作品根> --audio <作品根>/歌/vocals.wav
```

若 stem 自动相关性不足，但已由音频工程师确认 DAW 时间基准：

```bash
python3 skills/mv/mv-lyric-sync/scripts/align.py <作品根> --audio <stem> \
  --stem-timing-reviewer "<姓名>" --stem-timing-notes "<测量方法>" \
  --stem-master-offset-seconds 0.125 --stem-master-drift-seconds 0.004
```

低覆盖须在生成时应用校正包；旧参数 `--allow-low-confidence`、`--reviewer`、`--notes` 仅作兼容别名：

```bash
python3 skills/mv/mv-lyric-sync/scripts/align.py <作品根> --allow-low-coverage \
  --correction-reviewer "<姓名>" --correction-notes "<逐行校正依据>" \
  --corrections-file corrections.json --corrected-ass corrected.ass --corrected-lrc corrected.lrc
```

生成后先试听/检查。声学工具可取得必须原样复制的绑定对象：

```bash
python3 skills/mv/mv-lyric-sync/scripts/align.py <作品根> \
  --accept-existing --show-required-binding
```

然后二选一正式签收：

```bash
# A：具名、版本化、歌声专用且已校准的逐行/逐音素声学证据
python3 skills/mv/mv-lyric-sync/scripts/align.py <作品根> \
  --accept-existing --acoustic-evidence acoustic_evidence.json

# B：人实际逐行对照 master/stem/ASS/LRC/report 前置内容后的具名听审
python3 skills/mv/mv-lyric-sync/scripts/align.py <作品根> --accept-existing \
  --listening-reviewer "<姓名>" --listening-notes "<完整逐行听审结论>"
```

签收命令成功后才写 `acceptance.status=accepted` 并推进 `lyric_sync`。不要把首次生成的退出码 3 或 pending 报告转换成成功完成态。

## 检查重点

- ASS 必须保留原歌词全部字形和标点；未匹配字符用 `\k0`，不得静默删字。
- 全局字符覆盖低于 90%、任一行低于 85%、缺行、重叠或倒序都属于低文本覆盖路径。
- `stem_master_timing.bindings` 必须仍匹配当前 master 与 alignment audio；自动证据需通过相关性和 drift 阈值，显式证据需具名 reviewer、offset、drift、notes。
- 声学证据需有 model name/version、`singing_specific=true`、`calibrated=true`、`acceptance_eligible=true`、metric/threshold/confidence、覆盖全部歌词行的 `per_line[]` 或 `phonemes[]`，并绑定当前五类资产与 report 前置内容。
- listening review 由 `--accept-existing` 写入，绑定当前 master、alignment audio、lyrics、ASS、LRC、报告前置内容以及签收前报告文件 SHA。

测试：

```bash
python3 -m pytest -q skills/mv/mv-lyric-sync/scripts/test_align.py
```
