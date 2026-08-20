# MV 图片 B14 验收账本契约

权威文件：`<作品根>/生产数据/image_acceptance/image_acceptance.json`。

- `kind`: 固定 `mv_image_acceptance_ledger`
- `schema_version`: 当前为 `1`
- `sequence[]`: 图片首次 preflight 的稳定顺序；直接前驱链据此确定
- `assets`: key 必须是作品根相对图片路径
- `summary`: 最近一次命令计算的缓存，仅供展示；完成态必须实时调用
  `image_receipts.audit_ledger(root, ledger=...)`，不能只相信缓存

每个 `assets[relative_path]`：

```json
{
  "asset_kind": "clip_start|clip_end|shared_costume|shared_location|shared_asset|candidate|cover|other_image",
  "owner": "lead:主唱",
  "use": "Clip_001 首帧",
  "identity_scope": "contains_identity|no_identity",
  "attempts": [],
  "current": {}
}
```

`attempts[]` 保存不可覆盖的重抽历史；`current` 是最后一个 attempt 的同内容视图：

```json
{
  "attempt_id": "attempt-0001",
  "preflight": {
    "status": "ready",
    "planned_asset": "出图/段落/图片/Clip_001.png",
    "model": "GPT Image 2",
    "channel": "Codex",
    "prompt": {"path": "...", "sha256": "..."},
    "planned_references": [
      {
        "path": "出图/共享/图片/定妆_主唱.png",
        "sha256": "...",
        "owner": "lead:主唱",
        "use": "identity_anchor",
        "decodable": true,
        "probe": {"format": "PNG", "width": 2048, "height": 2048}
      }
    ],
    "planned_subject_ids": [],
    "upstream_contract": {
      "clip_id": "Clip_001",
      "expected_prompt": "出图/段落/prompt/Clip_001.md",
      "required_reference_paths": ["出图/共享/图片/定妆_主唱.png"],
      "required_subject_ids": [],
      "carries_identity": true,
      "contract_sha256": "..."
    },
    "previous_acceptance": {
      "asset": "上一图片相对路径",
      "asset_sha256": "...",
      "acceptance_sha256": "..."
    },
    "receipt_sha256": "..."
  },
  "submission": {
    "status": "recorded",
    "attempt_id": "attempt-0001",
    "asset_sha256": "...",
    "asset_decodable": true,
    "model": "GPT Image 2",
    "channel": "Codex",
    "prompt": {"path": "...", "sha256": "..."},
    "actual_references": [
      {"path": "出图/共享/图片/定妆_主唱.png", "sha256": "...", "owner": "lead:主唱", "use": "identity_anchor", "decodable": true}
    ],
    "actual_subject_ids": [],
    "provider_job_id": "img_job_01H...",
    "provider_evidence_required": true,
    "provider_evidence": {
      "path": "生产数据/provider_evidence/Clip_001.json",
      "sha256": "...",
      "kind": "mv_image_provider_evidence",
      "schema_version": 2,
      "source": "api_response_json",
      "adapter_id": "openai_responses_image_v1",
      "attempt_id": "attempt-0001",
      "preflight_sha256": "...",
      "raw_capture": {
        "path": "生产数据/provider_evidence/raw/Clip_001.response.json",
        "sha256": "..."
      },
      "output_selector": 0,
      "provider": "openai",
      "provider_job_id": "img_job_01H...",
      "provider_response_id": "resp_01H...",
      "submitted_at": "2026-08-20T10:15:30+00:00",
      "model": "GPT Image 2",
      "channel": "Codex",
      "asset_sha256": "...",
      "result_status": "completed",
      "provider_output_sha256": "<与当前资产完全相同的 SHA-256>",
      "acceptance_eligible": true,
      "verification_scope": "locally_verified_provider_capture",
      "provider_authenticity": "not_proven_offline"
    },
    "bound_preflight_sha256": "...",
    "receipt_sha256": "..."
  },
  "postflight": {
    "status": "accepted|rejected",
    "asset_sha256": "...",
    "machine_qc": {
      "source_report_path": "生产数据/image_qc/image_qc.json",
      "report_path": "生产数据/image_acceptance/qc_snapshots/<immutable>.json",
      "report_sha256": "...",
      "verdict": "ok|block",
      "precision_level": "full|degraded|none",
      "findings": []
    },
    "visual_review": {
      "reviewer": "审图人",
      "verdict": "pass|reject|unverifiable",
      "notes": "逐图并排目视范围与结论",
      "scope": "current_pixels_side_by_side_with_planned_references_and_previous_accepted_asset"
    },
    "bound_submission_sha256": "...",
    "acceptance_sha256": "..."
  }
}
```

## Provider evidence schema v2

正式 provider 路由不能只填
`provider_job_id`。`record_generation.py` 必须同时收到：

```bash
--provider-job-id "<真实 job/request/task id>" \
--provider-evidence 生产数据/provider_evidence/Clip_001.json
```

证据 manifest 和原始 capture 必须分为两个作品根内文件。provider job ID 至少 6 字符、不得是
`test/fake/dummy/sample/example/unknown/pending/...` 占位。manifest 严格拒绝重复键、未知字段、混合 source
和自带 JSON pointer；provider/channel/精确取值路径/成功终态都来自仓内受信 adapter，不由证据文件自报。

### API response capture（当前内置 OpenAI Responses image adapter）

