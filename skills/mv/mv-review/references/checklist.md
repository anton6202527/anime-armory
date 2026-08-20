# 作品质检 —— 全维度清单（看什么 · 怎么判 · 定级）

> 落到 mv 制MV 产线。**机** = `mv_check.py` 确定性查；**判** = LLM 语义判（含并排读图）。容错铁律：只记真问题。
> 正向标尺：卡点 `mv-beat/SKILL.md` · 运镜/动作 `mv-video/references/prompt_format.md` + `action_knowledge.md` · 一致性 `mv-image/references/prompt_format.md` + `visual_consistency.md` · 合成 `mv-compose/references/usage.md`。

## A. 视觉一致性（主角、场景、画风）

> 判到崩脸/漂移要"回 `mv-image` 重出该镜"时，重出的重抽上限按作品 `重抽预算策略` 档位走（默认 预算充足=抽到自检过；主角脸/画风零漂移容忍）——别在报告里要求无止境重抽。

| 维度 | 机/判 | 怎么查 | 定级 |
|---|---|---|---|
| 主角崩脸 / 断层 | 判（+机选） | `出图/段落/图片/镜头*.png` 与 `出图/共享/图片/定妆_*.png` 并排比脸型/发型/服色/锚点；装库则机给余弦相似度（阈值自标定：定妆组 `lead_floor`，未标定回退 0.45） | 漂到识别不出 🔴 / 轻漂 🟡 |
| 定妆组内漂移（floor 被拉低） | 机 | `image_qc` 的 `costume_outliers`：某定妆变体 vs 主参考显著低于组内其它——漂移定妆会放松整套脸检地板；确认后重抽该定妆 | 🟡 |
| 场景漂移 | 判 | 同场景跨段背景是否引用同一定妆场景图 | 🟡 |
| 画风跳变 | 判 | 是否守视觉蓝图 global_style；有无中途换生图工具的"一致性税" | 🟡 |
| 道具/配饰漂移 | 判 | 反复入镜道具一致 | 🟢/🟡 |
| 画面糊/低质 | 判 | 出图/clip 分辨率清晰度够投放 | 🟡 |
| 单曲视觉一致性包缺失 | 判 | `lead_identity_anchor / global_style / palette_anchor / section_look / motif_ledger` 是否在视觉蓝图/设定/分镜里被继承；MV 可换段落 look，但不能一支歌内换脸换主画风 | 🟡 |
| 参考输入/LoRA 未登记 | 判 | 若 `_设置.md` 写 `MV一致性增强=指定参考图/后端主体库/+LoRA`，检查 prompt 是否含 `reference_inputs`、参考图路径/主体 ID/LoRA trigger+底模+授权说明 | 🟡 |
| 构图重复 / 景别单调 / 静态长镜 | 机（+判） | **事前**：`shot_variety_audit.py` 读 `clip_plan.shot_design` 查同 (场景,景别,机位,运镜) 反复、连续同场景 run 景别<3 种、副歌 key 镜静止运镜、单场景占比过高、母题过用、大变化镜头缺参考锚。**事后**：`image_qc` dHash 查跨 clip 首帧撞脸、首↔尾帧几乎不动的静态长镜。都是 advisory（MV 命门=视觉不重复，但 recurring hook 可能刻意，只 warn 交人判） | 🟡 |
| 大变化镜头缺参考锚（易漂） | 机 | `shot_variety_audit` 的 `reference_gap`：近景/极端角度/换装/有禁漂约束的 clip 却没规划 `reference_inputs`——最易崩脸，出图前按 `MV一致性增强` 补参考图/后端主体库/LoRA | 🟡 |
| 漂移风险预测未跑/有 high 未处理 | 机 | **事前**：`mv-image/drift_risk.py` 逐 clip 打 high/medium/low（近景/大表情/极端角度/逆光/换装/长间隔复现/多主体/缺锚 + 定妆组基础分）；high 镜出图前挂参考、优先打样；image_qc 实测脸警自动回灌升 high | 🟡 |
| 正式大盘未打样直接全量 | 机（+判） | `mv-plan/pilot_matrix.py`：≥12 clip 的正式项目全量出图前应有打样矩阵（开场钩/副歌爆点/最高风险近景/最大运动/换装首镜 3-5 镜），打样验收（脸/风格/爆点体感）通过再全量——全量返工=整曲重烧积分 | 🟡 |
| 现实验证器空转（fail-closed） | 机 | `consistency_findings` 的 `verifier_coverage`：脸检/palette/dHash/视频脸检/抽帧感知「适用但休眠」（后端缺失静默降级）→ warn 现形；报告"跑过 QC"≠检测器真出活 | 🟡 |
| 副歌复现无升级 | 机（+判） | `craft_audit` 的 `chorus_no_escalation`：第 k 次副歌没有新场景/新景别/新母题/更高运镜能量/更多镜——传统结构律：每次副歌回归都加码，末副歌给全曲最大 payoff（余韵型收束刻意例外） | 🟡 |
| 主副歌无动静对比 | 机（+判） | `craft_audit` 的 `no_dynamics_contrast`：副歌平均运镜能量 ≤ 主歌（主歌收着副歌放，能量差=冲击）；主歌拉满 → headroom 耗尽 info | 🟡 |
| hook 不上脸 | 机（+判） | `craft_audit` 的 `hook_not_sung_on_camera`：副歌无对镜演唱近景（表演线是三线之锚）；全曲无表演线 → info 自检是否刻意纯叙事 | 🟡 |
| 冷开场过长 | 机 | `craft_audit` 的 `cold_open_too_long`：首个钩信号（key/副歌/动作峰值/近景）前累计 >8s——竖屏前 3 秒定生死；把副歌意象前置当 cold open 是常用解法 | 🟡 |
| 关键镜单候选裸奔 | 机（+判） | `craft_audit` 的 `key_clip_single_candidate/key_clip_coverage_unplanned`：副歌/key 镜应出 2-3 张首帧候选再挑（shoot options for the edit 片场惯例） | 🟡 |
| bridge 不换气 / 词画零呼应 | 机（info） | `craft_audit` 的 `bridge_no_look_shift`（音乐转折画面没跟上）与 `lyric_visual_echo_zero`（歌词意象与画面零重合）——弱信号只提示自检 | 🟢 |
| 切点系统性晚切 | 机 | `pacing.late_cut_bias`（mv-score 报告）：对齐切点中晚于拍点 >0.04s 的比例 >30%——剪辑手法：压拍或提前 1-3 帧落刀，晚切读感"慢半拍" | 🟡 |
| 出图来源链缺失/漂移 | 机 | 每张正式帧必须有统一 model+channel、实际 prompt、reference inputs、asset SHA-256；prompt/参考/图片被替换后收据应失效 | 正式版 🔴 |
| 同场景硬切色跳 | 机（+判） | `video_qc` 接缝 `same_scene_hard_cut_color_jump`：同 location 相邻镜主色/色温跳变（>120 RGB 距离）——非卡点冲击而是调色/生成不稳时算问题；卡点切的有意跳变豁免。导演确认刻意的接缝用 `video_qc --accept-discontinuity FROM:TO --reviewer --notes` 具名签进 `制片/intentional_discontinuity.json`，签署后不再误报 | 🟡 |
| 重画率/take 数失控（止损） | 机 | `consistency_findings` 的 `production_economy`：出图重画率 >35% 或平均每 clip take >3 → 积分烧穿前兆，回头修 prompt 锚点/参考图，别硬抽 | 🟡 |
| 演唱镜口型对不上 | 判 | **正面跟唱大特写**主角嘴型是否对得上人声（仅 `演唱口型≠关闭` 时要求；远景/侧脸/B-roll/空镜豁免）。对不上→用人声音频条件或后期 pass（LatentSync 优先）重做该 clip，或回 `mv-plan` 改分镜规避。见 `mv-video`「演唱口型对齐」 | 🟡 |

