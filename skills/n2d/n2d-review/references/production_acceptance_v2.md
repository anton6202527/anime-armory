# n2d 制作流程优化实施包与验收标准 v2

适用范围：n2d 拆集、人物分档定妆、多视图身份、跨集记忆锚、出图前置闸门，以及 n2d-review 自身可信度审计。本文给出可执行命令和放行条件；不把论文、厂商文档或项目经验写成“普适行业强制标准”。

## 1. 口径边界

- **有外部依据的方向**：动画工具采用正面、前 3/4、侧面、后 3/4、背面关键角度；多视图生成研究把跨视角一致性和内容漂移视为核心问题；视频评测研究把主体身份一致性拆成独立维度并做人类偏好对齐。
- **n2d 项目默认值**：`计划出场 >=10 集 → core_full`、PNG 短边 `>=512px`、首批物化 10 集、候选 Top-3、beam width 24、精修前看 5–10 集窗口、记忆锚的 gap/晚集触发规则，都是当前项目的工程启发式，不是普适行业定律。
- **“独立视角”含义**：必须是不同、可单独喂给后端的真实 PNG 路径与解码后像素；复制同字节文件、把相同像素换压缩/filter/metadata 重新编码、软链或换标签都不算独立。允许从同一张已人审通过的 turnaround 母本裁切或派生，但不同桶须有不同真实裁切像素，并登记 `derivation.method/source_path/source_sha256/crop_box`。不要求五张都独立生成。证据路径只能是解析后仍位于作品根内的规范相对路径。
- 外部来源包只会把**已登记的 `external_required` claims** 升为 `externally-grounded`；当前报告的 `4/4`（或 claims 增减后的任意 `N/N`）只表示本次登记的 N 条声明来源、日期、置信度和实现映射齐全，不代表整个 n2d-review 已获外部验证。只有独立审阅、held-out、盲法、预注册阈值、分层抽样、独立金标裁决、混淆矩阵与当前 artifact SHA 全部成立，才可写 `externally-calibrated`。

外部依据快照见 `external_grounding_2026-07-14.json`。主要来源：当前可访问的 Toon Boom Harmony 24 官方文档、CVPR 2025 CoSER、CVPR 2024 VBench、EMNLP 2020 Chapter Captor、NAACL 2025 scene segmentation 与 NIST AI RMF。

## 2. 章节划分实施与验收

### 2.1 首次粗切

```bash
python3 skills/n2d/n2d-script/scripts/split_novel.py <源小说> --out <作品根>
```

默认只物化前 10 集供试切，但 `脚本/split_plan.json` v2 必须保存全书 `source_units`、`arc_anchors`、`boundary_candidates`、全局 Top-3 beam paths 和每集 source span。`--target/--min/--max` 只能作为报告或软节奏参考，不得为了字数、时长切断场戏、爽点、因果或 cliffhanger。

### 2.2 边界审计与人工声明签收

```bash
python3 skills/n2d/n2d-script/scripts/boundary_audit.py <作品根> 1-10 --strict --json
python3 skills/n2d/n2d-script/scripts/boundary_review.py draft <作品根> 1-10 --write

# 保留边界：必须给语义证据
python3 skills/n2d/n2d-script/scripts/boundary_review.py sign <作品根> '<blocker_id>' \
  --decision keep --notes '<判断>' --reviewer '<人工声明 reviewer 标识>' \
  --semantic-evidence '<冲突闭环、爽点、钩子及下一集冷开证据>'

# 改边界：先真实修改 raw，再签应用收据
python3 skills/n2d/n2d-script/scripts/boundary_review.py sign <作品根> '<blocker_id>' \
  --decision rewrite --notes '<已实施修改>' --reviewer '<人工声明 reviewer 标识>' \
  --source-mapping-file <source_mapping.json>

python3 skills/n2d/n2d-script/scripts/boundary_review.py check <作品根> 1-10 --json
```

放行标准：

- 每个边界同时满足“上集冲突→爽点/反转→钩子闭环”和“下集前两拍可形成有效冷开”，不是只看上一集末尾。
- blocker 使用稳定 `blocker_id/code`，绑定左右 raw SHA 和 boundary contract SHA。
- `keep` 有非空 notes、semantic evidence 和人工声明 reviewer；该标识必须非空且不得使用明显自动化身份字样。
- `move/merge/split/rewrite` 的左右 raw 至少一侧必须已变化，且 receipt 绑定旧合同 SHA、当前左右 SHA 和非空 source mapping。
- 机器文件可刷新；`脚本/boundary_review.json` 与 `_拆集复核.md` 不得被续切覆盖。
- 付费卡点只在项目明确配置时执行；普通标点不得重复计为语义强钩。

边界收据中的本地 `reviewer` 同样只是人工声明标识：当前 CLI 能拒绝空值或明显自动化身份字样，但不能认证真实自然人、岗位权限或与生成流程的独立性。需要这些强保证时，应由外部身份系统或审批系统签发 reviewer ID/签名收据，并绑定同一 blocker、boundary contract 与左右 raw SHA。

## 3. 人物分档、多视图与一致性实施