Manifest：

```json
{
  "kind": "mv_image_provider_evidence",
  "schema_version": 2,
  "source": "api_response_json",
  "adapter_id": "openai_responses_image_v1",
  "attempt_id": "attempt-0001",
  "preflight_sha256": "<当前 preflight receipt_sha256>",
  "raw_capture": {
    "path": "生产数据/provider_evidence/raw/Clip_001.response.json",
    "sha256": "<当前 raw capture SHA-256>"
  },
  "output_selector": 0
}
```

受信 adapter 只从 raw capture 的精确 `/id` 、`/created_at`、`/model`、`/status` 和
`/output/<output_selector>/{type,id,status,result}` 取值；不递归搜索任意嵌套节点。`status` 必须为
`completed`，`output.type` 必须为 `image_generation_call`，`output.id` 必须等于
`--provider-job-id`。`output.result` 的严格 base64 解码字节 SHA-256 必须等于当前图片；
因此不能只在 wrapper 里换一个 `asset_sha256` 就把同一 provider output 绑到另一张图。
时间从 raw `/created_at` 取得，不得早于当前 preflight（仅容许 2 分钟时钟偏差）或晚于当前时间。

### UI 导出（仅可验证的 HAR provider response）

当 UI/浏览器可导出 HAR 网络捕获时，可用：

```json
{
  "kind": "mv_image_provider_evidence",
  "schema_version": 2,
  "source": "ui_export",
  "adapter_id": "openai_responses_image_har_v1",
  "attempt_id": "attempt-0001",
  "preflight_sha256": "<当前 preflight receipt_sha256>",
  "raw_capture": {
    "path": "生产数据/provider_evidence/raw/Clip_001.har",
    "sha256": "<当前 HAR SHA-256>"
  },
  "entry_selector": 0,
  "output_selector": 0
}
```

HAR adapter 要求所选 entry 的 origin 精确为 `https://api.openai.com/v1/responses...`、HTTP 200、
JSON response body，再执行与 API capture 完全相同的 job/time/model/status/output→asset 字节链校验。
截图、PNG/JPEG/PDF、HTML/MHTML/TXT/CSV 里拼六个 token，以及具名 UI 观察，只能当视觉留痕，
不是正式 B14 provider capture，不能使 postflight accepted。其它 provider 必须先按官方响应 schema
新增受信 adapter；unknown/custom adapter 默认阻断，不回退到全文 token 搜索。

### 验证边界与本地路由

离线复验只能证明“项目内 capture 自落盘后未变，且结构/字段/当前资产自洽”，不能证明
provider 确实签发、capture 前没被修改或 provider 时间真实。因此 ledger 明示写入
`verification_scope=locally_verified_provider_capture` 与 `provider_authenticity=not_proven_offline`。
要证明 authenticity，需 provider 签名/JWS+固定公钥，或在线 GET job/审计 API 复核并保存响应。

免 provider evidence 只适用于同时满足：`channel=local|offline|本地|离线` 且 model 显式带
`local:` / `offline:` / `本地:` / `离线:` 前缀。仅把 `GPT Image 2` 的 channel 改成 `local`
仍按正式 provider 路由阻断。

## 不变量

1. `preflight.planned_references` 和 `submission.actual_references` 的
   `(path, sha256)` 集合必须完全一致；actual 继承 planned 的 owner/use，不接受计划外引用。
2. clip 图片先消费当前 `clip_plan + reference_plan` 的逐 clip contract；prompt、必需引用、subject 或合同 hash
   不一致会阻断/使旧验收失效。`contains_identity` 至少一个当前可解码同源图片引用；文字占位、会话隐含参考、不可读文件不算。
3. 新图片的 preflight 必须绑定序列直接前驱的当前有效 acceptance。旧图片重抽会让所有下游前驱链失效。
4. 正式 provider submission 必须把非占位 job ID 与 schema v2 manifest、独立 raw capture 成对提交；
   adapter/attempt/preflight/job/time/model/channel/result status/output bytes/当前资产任一缺失、冲突或改变，
   submission/QC/旧 acceptance 立即失效。
5. postflight 只在当前像素等于 submission、机器结果 `full + ok`、当前引用/prompt/provider evidence 未变且具名目视
   `pass` 时写 `accepted`；其它结果写 `rejected` 并退出非零。
6. accepted/rejected postflight 不得覆盖；修复或重抽必须新建 attempt，旧结论保留在 `attempts[]`。
7. QC 聚合报告会逐图刷新，因此 postflight 复制不可变 per-attempt snapshot；后续图片 QC 不会误使前图失效。
8. `summary.all_current_accepted` 不是自验证事实。阶段完成必须实时扫描 clip 计划和 `出图/**`，并重验
   asset/prompt/reference/provider evidence/QC snapshot/previous acceptance 的当前 hash。
9. `(adapter_id, provider_job_id, output_selector)` 在全 ledger 唯一；同 job 多图只允许不同 selector，
   证据不得跨 attempt 复用。同 attempt 的 submission 仅允许完全幂等重放，任何差异都须新建 preflight。
10. `production_events.jsonl` 只是 ledger submission 的投影；image_qc 要求 asset/model/channel/prompt/
    references/subjects/provider 字段与当前 ledger 精确一致。缺 ledger 或只复制三个 B14 hash 均阻断。
