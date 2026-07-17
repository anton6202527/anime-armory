# panel_script.json schema

最小结构：

```json
{
  "schema_version": 1,
  "kind": "comic_panel_script",
  "title": "作品名",
  "chapter": "第1话",
  "status": "draft",
  "chapter_contract": {
    "path": "脚本/split_blueprint.json",
    "chapter_contract_sha256": "本话 chapter contract 规范 JSON 的 SHA256",
    "status": "confirmed"
  },
  "source_semantics": {
    "path": "脚本/第1话/source_semantics.json",
    "requires_normalization": true,
    "source_language": "英文/拉丁字母外语",
    "target_text_language": "中文",
    "target_text_metadata": {"lang": "zh-Hans", "dir": "ltr", "script": "Hans", "line_break": "cjk"},
    "status": "pass"
  },
  "visual_contract": {
    "style_baseline": "本话统一画风、线条、上色、明暗和纹理基线",
    "character_integrity_policy": "含角色格必须锁脸型、眼型/眼距、发际线、发型轮廓、服装主色、标志物和肢体完整性；不得因漫画风格降低脸/手脚/服装一致性标准",
    "scene_anchors": {
      "LOC_001": {
        "spatial_layout": "场景平面关系、入口、主要地标、前后景层级和常驻物件",
        "lighting_anchor": "主光方向、色温/冷暖、动机光源和是否允许剧情改光",
        "axis_eyeline": "主要人物左右站位、默认视线方向、正反打/反应格如何对位",
        "resident_assets": ["常驻道具/招牌/屏风/树/门窗等不可忽隐忽现的物件"],
        "forbidden_drift": ["不能换成别的建筑/时代/室内外", "不能冷暖光随机跳"]
      }
    },
    "character_state_timeline": {
      "CHAR_MAIN": [
        {"from_panel": "P001", "state": "左脸血痕出现后后续保留"}
      ]
    }
  },
  "panels": [
    {
      "panel_id": "P001",
      "story_function": "opening_hook",
      "source_excerpt": "原文摘录或源段落 ID",
      "meaning_zh": "白话/中文释义",
      "text_target": "本格最终可嵌字目标文本",
      "adaptation_note": "压缩、合并、删改、改成画面或改成对白的说明",
      "description": "首格画面描述",
      "characters": ["主角"],
      "character_bindings": [
        {
          "character_id": "CHAR_MAIN",
          "form_id": "FORM_BASE",
          "outfit_id": "OUTFIT_DEFAULT",
          "expression_id": "EXPR_ALERT",
          "state_id": "STATE_CH01_ENTRY"
        }
      ],
      "source_segment_refs": ["S001"],
      "location": "场景名",
      "scene_anchor_id": "LOC_001",
      "spatial_layout": "继承 LOC_001 的空间布局，本格角色在画面左前景，门在右后景",
      "lighting_anchor": "继承 LOC_001：画左上 5600K 冷窗光，画右侧弱暖灯轮廓光",
      "axis_eyeline": "本场轴线为左右对峙；主角画左，视线画右",
      "gaze_target": "对手手中的匕首 / 对话对象 / 画外声源",
      "eyeline_direction": "画右下方",
      "character_integrity": "脸型、眼型、发际线、发型轮廓、服装主色和标志物继承 CHAR_MAIN；头发/脸/手脚完整可读",
      "continuity_from": "P000 或上一格 ID；没有则写 none",
      "spatial_relationships": "人物左右/前后景/遮挡关系和关键接触点",
      "dialogue": [
        {
          "speaker": "主角",
          "text": "向后兼容台词",
          "text_target": "最终嵌字台词",
          "source_text": "可选：对应原文",
          "lang": "zh-Hans",
          "dir": "ltr",
          "tone": "紧张"
        }
      ],
      "narration": "旁白",
      "narration_target": "可选：最终嵌字旁白",
      "sfx": ["轰"],
      "art_notes": "景别、构图、表情、动作、禁漂移项",
      "layout_weight": "heavy",
      "panel_shape": "wide",
      "border_style": "standard",
      "gutter_intent": "翻页前停顿",
      "ink_plan": "清线轮廓、线宽变化、脸和手保持可读",
      "black_fill_plan": "反派背后黑场压迫，但不遮挡五官和关键道具",
      "tone_plan": "背景 20% 网点，衣料 40% 网点，焦点物保留白",
      "value_plan": "三值阅读：脸亮、披风暗、背景中灰",
      "effects_plan": "集中线指向匕首反光，速度线跟随挥刀路径",
      "references": ["CHAR_MAIN", "LOC_001"]
    }
  ]
}
```