### 3.1 分档真值

四档只允许：

- `core_full`：主角、核心长线、或当前计划出场 >=10 集；每个形态要求 front / three_quarter / side / rear_three_quarter / back、turnaround、body/outfit、expression/face anchor。
- `recurring_standard`：复现配角；要求 front / three_quarter、body/outfit、face anchor，侧背按镜头补。
- `named_minimal`：具名短线；要求 front、body/outfit、face anchor，近景/转头/过肩/复用时升档。
- `restricted_partial`：单集 `named_minimal` 功能角色可用结构化 restricted/no-face policy 只建手部、肩背、服装、剪影等局部；一旦复现 >=3 集、属于核心/长线或显式要求例外，则必须有 `status=approved`、reason/reviewer/allowed_parts 完整的合同，合同 `face_policy` 与角色记录完全一致，且 allowed_parts 不得包含 face/head/front/portrait/正脸/头部。

剧情推导给出最低档，显式设置只能升档。角色记录、asset bundle、角色 manifest、`reference_atlas.build_tier` 四处必须精确一致；任何一处自报降档都阻断。即使四处合谋写低，结构化 storyboard 的可见角色集数仍作为独立最低档证据：可见出场 `>=3` 集至少 `recurring_standard`，`>=10` 集至少 `core_full`；只扫结构化角色 ID，不扫散文、offscreen 或 forbidden，避免旧项目误报。

### 3.2 对当前像素逐视图签收

对每个 `core_full` 的每个形态逐项执行；expression 有多张候选时必须指定精确 path：

```bash
python3 skills/n2d/n2d-review/scripts/identity_eval_pack.py <作品根> \
  --record-current-view \
  --character-id CHAR_01 --form 常态 --view front \
  --reviewer '<角色设定终审>' --accept-current-pixels --json

python3 skills/n2d/n2d-review/scripts/identity_eval_pack.py <作品根> \
  --record-current-view \
  --character-id CHAR_01 --form 常态 --view expression \
  --view-path '出图/共享/图片/CHAR_01_常态_表情.png' \
  --reviewer '<角色设定终审>' --accept-current-pixels --json

python3 skills/n2d/n2d-review/scripts/identity_eval_pack.py <作品根> --write --json
```

若项目 `_设置.md` 已由用户明确授权“执行者实际像素目视”，执行者签收必须显式区分、不得冒充人工：

```bash
python3 skills/n2d/n2d-review/scripts/identity_eval_pack.py <作品根> \
  --record-current-view \
  --character-id CHAR_01 --form 常态 --view front \
  --review-kind executor_visual --reviewer '<视觉执行者标识>' \
  --accept-current-pixels --json
```

逐桶放行必须同时满足：

- 当前 registry 节点为 `ready/registered`，不是 `planned`；角色、形态、档位、view 和 path 精确匹配。
- PNG 可完整解码，格式/CRC/IDAT/scanline 有效，宽高均不低于 512，SHA 与当前文件一致。
- 五角、turnaround、expression 使用解析后仍在作品根内的规范相对路径和不同 decoded-pixel fingerprint；该指纹把合法 PNG 统一解码到 RGBA16 像素域，忽略压缩、filter、metadata 与 Adam7/非交错编码差异。禁止绝对路径、`..` 越界、软链/非规范别名、同图换标签、复制同字节文件、同像素重编码换 SHA、跨形态复用或普通文件伪 PNG。同源母本的不同真实裁切像素允许通过。
- binding fingerprint、对应 view 的 review contract、完整 criteria、reviewer、带时区时间齐全。默认人工路由要求 reviewer 非空且不得含明显自动化标识；执行者路由只在项目有显式用户授权时成立，并强制 `review_kind=executor_visual`、`reviewer_role=ai_visual_executor`、`human_signoff=false`。
- receipt 有 `confirmation.kind=explicit_current_pixels_acceptance` 且 `confirmation.accepted_current_pixels=true`；`bot/codex/agent/runner` 不能冒充人工 reviewer，但可在上述显式授权下以独立的 executor_visual 证据类别留痕。
- 生产 consumer 会再次从当前 registry 和当前 PNG 重算以上字段，不能只信 producer 输出。

这里的 `reviewer` 和 `confirmation={"kind":"explicit_current_pixels_acceptance","accepted_current_pixels":true}` 是**本地像素审阅声明合同**：它证明收据声明者对该收据所绑定的当前 `character_id/form/library_tier/view/path/verdict/reviewer/reviewed_at/png_sha256/registry_binding_fingerprint/registry_binding_fingerprint_kind/review_contract/criteria/confirmation` 作了当前像素确认。`human` 只是一种人工声明证据，`executor_visual` 则明确不是人工签收；两者都不能认证声明者真实身份，也不能证明其与生成、实现或选样独立。若项目需要真实身份、职责隔离或不可抵赖的强保证，必须接入本地产线之外的认证 reviewer ID、签名或审批系统收据，并让外部收据绑定同一组当前像素对象与 SHA；不能只改本地字符串。

### 3.3 出图前预检与出图后回验

出图前先跑 `image_preflight`，只有无 blocker 才能开始付费出图：