## B. 卡点 / 节奏（**MV 的命** —— 对 `mv-beat` 卡点原则）

| 维度 | 机/判 | 怎么查 | 定级 |
|---|---|---|---|
| beatgrid 来源与结构 | 机+判 | 可解析、有 beats/downbeats；绑定当前歌曲 SHA-256；正式版小节首相位与全曲 sections 由具名听审确认 | 正式缺证据/损坏 🔴 |
| BPM 合理 | 机 | bpm 在 ~40–220；偏低/偏高疑半速/倍速 | 嫌疑 🟡 |
| beats/downbeats 单调 | 机 | 时间戳严格递增、在歌长内 | 乱序 🔴 |
| clip 时长卡点 | 机（需 ffprobe）+判 | 每 clip 时长 = 相邻卡点之差；**clip 疑似等长 = 不卡点** | 等长 🟡 |
| 副歌密 verse 疏 | 判 | 副歌每 downbeat 切（碎）、verse 缓（2–4 拍） | 🟡 |
| 爽点对 downbeat | 判 | 高潮画面同帧砸在 downbeat 上 | 🟡 |
| 动作家族空泛 | 判 | `clip_plan.json` / 视频 prompt 是否有 `action_family/action_peak/transition_motif`，且一 clip 一个主动作；只写“炫酷动作/酷炫运镜”不给可执行动作链 | 🟡 |
| 动作强度不合段落 | 判 | verse 动作太满、副歌没高光动作、bridge 没反转动作；对 `action_knowledge.md` 段落强度表 | 🟡 |
| clip 总时长 ≈ 歌长 | 机（需 ffprobe） | clip 总和 vs `歌/song.*`/beatgrid.duration | 差大 🟡 |

