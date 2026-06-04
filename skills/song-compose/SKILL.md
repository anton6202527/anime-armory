---
name: song-compose
description: 写歌·作曲+演唱 — 把定稿歌词 + 曲风，生成一首【带人声】的完整歌（歌/song.wav）。多后端：云 Suno/Udio / 本地 ACE-Step(Mac可跑)/DiffRhythm；不是 TTS（TTS 不会唱）。song 写歌线第 2 步。Use when asked to 作曲 / 生成歌曲 / 出歌 / 让它唱出来 / Suno / ACE-Step / 把词谱成歌. Triggers 作曲, 生成歌曲, 出歌, 唱出来, 谱曲, Suno, Udio, ACE-Step, DiffRhythm, song-compose.
---

# song-compose — 作曲 + 演唱（写歌线第 2 步）

把 `写歌/<曲名>/词/lyrics.md`（定稿）+ 曲风，生成**带人声的完整歌** `歌/song.wav`。**自包含**，只用通用音乐生成工具。

> **关键认知**：项目里的 CosyVoice/FishSpeech 是 **TTS（说话），不会唱歌**。唱歌必须用**音乐生成模型**（出曲+人声）或歌声转换。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`作曲后端`。

## 后端（先云后本地，详见 `references/backends.md`）
| 路线 | 方案 | 装/要 | Mac |
|---|---|---|---|
| 云·最快 MVP | **Suno / Udio**（web 或 API） | 账号 / `SUNO_API_KEY` | ✅ |
| 本地·主力候选 | **ACE-Step v1.5** | pip + 权重，CoreML | ✅ |
| 本地·扩散 | **DiffRhythm 2** | pip + 权重 | ⚠️CUDA 偏好 |

> 像 LoRA 那样**先本地验证 ACE-Step 在 Mac 的出歌质量/速度**再定主力；MVP 先用 Suno 云最快听到成品。

## 工作流
0. **合法性闸门**：演唱音色 = 自有 / 授权 / 合成；**克隆真人嗓需授权**（2026 opt-in），未授权拒做。把音色来源记进 `_meta.vocal_source`。
1. **组 prompt**：从 `词/lyrics.md` 取结构化歌词 + `创作蓝图.md` 的曲风/情绪/平台 → 拼成音乐模型的「lyrics + style」输入（Suno: lyrics 框 + style 框；ACE-Step: --lyrics --prompt）。
2. **生成**：
   - 云 Suno → web 生成或 API（见 backends.md），下载到 `歌/`。
   - 本地 ACE-Step → headless 调用（见 backends.md）。
   - 任一方式产出后，用 `scripts/place_song.py` **归一**成 `歌/song.wav` + 可选 demucs 分离 `vocals/instrumental`。
3. **挑版**：音乐生成随机性大，**多生几版挑最佳**（旋律记忆点/演唱情绪/与词贴合）。
4. **落档**：`歌/song.wav` 定稿；回写 `_进度.md`。下一步：继续 `song-cover`（可选换音色）或把成品歌交 **`mv`** 做视频。

## 归一脚本
```bash
python3 <skill>/scripts/place_song.py <写歌作品根> <生成的歌文件> [--split]
# 拷成 歌/song.wav；--split 用 demucs 分出 vocals/instrumental（对齐/卡点更准）
```

## 详细参考
- 后端安装/调用（Suno API、ACE-Step headless、prompt 组法）：`references/backends.md`

## 常见错误
| 错误 | 纠正 |
|---|---|
| 拿 TTS 来"唱" | TTS 不会唱；必用音乐生成模型(Suno/ACE-Step) |
| 克隆真人歌手嗓未授权 | 拒做；只用自有/授权/合成音色 |
| 一版就定 | 多生几版挑旋律/演唱最佳 |
| 不分离人声直接给 mv-lyric-sync | demucs 分 vocals 对齐更准（--split） |
| 想复用 n2d-voice | 那是说话 TTS；唱歌各写各的 |
