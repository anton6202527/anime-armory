# finishing_plan.json schema

`finishing_plan.json` 记录传统漫画完成稿层的计划，供 `comic-image` 生成 prompt、供 `comic-compose` 处理拟声词、供 `comic-review` 做流程审查。

最小结构：

```json
{
  "schema_version": 1,
  "kind": "comic_finishing_plan",
  "chapter": "第1话",
  "render_stage": "网点完成稿",
  "style": "黑白日漫页漫",
  "panels": [
    {
      "panel_id": "P001",
      "art_stage_sequence": ["rough", "pencil", "lineart", "ink_blacks", "tone", "effects", "lettering_sfx"],
      "ink_plan": "clean contour, expressive line weight, keep face and hands readable",
      "black_fill_plan": "solid blacks behind the antagonist to frame the reveal",
      "tone_plan": "skin light tone, robe mid tone, background 20 percent tone, focal object left white",
      "value_plan": "three-value read: face light, cloak dark, background mid",
      "effects_plan": "focus lines toward the dagger reflection",
      "lettering_sfx_plan": {
        "mode": "drawn_sfx",
        "integration": "behind character silhouette, not covering face or hands",
        "shape": "jagged impact"
      },
      "no_bake_text_contract": "dialogue/narration stay out of raw image; SFX may be drawn only if listed here"
    }
  ]
}
```

字段规则：

- `render_stage`：来自 `_设置.md` 的 `出图稿层`，如 `完成稿`、`清线稿`、`墨线+黑场`、`网点完成稿`、`彩色完成稿`。
- `art_stage_sequence`：传统稿层顺序；即使 AI 一步出图，也要让 prompt 明确最终应像哪一层。
- `ink_plan`：线条、轮廓、线宽、脸/手/道具可读性。
- `black_fill_plan`：黑场和负形，不等于简单加暗角。
- `tone_plan`：网点、灰阶、材质和空间深度；彩色项目可写“价值层/灰阶预案”。
- `effects_plan`：速度线、集中线、冲击线、闪光、漫符、背景省略等。
- `lettering_sfx_plan`：拟声词是否作为绘制元素进入画面。对白和旁白仍必须后期嵌字。
- `no_bake_text_contract`：明确禁止正文文字、空白气泡、旁白框、UI 字、乱码字、水印烘焙进原图。
