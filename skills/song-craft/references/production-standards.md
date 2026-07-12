# Song 制作标准与阶段闸门

采集日期：2026-07-11。平台策略会变化；涉及交付规格时先核对官方来源。

## 标准分层

- **硬标准**：输入缺失、权利不明、音色未授权、音频损坏、阶段证据失败、hash 失配、严重削波、无法取得正式测量。这些阻断下游。
- **项目标准**：brief 中的目标听众、核心承诺、hook 策略、目标时长、声音身份；song form 中的 BPM、拍号、段落功能、和声与音域决策。它们必须明确，但答案由项目决定。
- **建议标准**：标题进入副歌、重复句、字数对称、流媒体响度参考、短视频 hook 到达时间。偏离不自动等于失败，需记录创作理由。
- **人判标准**：旋律记忆点、情绪可信度、咬字、编曲层次、混音平衡。必须结构化试听并绑定音频 hash，脚本不伪装能替代听觉判断。

## 阶段 Definition of Done

| 阶段 | 必要输入 | 完成标准 | 证据 | 失败回流 |
|---|---|---|---|---|
| A&R brief | `_meta`、用途、听众 | 核心承诺/声音身份/hook 策略/成功指标明确 | `song_brief_check.json passed=true` | 重写 brief |
| 参考边界 | 参考曲或明确无参考 | 每个参考只迁移抽象属性，列出不得复制项 | `reference_pack_check.json` | 重做 reference pack |
| 歌词/prosody | 结构化歌词 | 无占位；按曲式 profile 检查副歌、密度、行长与可复用乐句 | `lyric_prosody.json` | 回 `song-lyrics` |
| 曲式/和声/topline | 歌词与 brief | BPM 数字、拍号、段落功能明确；通用和弦循环不得冒充已作曲 | `song_form_check.json` | 重做 form/和声草图 |
| 作曲任务 | 上述四项通过、权利/音色合法 | compiler 只提交后端支持字段；输入文件 hash 固化 | `quality_gate_compose.json` + manifest v3 | 补合同或带理由 waiver |
| 多版挑版 | 已登记 take | 六维 `hook/melody/vocal/arrangement/mix/brief_fit` 全部评分；人判记录绑定 audio hash；单项不低于 2/5；阻断级 timecode note 已关闭 | `take_review.json` + `quality_gate_select.json` | 优先局部返修，再重评 |
| 局部返修 | timecode note + 源 take | 支持 repaint 的后端按区间修复；不支持时才整首重生；任何结果登记为新 take | `revision_jobs.json` | 执行 job 后回到盲听 |
| pre-master | 选中 take | `song.wav` 与 `混音/pre_master.wav` 有选择 receipt 和 hash；歌词对齐、咬字、情绪、平衡、兼容性和技术接缝经人工试听 | `takes_manifest.selection_receipt` + `mix_signoff.json` | 回局部返修/重混 |
| 交付母版 | 已批准 pre-master | 无隐式响度归一；生成 24-bit PCM，保留源采样率，不伪装为艺术母带 | `导出/master_delivery.json` | 回混音/母带决策 |
| 母带 QC | `导出/master.wav` | ITU-R BS.1770 integrated loudness、true peak、LRA 测量完整；严重失真/不可测阻断 | `master_check.json` 绑定 master hash | 回混音/母带 |
| 权益/发行 | split、录音权利、release metadata、AI 披露、母带 QC | original/cover/remix/interpolation 明确；sample 与音色授权单义；title/artist role/language/explicit/date/territory/P/C line 齐备；所有证据 hash 新鲜 | `rights_metadata_check.json` + `release_metadata_check.json` + `release_pack.json` | 补证据并重建 |
| 反馈 | 平台/experiment/take/样本量 | 只比较同 experiment；比例输出 95% Wilson 区间；小样本和宽区间不驱动改歌 | `feedback_summary.json` 绑定发行音频 hash | 扩样本，不直接改歌 |

## 音频交付解释

- ITU-R BS.1770-5 是响度和 true-peak 测量算法依据；脚本通过 ffmpeg `loudnorm` 分析模式取得 integrated LUFS、dBTP 和 LRA。
- Spotify 的 -14 LUFS 是播放器归一化参考。它不是要求所有母版统一压到 -14 LUFS；脚本只对异常响度和编码 headroom 给 warning。
- Apple Digital Masters 需要 24-bit 源文件，并要求用当前 Apple AAC 编码链试听。`apple_digital_masters` profile 会把低于 24-bit 作为 blocker，但编码试听仍需制作人完成。
- EBU R 128 的 -23 LUFS 面向广播节目归一化，不作为音乐流媒体母版的默认艺术目标。

## 官方依据

- ITU-R BS.1770-5, *Algorithms to measure audio programme loudness and true-peak audio level*: https://www.itu.int/rec/R-REC-BS.1770
- Spotify for Artists, *Loudness normalization*: https://support.spotify.com/artists/article/loudness-normalization/
- Apple, *Apple Video and Audio Asset Guide / Apple Digital Masters*: https://help.apple.com/itc/videoaudioassetguide/en.lproj/static.html
- EBU R 128, *Loudness normalisation and permitted maximum level*: https://tech.ebu.ch/publications/r128
- IFPI, *ISRC Handbook*: https://isrc.ifpi.org/images/downloads/ISRC_Handbook.pdf
- ACE-Step official inference documentation: https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/INFERENCE.md
- DDEX, *Communicating titles in ERN and MEAD*: https://kb.ddex.net/implementing-each-standard/best-practices-for-all-ddex-standards/guidance-on-releaseresourcework-metadata/communicating-titles-in-ern-and-mead/
- Spotify for Artists, *Music metadata guidelines*: https://support.spotify.com/artists/article/metadata-formatting-guidelines/
- U.S. Copyright Office, *Copyright and Artificial Intelligence, Part 2*: https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf
- NIST/SEMATECH, *Confidence intervals for proportions*: https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm

## 项目化解释

- `mix_signoff` 的八项是本项目 Definition of Done，不冒充全球统一混音标准；它解决的是“谁听过哪一版、确认了什么”的证据问题。
- 人类贡献说明不是平台普遍上传字段，但在 AI 参与较深时是权利判断和可主张作者性的必要项目证据；只有 prompt 不等于充分人类作者贡献。
- `>=100/500 plays` 仍是项目决策纪律；真正的不确定性同时看 Wilson 区间宽度，不能只看固定样本数。
- ACE-Step v1.5 已提供 `repaint/cover/lego/extract/complete` 等任务类型；局部问题优先 repaint，避免无谓重生成并降低其他段落漂移。

## 例外规则

实验性草稿可用 `--waiver-reason` 跳过 compose/select 阻断，但理由至少 10 字并写入 gate receipt。waiver 只允许继续探索，不把失败证据改写为通过，也不能让正式 release pack 绕过母带、权利和 hash 新鲜度要求。
