# 流程自审操作手册（模式②）—— 让产线可重复自我优化

把"人工复盘整条 n2d"固化成一条可复跑流程。默认产出 = 一份**建议报告**（report-only，不自动改 skill / Q&A / 模型矩阵）。

## 何时跑
- 用户主动要（"n2d 还能优化啥""过一遍流程"）。
- 每产出一批集后的阶段复盘。
- **接了新模型/能力时**（新生图模型/渠道、新生视频模型/渠道、新配音后端、平台出了新一致性/口型/音画特性）——这是最高价值触发点。

## 本地静态自审 + 独立 meta-audit（先跑）
联网前先确认产线自身没有明显治理漂移：

```bash
python3 skills/n2d/n2d-review/scripts/self_audit.py --json
python3 skills/n2d/n2d-review/scripts/meta_audit.py --json
# 要声称 adversarially-tested，必须实际运行：
python3 skills/n2d/n2d-review/scripts/meta_audit.py --run-tests --json
# 或随总自审：python3 skills/n2d/n2d-review/scripts/self_audit.py --run-meta-tests --json
```

默认两者都只读、不联网、不改文件；显式 `--run-tests` / `--run-meta-tests` 会执行登记的 pytest 回归，但不写生产状态。只有显式给 `--out PATH` 时才把与本次 JSON stdout 相同的完整报告原子落档，不修改 skill、`_进度.md` 或 gate 状态。`self_audit.py` 检查 `_进度.md` 并发安全、gate 单入口、横切覆盖率、行业基准外置、detector 治理和文档体量，并自动嵌入后一份 meta 报告；`meta_audit.py` 独立核对关键质量声明的五段证据链：

1. `declaration`：SKILL/宪法到底承诺了什么；
2. `implementation`：是否有实际代码，而非只写文档；
3. `invocation`：实现是否从生产/审计入口可达；
4. `test`：是否有正常路径回归；
5. `counterexample`：是否有能击穿错误实现的反例。

默认对抗/变形探针覆盖已经在实审中出现过的自证循环，包括：

- 核心人物把下游 `build_tier` 自报为低档后逃过多视图；
- 结构化参考有非空路径但 `status=planned`，被 truthy 判断伪装成 ready；
- 必需视角 bucket=`fail`，但删除顶层 verdict 后审计失明；
- 只有 PNG 签名/IHDR/IEND 的空壳带自洽哈希，被当成已看过的真实像素；
- 同时手改 registry 与 pack，塞入明显自动化 reviewer 标识、无时区时间、空 criteria 或缺 `confirmation={"kind":"explicit_current_pixels_acceptance","accepted_current_pixels":true}` 后逃过 consumer；
- SKILL 写“硬伤/不得落档”，实现却只发 WARN；
- `move/merge/split/rewrite` 只签 decision，或 receipt 未绑定改前合同、新左右 raw SHA 与 source mapping 也通过；
- report-only 子脚本 exit=0 但结构化 `status=warn`，却因旧 sidecar 被缓存为 pass；
- memory-anchor 本轮 unavailable 时不覆写旧 ready plan，让过期证据复活。

人物多视图、章节边界、记忆锚与仓库级命令的完整落地清单见 `production_acceptance_v2.md`。

需要新增题材/后端/项目反例时，用纯 JSON fixture pack 插入，不执行 fixture 代码：

```bash
python3 skills/n2d/n2d-review/scripts/meta_audit.py \
  --fixture <meta-fixture.json> --json
```

fixture 顶层为 `kind=n2d_review_meta_fixture_pack, version=1`，可含 `claims[]` 与 `probes[]`；每个静态 requirement 使用 `path`、`patterns[]`、可选 `glob/mode`。这让外部审计者能加反例，不必修改自审器本身。

fixture 本身仍不执行代码。若 probe 还提供本仓相对 `runtime_tests[]` pytest nodeid，只有显式加 `--run-tests` 才执行；报告中的 runtime receipt 会记录命令、exit code、当前 guard/test 文件 SHA 与输出尾部。仅扫描到 `def test_*` 或 guard 字符串时只能得到 `adversarial-test-coverage`，默认 `adversarially-tested=not_run`。

### 结论可信层级

每次结论必须分开写，不能把三层压成一个 PASS：

