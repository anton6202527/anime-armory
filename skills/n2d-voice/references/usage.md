# 调用规范
源 env(可选): source <作品根>/出视频/.minimax_env
逐句生成 + 整轨 + 时长清单：
    python3 <skill>/render_voice.py <作品根> 第N集 zh
    python3 <skill>/render_voice.py <作品根> 第N集 en   # 出海配音(英文)
产物：<作品根>/出视频/第N集/配音/{line_NN.wav, voice_zh.wav, voice_en.wav, 时长清单.json}

## 进度回写
完成后回写「配音」列：`python3 <novel2drama skill>/progress.py set <作品根> 第N集 配音 ✅`（别手工编辑进度表，易改错列）。

## 完成消息（驱动下一阶段）
配音完成后提示助手：「配音齐 → 下一步 /n2d-script <作品根> 第N集 用时长清单定稿故事板+SRT，再 /n2d-image」。
