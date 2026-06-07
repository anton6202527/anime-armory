# 调用规范
源 env(可选): source <作品根>/合成/.minimax_env
逐句生成 + 整轨 + 时长清单：
    python3 <skill>/render_voice.py <作品根> 第N集 zh
    python3 <skill>/render_voice.py <作品根> 第N集 en   # 出海配音(英文)：须先有 字幕_英文.srt（n2d-script 阶段2 产物），故 en 配音在分镜定稿后才跑
产物(zh)：<作品根>/合成/第N集/配音/{line_NN.wav, voice_zh.wav, 时长清单.json}
产物(en)：voice_en.wav（en 不产 时长清单.json——它只由 zh 产出，驱动下游镜头时长）

## ⚠️ macOS say 中文空音频自动降级

如果本机 `say -v Tingting` 中文语音资源未完整下载，可能生成无有效 duration 的空 AIFF。`render_voice.py` 会自动检测这种情况，并生成**静音占位时长轨**：

- `line_NN.wav` / `voice_zh.wav` 仍会生成，但内容是静音；
- `时长清单.json` 每句会标 `占位:true`；
- 配音目录会写 `_占位说明.md`；
- 这只用于 rough timing。**出图前必须换真实配音重跑 n2d-voice，再回跑 n2d-script 阶段2。**

## 进度回写
完成后回写「配音」列：`python3 <novel2drama skill>/progress.py set <作品根> 第N集 配音 ✅`（别手工编辑进度表，易改错列）。

## 完成消息（驱动下一阶段）
配音完成后提示助手：「配音齐 → 下一步 /n2d-script <作品根> 第N集 用时长清单定稿故事板+SRT，再 /n2d-image」。
