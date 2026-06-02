# 调用规范
源 env(可选): source <作品根>/出视频/.minimax_env
逐句生成 + 整轨 + 时长清单：
    python3 <skill>/render_voice.py <作品根> 第N集 zh
    python3 <skill>/render_voice.py <作品根> 第N集 en   # 出海配音(英文)
产物：<作品根>/出视频/第N集/配音/{line_NN.wav, voice_zh.wav, voice_en.wav, 时长清单.json}

## 进度回写
完成后把 <作品根>/common/_进度.md 该集「配音」列改 ✅（列若不存在，首次跑时在表头「草稿故事板」后插入「配音」列）。

## 完成消息（驱动下一阶段）
配音完成后提示助手：「配音齐 → 下一步 /n2d-script <作品根> 第N集 用时长清单定稿故事板+SRT，再 /n2d-image」。
