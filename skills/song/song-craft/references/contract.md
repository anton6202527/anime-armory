# song-* 机器契约

本文件是人读版；机器字段以 `scripts/contract.py` 为准。

## 作品根

```text
创作区/写歌/<曲名>/
├── _设置.md
├── _meta.json
├── _进度.md
├── 创作蓝图.md
├── 创作/song_brief.json
├── 素材/reference_pack.json
├── 词/lyrics.md
├── 歌/
│   ├── song_form.json
│   ├── chord_sheet.md
│   ├── topline_notes.md
│   ├── compose_task.md
│   ├── compose_task.json
│   ├── compose_prompts/
│   ├── takes/
│   ├── takes_manifest.json
│   ├── take_review.json
│   └── song.wav
├── 混音/master_check.json
├── 合规/
│   ├── AI使用说明.md
│   └── rights_metadata.json
├── 导出/
│   └── release_pack.json
└── 发行/
    └── feedback_summary.json
```

## 关键选择点

| 选择点 | 用途 |
|---|---|
| `歌曲用途` | 决定长度、hook 密度、是否优先服务 MV |
| `目标时长` | 约束生成与 QA 时长窗口 |
| `语言` | 决定歌词与演唱语言 |
| `BPM/速度` | 给作词行长、作曲 prompt、MV 卡点提供锚点 |
| `调性` | 给作曲 prompt 和后续编曲沟通提供锚点 |
| `乐器编制` | 给 style prompt / 编曲方向提供明确配器 |
| `人声类型` | 给 style prompt / 合规音色选择提供方向 |
| `作曲后端` | Suno / Udio / ACE-Step / DiffRhythm / 手工外部 |
| `生成版数` | 默认多版挑版，不一版定稿 |
| `挑版策略` | hook、人声、蓝图贴合、MV 适配等优先级 |
| `AI音频使用披露` | 发布/交平台前的合规留痕 |
| `发行目标平台` | 影响披露、时长、响度和封面/MV交接要求 |

## 阶段表

| key | 阶段 | owner | gate |
|---|---|---|---|
| `setup` | 项目骨架 | `song-craft/scripts/init_project.py` | deterministic |
| `brief` | A&R 简报 / 参考边界 | `song-craft/scripts/song_brief.py + reference_pack.py` | target listener + reference boundary |
| `lyrics` | 立项 + 词 | `song-lyrics` | user-review + singability check |
| `song_form` | 旋律/和声/曲式草图 | `song-craft/scripts/melody_chord_packet.py` | chord sheet + topline notes |
| `compose_plan` | 作曲任务包 | `song-compose/scripts/compose_song.py` | settings + lyrics |
| `takes` | 多版生成 / 注册 | backend + `compose_song.py register` | take manifest |
| `selection` | 挑版定稿 | `compose_song.py score/select` | user-listening |
| `revision` | timecode 局部返修 | `song-compose/scripts/revision_plan.py` + backend | blocking notes resolved/accepted |
| `cover` | 翻唱/换声 | `song-cover` | voice authorization |
| `review` | 质检 | `song-review` | machine + listening checklist |
| `mix_signoff` | 表演/混音签核 | `song-review/scripts/mix_signoff.py` | receipt bound to pre-master hash |
| `master_delivery` | 交付母版格式归一 | `song-craft/scripts/master_delivery.py` | mix signoff + lossless receipt |
| `master_qc` | 混音/母带检查 | `song-review/scripts/master_check.py` | audio delivery quality |
| `rights` | 权益元数据 | `song-craft/scripts/rights_metadata.py` | split sheet + rights metadata |
| `release_metadata` | 发行级元数据 | `song-craft/scripts/release_metadata.py` | roles + explicit/date/territory/P/C lines |
| `handoff` | 发布交付包 | `song-craft/scripts/release_pack.py` | release pack evidence |
| `feedback` | 发行数据回测 | `song-feedback/scripts/feedback_ingest.py` | real listener/platform data |

## take manifest

`歌/takes_manifest.json` 记录每一版的来源、状态、评分与定稿选择。`selected_take` 不为空时，`歌/song.wav` 应来自对应 take；若用户直接替换了 `song.wav`，下次 QA 会提醒补登记。
