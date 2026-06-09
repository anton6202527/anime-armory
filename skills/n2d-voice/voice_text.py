#!/usr/bin/env python3
"""配音念白文本清洗——从 render_voice.py 抽出，供其 import + 单测（render_voice 本体在导入时
即跑主流程，不可安全 import，故把纯文本逻辑独立到这里）。

`clean_text` 负责把 voiceover.txt 的一行台词清成「真正要念/要进 时长清单.json 文本 与字幕」的文本：
钩子 emoji(⚡💥🪝)/行尾裸词钩子 去掉、气口标记 `||` 变逗号且不残留 `。，`/`，，`/行首逗号/逗后空格。
这条历史上漏过 → 时长清单与字幕出现 `。，` 脏标点、字幕↔配音对账 🔴；test_render_voice.py 锁死。
"""
import re


def clean_text(t: str) -> str:
    t = re.sub(r'[⚡💥🪝]', '', t)                          # 钩子 emoji 永不念出
    t = re.sub(r'(?:钩子|爽点|集尾)\s*$', '', t)             # 行尾裸词钩子标记（仅行尾，避免误伤正文同字）
    t = t.replace('||', '，')                              # 停顿一拍 → 逗号（TTS 自然气口）
    t = re.sub(r'[，,]\s*[，,]+', '，', t)                  # 收拢叠出的逗号（治 ||紧跟逗号→「，，」）
    t = re.sub(r'([。！？…—；：、》」』）])\s*[，,]\s*', r'\1', t)  # ||紧跟句末标点/破折号：去多余逗号+尾随空格（治「。，」「——，」）
    t = re.sub(r'^\s*[，,]\s*', '', t)                     # 行首多余逗号
    t = re.sub(r'\s+([，,])', r'\1', t)                    # 逗号前不留空格（治 裸气口「字 || 字」→「字 ，字」）
    t = re.sub(r'，\s+', '，', t)                          # 中文逗号后不留空格
    return re.sub(r'\s+', ' ', t).strip()
