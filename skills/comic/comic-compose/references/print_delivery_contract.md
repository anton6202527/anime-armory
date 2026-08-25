# 印刷 PDF 交付合同

`导出格式=pdf` 是真实多页 PDF 产物，不再是 WebP 的别名。当前 renderer 使用 Pillow，把每页文字和画面先扁平为 RGB 像素，再写 `排版/<话>/print/<话>.pdf`，并在 `export_manifest.json.documents[]` 登记 PDF SHA、页数、页序、DPI、逐页源图 SHA/尺寸/mode/alpha 与结构扫描证据。

这只是可续跑的 raster interior PDF，不自动宣称 PDF/X、印厂可收、字体已嵌入、ICC output intent 已嵌入、出血正确或装订正确。封面、书脊和拼版也不在当前自动 renderer 范围内。

## 1. 建印刷规格合同

先实际渲染 PDF，再按印厂要求建立本话合同：

```bash
python3 skills/comic/comic-compose/scripts/export_longstrip.py "$ROOT" \
  --chapter 第1话 --formats pdf --render
python3 skills/comic/comic-compose/scripts/print_delivery.py "$ROOT" --chapter 第1话 init \
  --trim-width-mm 176 --trim-height-mm 250 --bleed-mm 3.2 --safe-mm 6.4 \
  --dpi 300 --reading-direction rtl --binding-edge right \
  --color-mode RGB --icc-policy printer_managed_srgb \
  --icc-profile-name "sRGB IEC61966-2.1" \
  --vendor-profile custom --vendor-requirement-evidence "印厂规格单路径或 URL"
```

合同 `排版/<话>/print_delivery_contract.json` 必须明确：

- `geometry_mm.trim / bleed / safe_area`；每页像素必须等于 `(trim+bleed) × dpi`（允许 2px 舍入差）。
- `dpi >= 300`。
- `page_order`、`binding.edge`、`reading_direction`；`rtl→right`、`ltr→left`。
- `font_handling.mode`：当前 Pillow 路线应为 `rasterized`，结构扫描须证明零 `/Font` object 且逐页有 `/Image`；外部矢量 PDF 走 `embedded` 时必须有嵌入证据。
- `color.mode` 与逐页实际 mode 一致；ICC 只能是 `embedded`（PDF 有 ICC/OutputIntent 证据）或有印厂规格证据的 `printer_managed_srgb/printer_managed_gray`。
- `transparency_policy=flattened`，逐页 `has_alpha=false`。

## 2. 人工印前签收

safe area 是否压到文字/脸/关键道具、单双页与装订是否正确、printer-managed ICC 是否符合印厂口径，不能靠文件存在性自动证明。实际看过当前 PDF 后显式签收：

```bash
python3 skills/comic/comic-compose/scripts/print_delivery.py "$ROOT" --chapter 第1话 accept \
  --reviewer "印前责任编辑" --reason "逐页检查当前 PDF 与印厂规格" \
  --confirm-safe-area --confirm-page-order --confirm-color-icc --confirm-font-handling
```

收据 `生产数据/print_readiness_receipt_<话>.json` 绑定当前合同 SHA、PDF SHA 和 manifest 中 PDF document record SHA。总发布签收还会再次绑定当前印刷合同与该 readiness receipt；换合同并补一张新印前收据后，旧总发布签收不会自动恢复。合同、页图、PDF 或处置声明任一变化，旧收据失效。

最终裁决：

```bash
python3 skills/comic/scripts/release_verdict.py "$ROOT" 第1话 \
  --medium print_pdf --usage public --write --json
```

不能自动证明的任一项缺收据时，`print_pdf` readiness 必须 blocked；不得拿普通 PNG/WebP 包冒充印刷交付。

## 3. KDP vendor profile

`print_delivery.py ... init --vendor-profile kdp` 会固化当前官方约束：内页为单页而非 spread、300dpi、0.125in/3.2mm bleed、无 crop marks、字体至少 7pt、字体嵌入或栅格化、透明度扁平化。gutter 随 trim 与页数变化，合同只记录“必须用当前 KDP calculator/官方表再次确认”，不会编造一个固定 gutter。未传 evidence 时自动记录 [KDP Manuscript Formatting Guide](https://kdp.amazon.com/en_US/help/topic/G201857950) 与核验日 2026-08-25；这仍不代表 KDP 已接收或 PDF/X 合规。
