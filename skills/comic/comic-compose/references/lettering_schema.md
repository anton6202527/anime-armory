# lettering.json schema v2

`lettering.json` 是从当前脚本、layout、finishing 与翻译表派生的版本化产物，不是可脱离上游自由改写的文本副本。正式结构：

```json
{
  "schema_version": 2,
  "kind": "comic_lettering",
  "chapter": "第1话",
  "language_mode": "中上英下",
  "source_bindings": {
    "panel_script": {"path": "脚本/第1话/panel_script.json", "exists": true, "sha256": "<current-file-sha256>"},
    "layout": {"path": "排版/第1话/layout.json", "exists": true, "sha256": "<current-file-sha256>"},
    "finishing_plan": {"path": "出图/第1话/finishing/finishing_plan.json", "exists": true, "sha256": "<current-file-sha256>"},
    "translation_map": {"path": "排版/第1话/lettering_translations.json", "exists": true, "sha256": "<current-file-sha256>"}
  },
  "translation_usage": {
    "content_ref_count": 1,
    "legacy_text_key_count": 0,
    "legacy_content_refs": [],
    "unbound_content_ref_count": 0,
    "unbound_content_refs": [],
    "stale_content_ref_count": 0,
    "stale_content_refs": [],
    "invalid_content_ref_count": 0,
    "invalid_content_refs": []
  },
  "items": [
    {
      "item_id": "L001",
      "content_ref": "panel:P001.dialogue:1",
      "panel_id": "P001",
      "type": "dialogue",
      "speaker": "主角",
      "source_text": "台词",
      "source_text_sha256": "<sha256-of-exact-source_text>",
      "text": "台词",
      "text_zh": "台词",
      "text_en": "Dialogue.",
      "text_source": "可选：原文或文言摘录",
      "translation_binding": {
        "key": "panel:P001.dialogue:1",
        "resolution": "content_ref_sha256",
        "source_text_sha256": "<sha256-of-exact-source_text>"
      },
      "lang": "zh-Hans",
      "dir": "ltr",
      "script": "Hans",
      "line_break": "cjk",
      "slot_id": "B001",
      "style": {"font": "project_default", "size": 44, "direction": "horizontal", "bubble": "round"}
    }
  ]
}
```

## 输入与逐条版本合同

- `source_bindings` 必须始终包含 `panel_script`、`layout`、`finishing_plan`、`translation_map` 四项的路径、存在状态和当前 SHA。可选文件缺失时也记录权威路径、`exists=false`、`sha256=""`；之后文件被创建同样会让旧 lettering 失效。
- 每个对白、旁白和 SFX 都必须有稳定 `content_ref`：旁白为 `panel:P001.narration`，对白为 `panel:P001.dialogue:1`，拟声词为 `panel:P001.sfx:1`。序号取脚本原数组位置，空的中间项不会让后续 layout 槽位错绑。
- `source_text` 是本次嵌字实际消费的当前目标文字（优先 `text_target` 等目标字段），`source_text_sha256` 是其精确 UTF-8 SHA-256；两者不是 `text_source`。后者只保存外语、古文或来源摘录，供编辑追溯。
- 脚本、layout、finishing、翻译表或逐条源文字变化后，旧 `lettering.json` 必须重建。只重跑 gate 不会刷新它；`lettering_contract.py` 会确定性阻断旧绑定。
- `export_manifest.json.lettering_sha256` 必须等于当前 `lettering.json` SHA；重建 lettering 后还须重新渲染，旧图片/PDF 不能重新签收。

## 翻译表合同

新翻译表以 `content_ref` 为 key，因此相同中文在不同说话人、语气或上下文中可以有不同译文：

```json
{
  "translations": {
    "panel:P001.dialogue:1": {
      "text_en": "Let's go.",
      "source_text_sha256": "<sha256-of-dialogue-1-current-source>"
    },
    "panel:P001.dialogue:2": {
      "text_en": "Move. Now.",
      "source_text_sha256": "<sha256-of-dialogue-2-current-source>"
    }
  }
}
```

解析顺序固定为：SHA-bound `content_ref` 对象 → 旧中文原文 key。`content_ref` 是位置/上下文主键，但位置不证明原句没变，因此只有对象里的 `source_text_sha256` 等于当前 item 源 SHA 时才应用译文；脚本在同一 `content_ref` 改词后，旧结构化译文标 `content_ref_stale`、不应用并 block 等待重译。旧 `content_ref: "English"` 字符串缺源 SHA，标 `content_ref_unbound`、不应用并 warn。旧中文原文 key 仍能读取，因为 key 本身须等于当前原句，但 item 会记录 `legacy_text_key` 并 warn；它无法为重复原文表达不同上下文。

英文/双语缺译文时，`lettering_translations.todo.json` 的每个任务会携带 `content_ref`、`source_text` 和 `source_text_sha256`。译者按 `content_ref` 回填翻译表，再重跑 `build_lettering.py`。

## 人工改写合同

不得直接改 `text` / `text_zh` / `text_en` / `text_custom` 造成静默分叉。确需编辑改写时，在同一 item 写 SHA-bound `editorial_override`：

```json
{
  "editorial_override": {
    "content_ref": "panel:P001.dialogue:1",
    "source_text_sha256": "<current-source_text-sha256>",
    "replacement": {"text": "现在出发。", "text_zh": "现在出发。"},
    "reason": "口语节奏优化",
    "reviewed_by": "责任编辑",
    "reviewed_at": "2026-08-20T10:00:00+08:00"
  }
}
```

`editorial_override.content_ref` 与 `source_text_sha256` 必须同时匹配当前 item，避免相同原文的改写收据被挪到另一个说话人/上下文。`replacement` 只允许 `text`、`text_zh`、`text_en`、`text_custom`。`build_lettering.py` 会从上一版按同一 `content_ref` 保留 override：当前源 SHA 一致时应用；源文字变化后保留为 stale finding，必须基于新源文字重新审批或删除，不能静默继承旧改写。

## 文字与样式字段

- `dialogue` 是对白气泡，`narration` 是旁白框，`sfx` 是拟声词；未来 `system` 文字也应使用同一逐条合同。
- `text` 保持向后兼容；`text_zh`、`text_en`、`text_custom` 是对应语言的最终渲染文本。`文字语言=中文` 时只渲中文，`英文` 只渲英文，`中上英下` / `英上中下` 按指定顺序渲染双语。
- `lang` / `dir` / `script` / `line_break` 是语言、方向和断行元数据。RTL 或 `line_break=dictionary_required` 不得由 Pillow 草稿 renderer 静默渲染。
- 空目标字符串不生成 item 或最终气泡；导出脚本也会跳过无文字 item 和未使用的 `bubble_slots`。
- `dialogue` / `narration` 容器由 comic-compose 绘制；不要在图像阶段烘焙空白气泡。
- `sfx` 可从 `finishing_plan.json` 继承 `style.drawn_lettering_mode`、`integration`、`shape`。对白、旁白和系统正文仍必须后期嵌字。
- 正式发布前必须确认字体授权；系统字体只能标为草稿状态。