字段规则：

- `panel_id`：同一话唯一，推荐 `P001`。
- `chapter_contract`：绑定本话 v2 contract。`chapter_contract_sha256` 与 `source_semantics.json.chapter_contract.sha256` 使用同一规范 JSON 算法；上游合同变化后 panel script 与下游任务必须 stale，重新审阅后才能更新绑定。
- `story_function`：该格的戏剧功能，如 `opening_hook`、`reaction`、`reveal`、`action_peak`、`turning_point`、`cliffhanger`。
- `source_semantics`（可选）：记录本话源语义归一化 gate 的路径和状态；源本是外语、文言/古汉语或混合语言时应存在，且 `status=pass` 后再进入排版/出图。
- `source_excerpt` / `meaning_zh` / `text_target` / `adaptation_note`：跨语种、文言/古汉语或强制归一化改编时的逐格追溯字段。它们让分格衡量从源文长度统一到“源语义 → 中文释义 → 目标嵌字 → 改编取舍”。
- `source_segment_refs`：源本改编的确定性追溯键，引用本话 `source_semantics.json.segments[].segment_id`。凡改编决策不是“删除/后文带出”的源段，都必须至少被一格消费；不存在的 segment ID、无决策源段或无格覆盖会阻断 strict source coverage。
- 改编中新增、确实没有对应源段的衔接格可以不填 `source_segment_refs`，但必须同时写 `adaptation_origin="original_bridge"` 和非空 `adaptation_note`；这是一条显式改编取舍，不能用空引用静默绕过 coverage。
- `character_bindings`：含具名角色格的正式身份绑定。每项必须带 `character_id / form_id / outfit_id / expression_id / state_id`，供出图任务消费角色、形态、服装、表情和当前剧情状态。旧 `characters:["CHAR_x"]` 只保留阅读与迁移兼容，不能代替正式绑定；迁移时按每个 `characters` 项查 identity registry 后补齐五个 ID，未知值不得用自然语言或 `default` 偷渡。
- `description`：画面事实，不写空泛风格词。
- `dialogue`：只存文字，不要求画进图里。`text_target` 优先作为最终嵌字文本；`text` 保留向后兼容；`source_text` 可记录原文。跨语种、RTL 或需词典断行文字应记录 `lang` / `dir`，避免渲染阶段靠错误启发式猜方向。
- `narration_target` / `sfx_target`（可选）：当目标嵌字语言不同于源文本或默认正文时，用于保留最终可渲染文本。
- `art_notes`：给排版和出图用，包含景别、构图、表情、动作、需要参考的资产。
- `references`：角色、场景、道具、服装、特效等引用 ID；MVP 可先留自然语言，正式出图前再规范。凡画面描述（description/art_notes/location）提到 registry 已登记实体（含别名 `assets[*].aliases`）而本格未绑定，`entity_presence_audit` 会出 warn——出图不附参考=形态裸奔（2026-07-17 虎妖/断横刀漂移实证）。
- `entity_schedule`（可选·渐进采用·参照同仓视频线 storyboard 同名字段）：逐格实体在场契约 `{"required_presence": ["MON_x", "PROP_y"], "offscreen_presence": [], "forbidden_presence": []}`。写了就受 `entity_presence_audit` 校验：必在实体必须出现在 characters/references 绑定集、必在与禁入不得冲突、禁入实体不得被绑定。未写的格审计会在报告 `derived_schedule` 给出由绑定集派生的底稿。
- `visual_contract`（正式出图前必填）：本话像素层一致性真值。至少包含 `style_baseline`、`character_integrity_policy` 和 `scene_anchors`；场景锚按 `LOC_` 管 `spatial_layout / lighting_anchor / axis_eyeline / resident_assets / forbidden_drift`。缺失时 `comic-review gate --stage image_preflight` 阻断。
- `scene_anchor_id` / `spatial_layout` / `lighting_anchor` / `axis_eyeline`：含场景格必填；可逐格写，也可用 `scene_anchor_id` 继承 `visual_contract.scene_anchors`。`scene_anchor_id` 必须在顶层 `visual_contract.scene_anchors` 登记，同一场景跨格不得随机换布局、主光方向、冷暖光、常驻物件或人物左右关系。
- `gaze_target` / `eyeline_direction`：含角色格必填。眼神必须锁定对话对象、对手、道具、命中点、画外声源或下一动作目标；不能只写“坚定眼神/看前方/远方”。除非明确写 `camera_role=POV/破第四墙`，不得默认看读者镜头。
- `character_integrity` / `completeness_notes`：含角色格必填。说明本格如何保持脸型、眼型/眼距、发际线、发型轮廓、服装主色、配饰/伤痕/标志物和身体完整性；动作格还要写清手脚归属、接触点和不可裁掉的部位。只写“保持人物完整”不够。
- `continuity_from` / `spatial_relationships`：推荐必填；多人同格时必须写。前者说明承接哪一格的状态、伤痕、道具或站位；后者锁人物左右、前后景、遮挡和关键接触点，减少跨格空间漂移。
- `layout_weight` / `visual_weight` / `importance`（可选）：`heavy` / `medium` / `compact` 或 1-3，用于让 `comic-layout` 以数据驱动方式决定大格/中格/小格，避免把具体项目 story_function 写进通用脚本。
- `panel_shape` / `border_style` / `gutter_intent`（可选）：缩略分镜/name board 层使用。`panel_shape` 可写 `wide`、`tall`、`small`、`full_width`、`borderless` 等；`gutter_intent` 写本格前后的停顿、快切、翻页钩子或呼吸。
- `ink_plan` / `black_fill_plan` / `tone_plan` / `value_plan` / `effects_plan`（可选）：传统原稿收尾计划。`comic-finishing` 会优先继承这些字段，缺失时按风格和叙事功能生成默认计划。黑白页漫和日漫网点风格建议显式写 `tone_plan`；动作、冲击、揭示格建议显式写 `effects_plan`。
- `style_bucket` / `scene_family` / `visual_context`（可选）：同一场景/光色族群标识，供 `comic-review` 的风格一致性按计划内场景分组，避免把夜景、梦境、蒙太奇、系统光效等合理差异误判成画风漂移。

## 一致性底线

- 漫画一致性底线：角色脸、眼神目标、身体完整性、场景布局、光位/冷暖、轴线视线和常驻道具都必须在出图前写成可审字段。
- 角色 reference 负责“同一张脸和同一套造型”，分格脚本负责“这一格怎么演、看哪里、站在哪里、光从哪里来”。不要把所有压力推给 prompt。
- 同一场景多格可以有景别变化、构图变化和情绪变化，但不能无理由换地点结构、换主光方向、换人物左右关系或让常驻物件忽隐忽现。
- 视觉契约必须具体到可执行对象：眼神写“看匕首反光/看画右的对手/看画外声源”，场景写 `LOC_` 锚和光位，人物完整性同时覆盖脸/眼/发与手脚/关键道具。
