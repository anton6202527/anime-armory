# panel_jobs.json schema

最小结构：

```json
{
  "schema_version": 2,
  "kind": "comic_panel_jobs",
  "chapter": "第1话",
  "model": "自定义",
  "channel": "manual",
  "backend_capabilities": {
    "adapter_id": "manual_or_unknown",
    "reference_image_limit": 6,
    "supports_image_inputs": true,
    "persistent_subject": false
  },
  "text_language": "中文",
  "render_stage": "网点完成稿",
  "finishing_plan": "出图/第1话/finishing/finishing_plan.json",
  "reference_plan": {
    "path": "生产数据/comic_reference_plan_第1话.json",
    "plan_sha256": "64位sha256",
    "inputs_fingerprint": "64位sha256"
  },
  "jobs": [
    {
      "panel_id": "P001",
      "status": "planned",
      "size": {"width": 1440, "height": 900},
      "production_contract_prompt": "含参考ID、角色DNA、场景锚、传统稿层与禁继承的完整生产合同",
      "production_negative_contract": "完整负向/合规/禁继承合同",
      "prompt_source_kind": "compiled_submit_prompt",
      "prompt_compiler": {
        "kind": "comic_compiled_image_prompt",
        "version": 1,
        "profile_version": "2026-07-10.1",
        "profile": "gpt_image_comic_natural",
        "backend": "gpt_image",
        "language": "zh"
      },
      "submit_prompt": "只含可见画面、构图、画风稿层、连续性、最短身份保持、收尾技法、无字策略和人体接触点",
      "prompt": "与 submit_prompt 完全相同的兼容别名",
      "negative_prompt": "仅在 profile 支持独立负向字段时填写",
      "source_contract_sha256": "64位sha256",
      "submit_prompt_sha256": "64位sha256",
      "execution_input_sha256": "提交prompt+画布+真实参考SHA+角色绑定+panel plan 的64位sha256",
      "consumed_contracts": {
        "reference_plan": {
          "plan_sha256": "64位sha256",
          "inputs_fingerprint": "64位sha256",
          "panel_plan_sha256": "64位sha256"
        },
        "identity_registry": {"schema_version": 2, "sha256": "64位sha256"},
        "panel_script": {"sha256": "64位sha256"},
        "layout": {"sha256": "64位sha256"}
      },
      "character_bindings": [{
        "character_id": "CHAR_MAIN",
        "form_id": "FORM_BASE",
        "outfit_id": "OUTFIT_BASE",
        "expression_id": "EXPR_NEUTRAL",
        "state_id": "STATE_BASE",
        "resolved_contracts": {}
      }],
      "continuity_contract": {
        "scene_anchor_id": "LOC_001",
        "spatial_layout": "继承 LOC_001 空间布局",
        "lighting_anchor": "画左上 5600K 冷窗光",
        "axis_eyeline": "左右对峙轴线，主角画左看画右",
        "gaze_target": "对手手中的匕首",
        "eyeline_direction": "画右下方",
        "character_integrity": "脸型/眼型/发际线/服装主色/标志物和肢体完整性继承 CHAR_MAIN",
        "continuity_from": "P000"
      },
      "traditional_finish_contract": {
        "ink_plan": "clean contour and readable hands",
        "black_fill_plan": "solid blacks behind antagonist",
        "tone_plan": "20 percent background screentone",
        "effects_plan": "focus lines toward reveal object",
        "no_bake_text_contract": "dialogue and narration stay out of raw images"
      },
      "reference_budget": {
        "adapter_id": "manual_or_unknown",
        "reference_image_limit": 6
      },
      "references": [
        {"id": "CHAR_MAIN", "path": "出图/共享/图片/CHAR_MAIN_front.png", "role": "front", "sha256": "64位sha256", "required": true}
      ],
      "result_path": "",
      "source": "manual",
      "reference_input_mode": "codex_exec_image_flags",
      "reference_input_count": 1,
      "reference_manifest": "生产数据/codex_reference_bundles/第1话/P001.json"
    }
  ]
}
```

正式状态语义：

- `planned`：任务已写，未执行。
- `submitted`：已交给某个后端或人工流程。
- `awaiting_review`：机器 QC 为 pass，但当前像素尚未具名人审。
- `qc_warn`：机器只发现启发式 warning，尚未具名签收；不算 ready。
- `qc_block`：确定性缺件/损坏/引用覆盖/分辨率血统或 unverifiable；永不可人工豁免。
- `ready`：图片已落到 `result_path`，且具名人审为 `accepted` 或 `accepted_with_warnings`；验收同时绑定当前 artifact SHA、on-disk/job post-QC、机器 findings SHA、contact sheet SHA、comparison packet fingerprint 与每个比较输入 SHA。
- `rework`：需要重出。

`warn` 不能自动变 `ready`，但审核人实际查看当前 contact sheet 后，可以用明确理由签为 `accepted_with_warnings`，receipt 必须记录 warning codes。`skipped`、legacy 无 SHA 签收和 `unverifiable` 都不能授权正式状态。像素、post-QC、contact sheet 或任一比较输入变化时，旧签收立即 stale；重建 job 也不得保留该 `ready`。

正文台词不要写进 `submit_prompt`。`text_language` 只记录后期嵌字/导出的文字语言；台词只作为低细节嵌字区和表演语气的上游依据。

## 完整合同与提交 prompt 的边界