## C. 卡拉OK字幕（确定性为主 → 机检）

| 维度 | 机/判 | 怎么查 | 定级 |
|---|---|---|---|
| 占位未精修 | 机 | `lyrics.lrc`/`karaoke.ass` 含 `待`/`TODO`/`（待` | 🔴 |
| 时间戳越界 | 机 | 字幕时间 > 歌长 | 🟡 |
| 时间单调/不重叠 | 机 | 行起始递增、不与上行重叠 | 🟡 |
| 行数对账 | 机 | 字幕行数 vs `词/lyrics.md` 词行数 | 差大 🟡 |
| 卡拉OK视觉 | 判 | 逐字高亮可读、位置不挡主体、竖屏适配 | 🟢/🟡 |
| 词↔实唱一致 | 判 | 对齐偏差大多因词与实唱不符 | 🟡 |
| 对齐收据新鲜 | 机 | alignment report 绑定当前 song/master/lyrics hash；低覆盖 waiver 有 reviewer + notes | 正式版 🔴 |

## D. 音画 / 合成（对 `mv-compose`）

| 维度 | 机/判 | 怎么查 | 定级 |
|---|---|---|---|
| 成片有音轨 | 机（需 ffprobe） | 成片含 audio stream（MV 没声音=废） | 缺 🔴 |
| 成片时长 ≈ 歌长 | 机（需 ffprobe） | 成片 duration vs 歌长 | 差大 🟡 |
| 画幅符合 | 机（需 ffprobe） | 分辨率宽高比 vs `_meta.aspect`（9:16/16:9） | 不符 🟡 |
| 歌是主音轴 | 判 | 整首歌作主音轨、clip 原声静音（MV 不做 ducking） | 🟡 |
| 剪辑点踩鼓点 | 判 | 切点对齐 beatgrid（不是匀速过场） | 🟡 |
| 留白/呼吸 | 判 | 间奏/outro 留白不被硬切填满 | 🟢 |
| OTIO/锁版 | 机+判 | `timeline.otio` 有 V1 画面+A1正式歌+段落/接缝 markers，receipt/edit hash 新鲜；picture lock 绑定 animatic、帧、prompt、时间线 | 正式版 🔴 |
| 母带未被截短/改响 | 机 | 输出 vs 输入歌时长 ≤100ms；integrated loudness 漂移 ≤0.5 LU；真峰值 >0 dBTP 阻断、>-1 dBTP 复核 | 越阈 🔴/🟡 |
| 交付编码 | 机 | ProRes 422 HQ/PCM 48k 母版；BT.709 H.264 High yuv420p/AAC 48k/faststart 交付版 | 正式版 🔴 |
| 审片收据 | 机+判 | 默认机检只读；只有真实 reviewer 完成人审并给出非空 notes 后显式写收据。收据绑定当前 final / master / delivery QC / provenance / AI disclosure 五个 SHA-256 | 缺签收或任一绑定过期 🔴 |

