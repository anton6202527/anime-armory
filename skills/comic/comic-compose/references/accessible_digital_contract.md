# accessible digital / EPUB FXL readiness 合同

comic 现在可由 `scripts/build_epub_fxl.py` 生成真实 EPUB 3 fixed-layout 并登记 `export_manifest.json.documents[]`；也接受外部专业工具生成的 EPUB。普通 PNG/WebP/PDF 图片包不能冒充 EPUB 或 accessible digital。

```bash
python3 skills/comic/comic-compose/scripts/build_epub_fxl.py "$ROOT" --chapter 第1话 \
  --alt-json page_alts.json --reviewer "无障碍编辑" --reason "逐页对照实际画面复核"
```

脚本会把 `mimetype` 作为未压缩 ZIP 首项，生成 container、OPF、spine、nav、逐页 XHTML/alt 和 discoverability metadata，并从 layout 写入真实 `page-progression-direction=ltr|rtl`。EPUB、`accessible_digital_contract.json`、`export_manifest.json` 先在同一 staging 内完成 ZIP CRC、XML、包结构、页图数量和互相 SHA 检查，再以带 flock/WAL/backup/CAS recovery 的组三文件事务提升，manifest 最后切；失败或崩溃保留上一组 active 成品。本机有 `epubcheck` / `ace` 时再执行外部验证，工具缺失会明确记为 unavailable。它不评判替代文本语义质量，也不签发 conformance certification。

`--alt-json` 兼容旧的逐页字符串，也推荐使用结构化语义稿：

```json
{
  "page_001": {
    "alt": "两格漫画：甲发现门外异常，乙回头确认。",
    "long_description": "先是走廊全景，随后切到乙的反应特写。",
    "reading_order": ["P001", "P002"],
    "panels": [
      {
        "panel_id": "P001",
        "description": "甲站在走廊尽头看向门外。",
        "dialogue": [{"speaker": "甲", "text": "外面有人。"}],
        "narration": [],
        "sfx": ["咚"]
      },
      {
        "panel_id": "P002",
        "description": "乙回头。",
        "dialogue": [{"speaker": "乙", "text": "我去看看。"}]
      }
    ]
  }
}
```

`reading_order` 必须恰好覆盖每个 `panel_id` 一次。脚本把分格说明、说话人对白、旁白和 SFX 以可编程 DOM 顺序写进 XHTML，并用 `aria-describedby` 绑定页面图；视觉隐藏只改变呈现，不删除辅助技术可读内容。合同记录整份语义稿 SHA、分格/对白数量、说话人覆盖率和扩展说明数量。

裁决会用标准库验证 `mimetype` 是 ZIP 首项且未压缩、container rootfile 指向真实 OPF、manifest/spine/nav/XHTML、实际 `rendition:layout=pre-paginated`、包内 accessibility metadata，以及每个 XHTML `img` 是否显式带 `alt` 属性。它不会判断 `alt=""` 是否真为装饰图、替代文本是否准确充分，也不做辅助技术实测。因此结论只能是：

```json
"assurance": {
  "level": "workflow_readiness_human_attested",
  "not_conformance_certification": true
}
```

不能宣称已通过 EPUB Accessibility/WCAG 认证。合同以 EPUB Accessibility 1.1 为正式基线，同时仅跟踪 2026 年 EPUB Accessibility 1.2 Candidate Recommendation，不能把候选推荐冒充已发布正式标准：

```json
"provenance": {
  "formal_baseline": {
    "standard": "EPUB Accessibility 1.1",
    "url": "https://www.w3.org/TR/epub-a11y-11/"
  },
  "candidate_tracking": {
    "standard": "EPUB Accessibility 1.2 Candidate Recommendation",
    "url": "https://www.w3.org/TR/2026/CR-epub-a11y-12-20260721/",
    "not_claimed_as_formal_baseline": true
  }
}
```

最小 readiness 字段：

```json
{
  "schema_version": 2,
  "kind": "comic_accessible_digital_contract",
  "chapter": "第1话",
  "artifact": {"path": "排版/第1话/accessible/第1话.epub", "sha256": "..."},
  "rendering": {"rendition_layout": "pre-paginated"},
  "reading_order": ["page_001", "page_002"],
  "text_alternatives": {
    "coverage": 1.0,
    "missing": [],
    "reviewer": "无障碍编辑",
    "reviewed_at": "2026-08-20T00:00:00Z",
    "reason": "逐页核对替代文本与画面语义"
  },
  "semantic_transcript": {
    "sha256": "...",
    "pages": 2,
    "panels": 9,
    "dialogue_lines": 14,
    "speaker_attribution_coverage": 1.0,
    "extended_descriptions": 7,
    "programmatic_order": ["P001", "P002"]
  },
  "navigation": {"toc": true, "landmarks": ["bodymatter"]},
  "accessibility_metadata": {
    "title": "作品名 第1话",
    "language": "zh-Hans",
    "access_modes": ["visual", "textual"],
    "access_mode_sufficient": [["visual", "textual"]],
    "accessibility_features": ["alternativeText", "readingOrder", "longDescription", "structuralNavigation"],
    "accessibility_hazards": ["none"],
    "accessibility_summary": "逐页图像含经人工复核的文本替代。"
  },
  "provenance": {
    "formal_baseline": {"standard": "EPUB Accessibility 1.1", "url": "https://www.w3.org/TR/epub-a11y-11/"},
    "candidate_tracking": {"standard": "EPUB Accessibility 1.2 Candidate Recommendation", "not_claimed_as_formal_baseline": true}
  },
  "assurance": {
    "level": "workflow_readiness_human_attested",
    "not_conformance_certification": true
  }
}
```

`rendering.rendition_layout=pre-paginated` 是本工作流对 `epub_fxl` 的固定版式声明；它仍不能替代对 OPF 中 `rendition:layout` 的独立检查。`text_alternatives` 的 reviewer/reviewed_at/reason 必须具名留痕；机器只证明 `alt` 属性存在，语义质量由该人审负责。`accessMode`、`accessibilityFeature`、`accessibilityHazard` 属 discoverability 必备元数据；`accessModeSufficient`、`accessibilitySummary` 也在本工作流中要求显式填写，避免仅有图片和一句笼统声明。

运行：

```bash
python3 skills/comic/scripts/release_verdict.py "$ROOT" 第1话 \
  --medium epub_fxl --usage public --write --json
```