- `production_contract_prompt` / `production_negative_contract`：人和 gate 使用，必须完整；可以含内部 ID、reference 路径、角色 DNA、场景锚、continuity、禁继承、传统稿层和审计说明。
- `submit_prompt`：`skills/comic/_lib/comic_image_prompt_compiler.py` 的唯一模型输入。静态图比视频 prompt 需要更多构图/画风/稿层信息，但仍不得含内部 ID、路径、registry 全文、精确对白或后期流程说明。
- 安全呈现改写属于编译步骤：必须先转为非写实、非伤害细节的可画措辞，再落 `submit_prompt_sha256`；runner 只包裹和提交，不得让实际发送内容脱离已记录哈希。
- `prompt`：为旧 runner/人工流程保留的兼容键，schema v2 中必须与 `submit_prompt` 完全相同；不得重新塞回完整合同。
- `references` / `reference_budget`：属于请求控制层；runner 真实附图，模型 prompt 只写参考角色作用，不写本地路径。
- `comic-review gate --stage image_preflight` 会校验 schema、compiler kind/version、backend/profile、合同 hash、提交 hash 和 lint；`codex_panel_runner.py` 在调用前再验一次。

注意：`references[].path` 表示 job 已绑定共享参考图；`reference_input_count` 和 `reference_manifest` 表示生成时已经把这些参考图真实传给后端。已有面板如果只有 path、没有 manifest 或 `reference_input_count=0`，应由 `comic-identity` 标入重抽计划。

`backend_capabilities` / `reference_budget` 来自 comic 自己的 `image_backend_adapter`，用于记录当前模型+渠道的参考图预算、是否支持真实图片输入、是否具备持久主体能力。它是 job 生成时的执行约束，不代表本机一定已安装对应 runner。

`character_bindings` 是具名角色逐格身份与状态真值。`characters` 只可作人读/检索列表，裸名字不能解析为资产，单独出现 `CHAR_` 也不能代替 binding。每个 binding 的四个子 ID 必须存在于 identity registry v2，且 `state_id` 声明的 form/outfit/expression 必须与本格绑定一致。

`reference_plan` 与 `consumed_contracts` 证明 job 消费的是当前处方，不是另行随意挑图。处方先给每个具名角色至少一个真实身份锚，再保留 `LOC_` 与常驻 `PROP_`；关键引用超过执行后端真实附件上限时必须拆格/分区合成，不能静默省略。任何输入、计划或已选参考内容变化都会使对应 hash 失效。

`continuity_contract` 来自 `panel_script.json` 的逐格字段和顶层 `visual_contract`。它是出图 job 的像素层约束，至少应覆盖：

- `scene_anchor_id / spatial_layout / lighting_anchor / axis_eyeline`：同场景布局、光位、冷暖和人物左右关系不能跨格随机漂移；`scene_anchor_id` 必须登记在顶层 `visual_contract.scene_anchors`。
- `gaze_target / eyeline_direction`：角色眼神锁具体戏内目标；除明确 POV/破第四墙外，不看读者镜头，也不能只写“坚定眼神/看前方/远方”。
- `character_integrity`：脸、眼型/眼距、发际线、发型、服装、标志物、手脚和关键道具完整可读；只写“保持人物完整”不够。
- `continuity_from / spatial_relationships`：承接上一格的站位、伤痕、道具状态、接触点和前后景遮挡关系；多人同格必须写清左右、前后景、遮挡和关键接触点。

缺这些字段时，`comic-review gate --stage image_preflight` 会在付费/批量出图前阻断，要求回 `comic-script` 补视觉契约后重建 job 包。

`traditional_finish_contract` 来自 `出图/第N话/finishing/finishing_plan.json`。它不替代视觉一致性契约，而是把传统漫画完成稿手法注入 prompt：

- `art_stage_sequence` / `render_stage`：目标稿层，如清线稿、墨线+黑场、网点完成稿、彩色完成稿。
- `ink_plan` / `black_fill_plan`：线条、轮廓、线宽、黑场、负形和焦点层级。
- `tone_plan` / `value_plan`：网点、灰阶、材质、空间深度和黑白灰可读性。
- `effects_plan`：速度线、集中线、冲击线、闪光、漫符、背景省略。
- `lettering_sfx_plan`：拟声词是否作为画面元素绘制；对白和旁白仍后期嵌字。
- `no_bake_text_contract`：禁止正文、空白气泡、旁白框、UI 字、乱码字、水印烘焙进原图。

启用传统原稿流程但缺该字段时，`comic-review gate --stage image_preflight` 给 warn，建议先跑 `comic-finishing` 并重建出图包。

## 镜头语言参考

`skills/comic/references/运镜/manifest.json` 是漫画线可用的镜头语言参考库。漫画不直接播放运镜，出图任务中应把它转译为静态画面约束：

- `推镜头` → 更近景别、更大主体占比、焦点压到脸/手/道具。
- `拉镜头` → 更大环境关系、孤独/余韵/处境暴露。
- `甩镜` / `冲击变焦` → 斜切格、速度线、冲击线、动势模糊，但不要牺牲人物完整性。
- `焦点转移` / `前景遮挡揭示` → 前后景虚实、遮挡边缘、视线引导。
- `顶视俯拍` / `无人机航拍` → 大格定场、阵法几何、路线和群像站位。

写 `prompt`、`art_notes` 或 `traditional_finish_contract.effects_plan` 时可引用这些结构化词，但最终必须落成可画的构图、线条和层次，不要只写“炫酷运镜”。