| 层级 | 只证明什么 | 不证明什么 |
|---|---|---|
| `self-checked` | 声明、实现、调用可静态追溯 | 行为真的能抓反例 |
| `adversarial-test-coverage` | 静态能找到已登记 guard、测试和反例（defined-only） | pytest 在当前代码上真实执行过 |
| `adversarially-tested` | 本次登记的 pytest nodeid 运行成功，收据绑定当前 guard/test SHA | 未知反例不存在、未来代码仍会通过 |
| `externally-grounded` | 当前已登记 `external_required` claims 的官方/论文等来源完成 provenance 与实现映射 | 未登记声明或整个 n2d-review 均获外部验证；gate 在独立留出样本上的误报/漏报率 |
| `externally-calibrated` | 登记的独立 held-out/盲法校准合同完整、当前 artifact SHA 有效、FNR/FPR 过预声明阈值 | reviewer 真实身份或组织独立性已获认证；未知盲区不存在、审查或结果无偏、跨题材普适 |

**0 block / 0 warn，甚至 `externally-calibrated=complete`，也不得表述成“无盲区”“审查无偏/结果无偏”。**它只表示当前登记的静态链、已知反例和这次锁定样本没有发现超阈缺口。进入联网对标前可以要求本地 WARN 清零，但未做独立留出实验时 `externally-calibrated=not_run` 必须如实保留。

逐视图收据里的 `reviewer` 与 `confirmation={"kind":"explicit_current_pixels_acceptance","accepted_current_pixels":true}` 也是同一信任边界：它们只构成“该标识声明已按当前 SHA 查看指定 `character_id/form/library_tier/view/path/verdict/reviewer/reviewed_at/png_sha256/registry_binding_fingerprint/registry_binding_fingerprint_kind/review_contract/criteria/confirmation`”的本地合同，consumer 能拒绝空值和明显自动化标识，但不能据此认证真实自然人或职责独立。需要强身份/独立性保证时，必须另接本地产线之外的认证 reviewer ID、签名或审批系统收据，并绑定同一对象合同与当前 artifact SHA。

### 外部证据 provenance schema

联网结论不能只留一条 URL。先看机器 schema：

```bash
python3 skills/n2d/n2d-review/scripts/meta_audit.py --print-evidence-schema
```

`version=1` 是向后兼容的**来源 grounding 包**；官方链接、论文和实现映射不等于性能校准：

```json
{
  "kind": "n2d_review_external_evidence",
  "version": 1,
  "evidence": [{
    "claim_id": "turnaround_alignment_enforcement",
    "claim": "多视图应同尺寸、同基线对齐",
    "claim_type": "deterministic_contract",
    "source": {
      "title": "来源标题",
      "url": "https://...",
      "kind": "official"
    },
    "checked_at": "2026-07-14",
    "confidence": "high",
    "implementation_mapping": [{
      "path": "skills/n2d/n2d-image/scripts/image_qc.py",
      "symbol": "audit_turnaround_alignment",
      "enforcement": "warn",
      "rationale": "先生成可复算几何证据并交人审"
    }]
  }]
}
```

`version=2` 仍用同一 `evidence[]` 做 grounding；只有额外的 `calibrations[]` 能改变 `externally-calibrated`：

```json
{
  "kind": "n2d_review_external_evidence",
  "version": 2,
  "evidence": [],
  "calibrations": [{
    "claim_id": "turnaround_alignment_enforcement",
    "calibration_id": "CAL-2026-07-heldout-01",
    "evaluated_at": "2026-07-14T09:00:00+08:00",
    "reviewer": {
      "reviewer_id": "independent-reviewer-01",
      "affiliation": "independent-qc-lab",
      "independent_from_implementation": true,
      "independent_from_sample_selection": true,
      "conflict_of_interest": "none_declared"
    },
    "held_out": true,
    "blind_to_gate_result": true,
    "protocol": {
      "predeclared_at": "2026-07-13T09:00:00+08:00",
      "selection_locked_before_evaluation": true,
      "thresholds": {"max_fnr": 0.10, "max_fpr": 0.05},
      "sampling": {
        "method": "stratified_random",
        "population_description": "角色档位 × 镜头类型",
        "population_size": 1000,
        "sample_size": 100,
        "strata": [
          {"name": "dialogue", "sample_count": 50, "selection_rule": "seeded random"},
          {"name": "action", "sample_count": 50, "selection_rule": "seeded random"}
        ]
      }
    },
    "ground_truth": {
      "adjudication_method": "two-pass independent labels",
      "adjudicator_ids": ["adjudicator-a", "adjudicator-b"],
      "disagreement_resolution": "third adjudicator majority",
      "blind_to_gate_result": true,
      "adjudicators_independent_from_implementation": true
    },
    "results": {
      "confusion_matrix": {"tp": 45, "tn": 48, "fp": 2, "fn": 5},
      "fnr": 0.10,
      "fpr": 0.04
    },
    "artifacts": [
      {"role": "protocol", "path": "校准/protocol.json", "sha256": "<64-hex>"},
      {"role": "sample_manifest", "path": "校准/sample_manifest.json", "sha256": "<64-hex>"},
      {"role": "predictions", "path": "校准/predictions.jsonl", "sha256": "<64-hex>"},
      {"role": "ground_truth", "path": "校准/ground_truth.jsonl", "sha256": "<64-hex>"}
    ]
  }]
}
```

