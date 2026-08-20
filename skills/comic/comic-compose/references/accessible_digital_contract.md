# accessible digital / EPUB FXL readiness 合同

comic 当前**没有自动 EPUB renderer**。`epub_fxl` 只提供可选的交付验收轴：外部专业工具生成真实 `.epub` 后，把它登记进 `export_manifest.json.documents[]`，再写 `排版/<话>/accessible_digital_contract.json`。普通 PNG/WebP/PDF 图片包不能冒充 EPUB 或 accessible digital。

裁决会用标准库验证 `mimetype` 是 ZIP 首项且未压缩、container rootfile 指向真实 OPF、manifest/spine/nav/XHTML、实际 `rendition:layout=pre-paginated`、包内 accessibility metadata，以及每个 XHTML `img` 是否显式带 `alt` 属性。它不会判断 `alt=""` 是否真为装饰图、替代文本是否准确充分，也不做辅助技术实测。因此结论只能是：

```json
"assurance": {
  "level": "workflow_readiness_human_attested",
  "not_conformance_certification": true
}
```

不能宣称已通过 EPUB Accessibility/WCAG 认证。合同的标准 provenance 必须写：

```json
"provenance": {
  "standard": "EPUB Accessibility 1.1",
  "url": "https://www.w3.org/TR/epub-a11y-11/"
}
```

最小 readiness 字段：

```json
{
  "schema_version": 1,
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
  "navigation": {"toc": true, "landmarks": ["bodymatter"]},
  "accessibility_metadata": {
    "title": "作品名 第1话",
    "language": "zh-Hans",
    "access_modes": ["visual", "textual"],
    "access_mode_sufficient": [["textual"], ["visual", "textual"]],
    "accessibility_features": ["alternativeText", "readingOrder"],
    "accessibility_hazards": ["none"],
    "accessibility_summary": "逐页图像含经人工复核的文本替代。"
  },
  "provenance": {
    "standard": "EPUB Accessibility 1.1",
    "url": "https://www.w3.org/TR/epub-a11y-11/"
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
