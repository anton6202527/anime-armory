---
name: song-compose
description: 写歌·作曲+演唱 — 把定稿歌词 + 曲风生成带人声完整歌；完整 A&R/参考/和声/topline 合同与实际后端提交字段分层，由本线 compiler 映射 Suno/Udio/ACE-Step/DiffRhythm 的 style/prompt、lyrics、duration；多版登记、评分、挑版定稿。Use when asked 作曲 / 生成歌曲 / 出歌 / 音乐 prompt / prompt compiler / Suno / ACE-Step / 把词谱成歌 / 挑版. Triggers 作曲, 生成歌曲, 出歌, 唱出来, 谱曲, 音乐prompt, prompt compiler, Suno, Udio, ACE-Step, DiffRhythm, 挑版, 多版, song-compose.
---

# song-compose — 作曲 + 演唱（写歌线第 2 步）

把 `创作区/写歌/<曲名>/词/lyrics.md`（定稿）+ 曲风 + A&R 简报/参考边界/和声草图，生成**带人声的完整歌** `歌/song.wav`。**自包含**，只用通用音乐生成工具。

> **关键认知**：项目里的 CosyVoice/FishSpeech 是 **TTS（说话），不会唱歌**。唱歌必须用**音乐生成模型**（出曲+人声）或歌声转换。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/song-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`作曲后端`、`生成版数`、`目标时长`、`语言`、`BPM/速度`、`调性`、`挑版策略`、`AI音频使用披露`。

## 后端（先云后本地，详见 `references/backends.md`）
| 路线 | 方案 | 装/要 | Mac |
|---|---|---|---|
| 云·最快 MVP | **Suno / Udio**（web 或 API） | 账号 / `SUNO_API_KEY` | ✅ |
| 本地·主力候选 | **ACE-Step v1.5** | pip + 权重，CoreML | ✅ |
| 本地·扩散 | **DiffRhythm 2** | pip + 权重 | ⚠️CUDA 偏好 |

> 像 LoRA 那样**先本地验证 ACE-Step 在 Mac 的出歌质量/速度**再定主力；MVP 先用 Suno 云最快听到成品。

## 工作流
0. **合法性闸门**：演唱音色 = 自有 / 授权 / 合成；**克隆真人嗓需授权**（2026 opt-in），未授权拒做。把音色来源记进 `_meta.vocal_source`。
1. **生成作曲任务包**：先跑 `scripts/compose_song.py`，从 `_设置.md` / `_meta.json` / `词/lyrics.md` / `创作蓝图.md`，并自动读取可选的 `创作/song_brief.md`、`素材/reference_pack.md`、`歌/chord_sheet.md`、`歌/topline_notes.md` 生成：
   - `歌/compose_task.md`
   - `歌/compose_task.json`
   - `歌/compose_prompts/take_XX.md`
   - `歌/takes_manifest.json`
   > **完整合同 ≠ 后端字段**：take Markdown 保留 A&R brief、参考边界、和声、topline、操作提示和挑版标准；`skills/song/_lib/song_prompt_compiler.py` 只把可执行的声音身份、Style seed、情绪动态、hook 意图编译到 style/prompt 字段，把**完整歌词原文**放 lyrics 字段，把时长放结构化参数。Suno/Udio、ACE-Step、DiffRhythm 的字段名不同，由 profile 映射；不得把整份 Markdown 粘进一个 prompt 框，也不得摘要歌词。
   > **Style Prompt 配方**：整体声音写 `曲风 + 情绪 + BPM + 调性 + 器乐编制 + 人声类型 + 动态走向 + hook 意图`；段内转场/器乐高光/演唱方式靠歌词内联元标签（`[Build]`/`[Drop]`/`[Instrumental]`/`[Whispered]`…）。compiler 会消费 `song_brief.json.sonic_identity/emotional_arc/hook_deadline_seconds`，但不会把 reference pack、权利说明或文件路径拼进 style。
2. **按后端编译字段生成多版**：
   - 云 Suno/Udio → 只把 take 的 `submit_fields.style` / `submit_fields.lyrics` / title 分别贴入 Custom 字段；下载到 `歌/`。
   - 本地 ACE-Step → `submit_fields.prompt`、`lyrics`、`audio_duration` 分列传入 headless 调用。
   - DiffRhythm / manual → 按任务包生成。
3. **登记 take**：外部生成的每版音频用 `compose_song.py --register <音频> --take N` 写回 `歌/takes/take_NN.wav` 和 manifest。
4. **挑版**：音乐生成随机性大，**多生几版挑最佳**（副歌 hook / 人声清晰 / 与蓝图贴合 / MV 卡点适配）。先用 `take_review.py` 记录盲听分、timecode note、风险和推荐版；再用 `compose_song.py --score take_NN ...` 同步到 manifest。
5. **落档**：用 `compose_song.py --select take_NN` 把选中版归一成 `歌/song.wav`；回写 `_进度.md`。下一步：继续 `song-cover`（可选换音色）或 `song-review` / `song-craft` 合规留痕；如需视频制作，交付最终音频成品即可。

## 多版任务包 / 挑版脚本
```bash
python3 <skill>/scripts/compose_song.py <写歌作品根> --backend ACE-Step --takes 4 --duration 120
python3 <skill>/scripts/compose_song.py <写歌作品根> --register ./out.wav --take 1
python3 <skill>/scripts/compose_song.py <写歌作品根> --score take_01 --hook-score 5 --vocal-score 4 --fit-score 5 --notes "副歌最稳"
python3 <skill>/scripts/compose_song.py <写歌作品根> --select take_01
python3 <skill>/scripts/take_review.py <写歌作品根> --take take_01 \
  --hook-score 5 --melody-score 5 --vocal-score 4 --arrangement-score 4 --mix-score 4 --fit-score 5 \
  --timecode "00:38|note|副歌进入很稳" --write
```

## 兼容归一脚本
```bash
python3 <skill>/scripts/place_song.py <写歌作品根> <生成的歌文件> [--split]
# 拷成 歌/song.wav；--split 用 demucs 分出 vocals/instrumental（对齐/卡点更准）
```
`place_song.py` 保留给旧流程和用户已有成品歌；新流程优先 `compose_song.py`，因为它会留下多版和挑版记录。

## 详细参考
- 后端安装/调用（Suno API、ACE-Step headless、prompt 组法）：`references/backends.md`

## 常见错误
| 错误 | 纠正 |
|---|---|
| 拿 TTS 来"唱" | TTS 不会唱；必用音乐生成模型(Suno/ACE-Step) |
| 克隆真人歌手嗓未授权 | 拒做；只用自有/授权/合成音色 |
| 一版就定 | 先生成/登记多版，按 take manifest 挑旋律/演唱最佳 |
| 把 A&R/参考/和声说明整份粘进 style | 只提交 `后端编译提交字段`；完整合同留给制作决策、复核和溯源 |
| 为了“精简 prompt”摘要或删改歌词 | 禁止；歌曲 compiler 只精简 style，上游定稿歌词原文完整进入 lyrics 字段并以 hash 锁定 |
| 需要更准地检查人声 | 先用 demucs 分离 vocals，再做试听和时间点核对 |
| 拿说话 TTS 当唱歌 | TTS 只能说话；唱歌必须走音乐生成或歌声转换 |
