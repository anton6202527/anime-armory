# Semantic Vibe Morphing (语境与文风渐变曲线)

长篇小说的文风不应是从头到尾一条直线的。
优秀的网文懂得在不同 Arc（故事篇章）之间做**文风渐变（Tone Morphing）**。

## 概念：Tone Curve (文风曲线)

系统不再只比较一个固定的 `风格指纹.json`，而是允许配置 `tone_curve.json`，将章段映射到不同的情感基调：

```json
{
  "arcs": [
    {
      "range": "1-50",
      "arc_name": "初入江湖",
      "target_vibe": "Light, comedic, fast-paced (轻喜剧，快节奏，少年感)",
      "anchor_file": "设定/风格指纹_轻松.json"
    },
    {
      "range": "51-120",
      "arc_name": "家族覆灭",
      "target_vibe": "Gritty, oppressive, sensory-heavy (压抑，沉重，多感官心理描写)",
      "anchor_file": "设定/风格指纹_沉重.json"
    }
  ]
}
```

## 落地机制
1. **Ghostwriter 注入**：`draft_packets.py` 在生成任务包时，会根据当前章节号匹配 Tone Curve，注入当期的 `target_vibe` 提示。
2. **Review 漂移检测**：`extract_style.py` 会动态拉取属于当前章节区间的 `anchor_file` 进行相似度比对。如果第 60 章写得像前 50 章一样轻松搞笑，系统会报 `🔴 建议级：文风与当前 Arc 曲线不符`。