校验命令：

```bash
python3 skills/n2d/n2d-review/scripts/meta_audit.py --evidence <evidence.json> --json
# 或随总自审：
python3 skills/n2d/n2d-review/scripts/self_audit.py --evidence <evidence.json> --json
```

校验器会确认 grounding mapping 的 `path` 位于本仓、文件真实存在、`symbol` 能在目标文件中找到；`externally-grounded=complete` 只覆盖完成这些检查的已登记 `external_required` claims。当前报告中的 `4/4`（或 claims 增减后的任意 `N/N`）只描述本次登记范围，不外推到整个 n2d-review。校准侧会机器复算混淆矩阵、FNR/FPR 与样本量，验证预声明时间早于评测时间，并逐项核对四类 artifact 的当前路径与 SHA。任一独立性/held-out/盲法/抽样/裁决/指标/文件绑定缺失均为 `invalid`；指标完整但超阈为 `failed`；只覆盖部分 `external_required` claim 为 `partial`；完全没有 calibration 行为 `not_run`。这些结构字段仍不认证 reviewer 的真实身份或组织独立性；需要作该强声明时另附外部认证 ID、签名或审批收据。硬闸来源克制遵守设计宪法 B10：`market_post/vendor_marketing/secondary`、`confidence!=high`、`quality_heuristic/market_observation` 不能直接映射 `enforcement=block`。外部材料最多形成 grounding 或提出假设，不能靠权威链接升级为“已校准”。

## 三轴取证（联网，必带年月）
按行业三大验收维分轴搜，每轴落到"当前 SOTA 做法 + 证据链接 + 日期"：

| 轴 | 搜什么 | 映射到 n2d 的 |
|---|---|---|
| **一致性** | 定妆/参考/相似度 KPI、多视图、IP-Adapter/LoRA、多镜故事板、self-storyboard、同一生图模型/渠道贯穿 | n2d-image / n2d-script 角色场景卡 / n2d-review gate |
| **效率** | 单分钟成本、周期、批量自动化、CLI 直调 | 全线（重抽预算/voice-first/批量并发任务） |
| **可控性** | 口型 lip-sync、原生音频、音画同步、运镜控制、节奏工具 | n2d-video / n2d-voice / n2d-compose |
| **模型演进**（横切） | 各 stage 当前最强模型（图/视频/配音）及其新语法 | 各 stage 的 platforms.md / backends.md |

> 搜索词带"2026""最新""最佳实践""翻车"可用于发现候选假设；中英文各搜一轮。最终证据优先官方/法规/标准/论文/第一方量测。实战贴只能作风险线索或辅助解释，不能单独决定硬闸。

## 固定复核点（每次流程自审都要过）
- **审查器自身是否可被击穿**：五联覆盖是否完整；默认对抗场景是否有 guard + 反例 + runtime nodeid；是否把静态 test 文本冒充 tested，或把 `0 warn` / calibration complete 误写成无盲区/无偏。
- **外部证据强制力**：每条联网结论是否有 claim/source/date/confidence/implementation mapping；营销/市场观察是否被误升为 BLOCK；官方/论文链接是否被错误计作 calibration；`grounded N/N` 是否被错误外推为整个 n2d-review 已获外部验证。
- **外部校准真实性**：是否独立审阅、held-out、blind、阈值预注册、样本分层锁定、ground truth 独立裁决、混淆矩阵可复算、FNR/FPR 过阈，并绑定当前本仓 artifact SHA；若声称 reviewer 身份或组织独立性已认证，是否另有外部认证 ID、签名或审批收据，而非只填本地字符串。
- **image_qc 精度闭环**：视频/合成前是否强制消费 `生产数据/image_qc/<ep>/image_qc_<ep>.json`，并要求 `precision_level=full`、`hard_blocks=0`；缺依赖、degraded/none 或旧报告不得进入视频。
- **交付口径 vs 生成口径**：仪表盘是否同时展示 `generation_pass_rate` 与 `deliverable_pass_rate`；任何 QA block 都应让可交付通过率归零，避免把生成尝试成功率误当成验收通过率。
- **原生音画物理一致性**：`制作模式=原生音画` 是否在视频总览和人审中覆盖声源归属、口型策略、材质/动作声、空间声学、字幕/后期策略；成片后是否有 whisper/字幕对齐兜底。
- **参考资产机器清单**：定妆、表情、尾帧、场景/道具 reference 是否有 registry/manifest 级证据，而不是只在 prompt 文本里写“参考图”；缺 machine-readable manifest 的建议优先落到 gate 或 image_qc。
- **后端适配层**：生图/生视频的负向提示、主体锁、首尾帧、多参考、原生音轨策略是否经能力矩阵/adapter 归一；不要把某平台文案直接当跨平台契约。