```bash
python3 skills/n2d/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_preflight
```

生成 Clip PNG 后再跑 `image`，对当前像素和出图后一致性做回验；未通过不得进入出视频：

```bash
python3 skills/n2d/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image
```

验收：两次正式 gate 的所有 load-bearing finding 均为 `block=0`；`dashboard.py gate` 必须把运行事件和 findings 落入 `生产数据/`，不能以仅打印 JSON 的裸 `n2d-review/scripts/gate.py` 调试入口代替。缺档位资产时只补共享库，不得用 `--skip-preflight`、局部 shots 或 P0 小样绕过后生成 Clip PNG。

## 4. 跨集记忆锚实施与验收

```bash
python3 skills/n2d/n2d-identity/scripts/memory_anchor.py <作品根> 第N集 --json
python3 skills/n2d/n2d-image/scripts/reference_planner.py <作品根> 第N集
python3 skills/n2d/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_preflight
```

`reference_planner.py` 此处故意不加 `--json`：默认执行会把当前计划落档到作品根供随后的 `image_preflight` 消费；`--json` 仅打印、不落档，只适合预览，不能作为本节实施命令。

放行标准：

- plan 为 v3、`status=ready`、`available=true`、episode 精确一致。
- `source_fingerprint` 同时绑定当前 identity registry、drift report、storyboard 三份 SHA。
- 每个 reinject `(character_id, form)` 只做精确匹配；多形态歧义、重复 key、缺 row、错误引用或路径越界均阻断。
- planner 的 required/consumed/unconsumed 与每个真实 Clip 的引用逐项相等；聚合计数或 summary 自报不能放行。
- 每个 reference path 与当前 SHA 一致；任何旧 ready sidecar、删除后的缓存或本轮 `status=warn` 均不能复活。
- 第一集/首次视觉集没有更早 PNG 时，允许“ready + 空历史”基线；一旦存在更早 PNG 而 drift/plan 不可用，则 fail closed。

## 5. n2d-review 自身反偏验收

```bash
python3 skills/n2d/n2d-review/scripts/meta_audit.py \
  --root . \
  --evidence skills/n2d/n2d-review/references/external_grounding_2026-07-14.json \
  --run-tests \
  --out <作品根>/生产数据/n2d_review_meta_audit.json \
  --json

python3 skills/n2d/n2d-review/scripts/self_audit.py \
  --root . \
  --evidence skills/n2d/n2d-review/references/external_grounding_2026-07-14.json \
  --run-meta-tests \
  --out <作品根>/生产数据/n2d_review_self_audit.json \
  --json
```

`meta_audit.py` 是 report-only 治理审计，固定以退出码 0 结束；因此不得把“命令成功退出”当作验收通过。验收方必须解析已落档 JSON 的 `assurance` 和 `adversarial_runtime_receipt`，逐项核对状态、覆盖数、当前 guard/test SHA、实际 pytest 状态与错误列表。`self_audit.py` 也必须消费并落档同一轮 meta 证据；其退出码只负责已有 `block`，不能替代对上述 assurance/receipt 的结构化校验。

代码交付最低标准：

- `self-checked=complete`：声明、实现、调用三段可追溯。
- `adversarial-test-coverage=complete`：登记的 guard、回归和反例静态齐全。
- `adversarially-tested=complete`：本次真实 pytest 收据通过，并绑定当前 guard/test SHA；只扫描到测试文本不算。
- `externally-grounded=complete`：仅表示当前登记的 `external_required` claims 已有有效外部来源、日期、置信度和实现映射；当前 `4/4` 或其他 `N/N` 不代表整个 n2d-review 已获外部验证。
- 没有真正独立留出实验时，必须如实保留 `externally-calibrated=not_run`。这不阻止代码交付，但禁止宣称“无偏、无盲区、已达普适行业标准”。

若要把 `externally-calibrated` 升为 complete，至少准备四类当前仓库 artifact：预注册 protocol、锁定 sample manifest、gate predictions、独立 ground truth；再由与实现和选样均独立的审阅者在 blind held-out 分层样本上评测，机器复算 confusion matrix、FNR/FPR 并按预声明阈值判定。若还要声称审阅者的真实身份或组织独立性已获认证，必须另附外部认证 ID、签名或审批系统收据；仅在 JSON 里填写 `reviewer_id/independent=true` 仍是合同声明，不是身份认证。

## 6. 仓库级最终验收

```bash
python3 -m pytest -q skills/n2d/n2d-review/scripts
python3 -m pytest -q skills/n2d/n2d-image/scripts
python3 -m pytest -q skills/n2d/n2d-identity/scripts
python3 -m pytest -q skills/n2d/n2d-script/scripts
python3 -m pytest -q skills/n2d
python3 tools/update_skill_stats.py
python3 tools/validate_skills.py
python3 tools/independence-audit/scripts/check_independence.py
```

任何测试失败、F7 统计过期或跨线依赖失败都不算完成。可选 golden fixture 不在仓库时只允许显式 skip，不得把“缺 fixture”伪装成通过；交付流程不依赖任何版本控制命令。
