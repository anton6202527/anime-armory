# 专业文字 renderer 与字体覆盖

`skills/comic/_lib/text_renderer_adapter.py` 把三件事分开记录：

1. renderer 声明支持哪些能力；
2. 当前语言/方向/书写模式需要哪些能力；
3. 当前文字是否真的由该 renderer 渲染，并且字体是否含所需 glyph。

Pillow 只允许作为安全的横排 CJK/Latin 草稿 fallback；它不能声明 RTL、复杂 shaping、CJK 竖排或正式出版能力。系统同时存在 `pango-view + hb-shape` 时，可处理横排复杂 shaping；竖排仍需显式 `vertical_cjk` adapter。

项目可在 `生产数据/text_renderer_adapters.json` 注册专业 renderer：

```json
{
  "adapters": [{
    "id": "studio-typesetter",
    "protocol": "comic_text_rgba_v1",
    "command": ["/absolute/path/to/renderer", "--request", "{request}", "--output", "{output}"],
    "supports": [
      "cjk_horizontal",
      "latin_horizontal",
      "complex_shaping",
      "rtl",
      "vertical_cjk",
      "font_fallback"
    ]
  }]
}
```

命令收到 JSON request，必须写真实 PNG。调用方验证图片可解码、尺寸、mode 与输出 SHA 后写 `comic_text_render_receipt`；失败或缺能力时不能静默回落成正式成品。注册命令按 argv 执行，不经过 shell。

`validate_glyph_coverage()` 使用当前字体文件和 HarfBuzz 真实 shaping，`gid=0` 视为缺 glyph；收据绑定 text SHA 与 font SHA。字体文件或 `hb-shape` 不可用时状态为 `unavailable`，不能把“未检查”写成通过。正式发布应同时保存 renderer selection、render receipt 和 glyph coverage receipt。