## E. 合规（非交涉项，每次必查）

| 维度 | 机/判 | 定级 |
|---|---|---|
| AI 视觉使用披露 | 机+判 | 成片有当前 `合规/ai_usage.json`，枚举、生图/视频模型与渠道、目标平台均与 `_设置.md` 一致；上传时仍独立完成平台 AI 声明 | 发布/签收前缺失或过期 🔴 |
| C2PA 结构 | 机 | requested 时 `embedded=true` 且 `structurally_valid=true`；只证明 manifest 结构可解析 | 失败 🔴 |
| C2PA 签名 | 机 | `signature_valid=true`；签名数学有效不等于发布方可信 | 失败 🔴 |
| C2PA 信任链 / 测试证书 | 机 | 分开核 `trust_checked` / `trusted` / `certificate_profile`；test certificate 只能开发验证，不得当生产可信凭证 | 未查信任链、untrusted 或 test 🔴 |
| C2PA 时间戳 | 机 | 分开报告 `signed_at`、`timestamp_validated`、`timestamp_trusted`；`signature_info.time` 只是签署时间，不能冒充 TSA。无可信 TSA 仅在 `timestamp_exception_allowed=true` 的具名交付例外下为 🟡 | 无例外且缺可信 TSA 🔴；显式例外 🟡 |
| C2PA 与平台披露边界 | 判 | Content Credentials 是可选来源凭证，**不替代** `ai_usage.json` 或目标平台上传界面的 AI 内容声明 | 用 C2PA 替代披露 🔴 |
| 输入歌权利 | 判 | 歌的词曲版权随歌（自有/授权/原创）；mv 只做视觉不改属性 | 🔴 |

## F. 完整性 / 对账（机检）

| 维度 | 定级 |
|---|---|
| `视觉蓝图.md` / `_进度.md` / `_meta.json` 齐全 | 缺 🟡 |
| `歌/song.*` 存在 vs `_meta.has_song` | 不符 🟡 |
| `词/lyrics.md` 存在 vs `_meta.has_lyrics` | 不符 🟡 |
| 段落数 vs `_meta.structure` | 不符 🟡 |
| 进度表勾选 vs 实际产物（beatgrid/出图/clip/字幕/成片） | 不符 🟡 |
| 产物快照（clip 数 / 出图数 / 字幕行数 / beatgrid bpm / 成片存在） | 🟢 信息 |

---

## 健康度概览表（报告必附）

```
维度        通过  问题(🔴/🟡)  备注
视觉一致性   —    0/1          镜头09 少年发色较定妆偏深
卡点节奏     —    0/1          Clip00/09/10/19 时长一致 → 疑似等长不卡点（ken-burns 占位）
卡拉OK字幕   ✅    0/0
音画合成     ✅    0/0          成片 20.0s ≈ 歌 19.97s · 9:16 · 含音轨
合规         ✅    0/0          AI 视觉使用披露已留痕
完整性       —    0/1          _meta.has_song=false 但 song.* 已就位（meta 未更新）
产物快照     5 clip · 5 出图 · 字幕6行 · BPM 143.55 · 成片✅
（ffprobe 缺失时 clip/成片 时长·画幅·音轨 = 跳过，非通过）
```