## 对照 → 差距清单
逐 stage 把"基准做法"对到 `n2d-*/SKILL.md` + `references/*` + `n2d/Q&A.md`：

- **先查已实现**：很多"新做法"产线早做了（如两层定妆库、voice-first、导演节奏）。**已实现的不重复立项**——只在报告里标"✅ 已覆盖"一行带过。
- **找真差距**：只记"基准有、n2d 没有或更弱"的。每条写成：
  ```
  差距：<一句话>
  证据：<链接>（采集 <年-月>）
  落点：<改哪个 skill 哪段 / 或新立项>
  优先级：must（影响成片质量/合规）/ optional（增稳/提效）
  可脚本化：是/否（是→能进 mechanical_check）
  ```
- **分三类处置**：① 硬约束（铁律/Q&A 条目）② 可选增强（opt-in 段）③ 机检项（脚本）。

## 模型矩阵刷新（默认只给建议）
`n2d/references/模型矩阵.md` 是各轴 **SOTA vs n2d 默认 vs 升级触发** 的防过期快照。每次跑模式②都要检查它是否过期，并在报告里给出**刷新建议 / diff 草案 / 来源链接**；只有用户明确要求“刷新矩阵/落地本轮自审”时，才实际修改该文件：改三表的"SOTA 快照(年-月)"列 + 顶部采集日期 + 升级触发。这避免默认流程自审一边说 report-only、一边偷偷改产线。

## 起草 + 落地（人确认后）
1. 高价值项**直接起草** `Q&A` 新条目草案（记结论 + 决策 + 落点表，像 Q28/Q29 那样），作为"自我优化"的候选留痕。
2. 建议的 skill edit 写成 diff 级描述（改哪段、加什么铁律/段落）。
3. **改任何 skill → 必同步 `skills/README.md` 索引**（仓库硬约定，缺了视为未完成）。
4. **默认不自动改产线**：模式②产报告，用户拍板后再由对应 skill / 人执行编辑。`refresh-matrix`、写 Q&A、改 SKILL.md、改 README 都属于落地模式，不属于默认 report-only。默认报告只输出给调用方；正式验收可用 `--out <作品根>/生产数据/...json` 留当前 SHA 绑定收据，但**不得在 skill 目录存 `_流程自审_*.md`**，也不得把旧报告当成本轮重跑替代品。

## 防过期 / 防噪声铁律
- 每条建议**带来源链接 + 采集日期**；旧报告里的建议可能已被采纳或已过时，落地前重新核对当前 skill。
- 容错铁律同模式①：只报"真差距"，不把"换种说法会更好"的主观偏好堆进来。
- 模型名/特性会变（如某生视频模型的多镜语法、某配音后端的情绪集）——写"能力"而非死绑某产品版本号，绑版本号的放 `platforms.md`/`backends.md` 档案里，正文写通用原则。

## 一次自审的标准产物
```
# n2d 流程自审 <年-月-日>
## 结论可信层级
  - self-checked: complete/partial/not_run
  - adversarial-test-coverage: complete/partial/not_run（静态 defined-only）
  - adversarially-tested: complete/partial/failed/invalid/not_run
  - externally-grounded: complete/partial/not_run（仅覆盖已登记 external_required claims；写明 N/N）
  - externally-calibrated: complete/partial/failed/invalid/not_run
  - 限制：0 warn 或 calibration complete 也不代表无盲区/无偏
## 三轴取证摘要（含来源链接）
## 差距清单（按优先级）
  - [must] …  落点：n2d-xxx 某段
  - [optional] … 
## 已覆盖（✅ 一行带过，证明查过没重复）
## 模型矩阵刷新建议（只给 diff 草案，默认不写文件）
## 建议落地顺序 + 是否需要改 README
```
