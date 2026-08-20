# MV 流程与一致性审查·落地记录

> 当前基线：2026-08-20。旧的 2026-07-20 暂缓判断已被本轮实时复核取代；执行口径以 `contract.md`、`production-standards.md`、各产物 schema 与机器 validator 为准。

## 本轮已落地

| 主题 | 当前合同 | 权威落点 |
|---|---|---|
| 单一状态真值 | `_设置.md` 派生运行时；`_meta.json` 与 `_进度.md` 只是镜像。所有产物阶段完成态必须经过 output-health controller；`[x]`、`✅`、`1/1` 不再有旁路 | `state_contract.py`、`completion.py`、`progress_set.py` |
| 供应商能力 | model × channel × 输入角色/数量/组合/时长/声轨分开描述；未知组合 fail-closed；预览模型只在具名 adapter 下可用 | `video_capabilities.py`、`video_jobs.py` |
| 生成可追溯 | 任务 controls、实际提交引用、provider evidence、输出文件与当前上游逐级 SHA-256 绑定；不能只填 job id 或生成时间 | image/video receipts |
| 多镜头母片 | 按具名且绑定当前母片的真实 cut map 拆分；唯一临时目录、无覆盖写、原子登记，避免并发串片 | `video_jobs.py` |
| 歌词对齐 | 文本覆盖率与声学置信度分开；正式签收只接受 singing-specific 且 eligible 的声学证据，或具名逐行听审；stem→master 的 offset/drift 必须绑定当前音频 | alignment schema v5 |
| 时间线与色彩 | OTIO 使用整数帧与官方 adapter round-trip；每个选中输入都有显式色彩分类/变换，不能只给最终文件贴 BT.709 标签 | OTIO receipt v3、color manifest v2 |
| 音频身份 | 最终 MP4 与母版均须对原曲做 PCM 级首/中/尾相关、offset、drift 与时长核验 | delivery QC v3 |
| 披露与来源 | AI usage、ingredients、成片/母版/资产全集逐项绑定；C2PA 的 embedded、signature、trust、test credential、TSA 分开报告，并对当前签名文件实时复验 | `ai_usage.py`、`provenance.py`、`completion.py` |
| 审片与发布 | review 必须为当前机检零硬阻断后的具名签收；发布按平台/法域重算规则，上传回执必须绑定平台原始 API JSON 或 UI 导出及真实作品 URL | review receipt、`release_decision.py`、handoff receipt |

## 仍属环境前置，而非可降级旁路

- 正式 OTIO 导出需要可用的 OpenTimelineIO Python 环境；缺依赖时只能明确阻断或输出显式 preview，不能把手写 JSON 当官方 round-trip。
- 请求 C2PA 时需要 `c2patool`、生产签名凭据、信任锚和可信时间戳服务；工具缺失或 test/untrusted credential 不能伪装为可信发布证据。
- 平台上传本身仍由人或外部平台 API 完成。本仓库验证复制进作品根的原始回执/导出、哈希、remote asset id 与作品 URL，不声称能从离线环境证明平台持续在线。

## 暂不升为机器硬闸

- VLM 对构图与审美的裁决仍是辅助意见；只有可复算的像素、时序、哈希、schema 和具名签收进入硬门。
- 纯审美偏好不设伪精确阈值；通过候选比较与具名 picture/review sign-off 留痕。
- 平台政策会变化；内置 ruleset 必须带版本和核验日期，未知平台一律要求当前人工政策复核，不静默套用别的平台规则。

## 复审触发条件

任一模型/渠道公开能力、平台披露规则、C2PA 规范、候选采集日期或产物 schema 变化时，先刷新官方来源和 capability/ruleset 版本，再运行 consistency charter、全量 MV 测试、skill 统计与跨线独立性审计。
