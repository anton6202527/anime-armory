# n2d-compose Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `n2d-compose` skill — assemble a finished 漫剧 episode from the per-Clip videos in `视频/` + (optional) the `配音/` voice track + (optional) BGM (placeholder/file/Suno) + burned bilingual subtitles → `成片_第N集_{mode}.mp4`. This automates the 剪映 "字幕+混音" step in FFmpeg.

**Architecture:** SKILL.md (instructions incl. the BGM-options prompt + industry-norm reference + optional 转场音效) + `compose.sh` (refactored from this session's `_compose.sh`: argv 作品根/集/mode; reads `视频/`+`配音/`+SRT; placeholder-or-file BGM; voice-ducking via `sidechaincompress`; subtitle burn) + `render_subs.py` (Pillow→transparent-PNG subtitles, ported as-is; needed because this machine's Homebrew ffmpeg has NO libass). Verification = smoke-run on 第1集's real assets (8 clips + voice_zh.wav + SRT).

**Tech Stack:** bash + ffmpeg/ffprobe (Homebrew, NO libass), Python 3.9 + Pillow (subtitle PNG render), macOS system fonts (STHeiti/Arial).

**This is skill-authoring (markdown + helper scripts).** "Tests" = smoke-runs on 第1集 real data + a burned-subtitle frame check. Follow the n2d skill pattern (SKILL.md + references/ + helper scripts). Reuse the verified session scripts — do NOT rewrite their internals beyond the specified refactor.

**Paths:**
- Skill dir: `/Users/lalala/learn/anime-armory/.claude/skills/n2d-compose/`
- Port FROM: `制漫剧/冷宫有妖气/出视频/_compose.sh`, `制漫剧/冷宫有妖气/出视频/_render_subs.py`
- Test 作品: `/Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气/` (第1集 has 8 clips at `出视频/第1集/Clip*.mp4` flat, `出视频/第1集/配音/voice_zh.wav`, `脚本/第1集/字幕_{中文,英文}.srt`)
- Git branch: `design/n2d-pipeline-reorder` (stay on it)

---

### Task 1: Skill skeleton + SKILL.md (incl BGM-options prompt + 行业参考文案)

**Files:**
- Create: `.claude/skills/n2d-compose/SKILL.md`
- Create: `.claude/skills/n2d-compose/references/` (dir)

- [ ] **Step 1: Create dir + SKILL.md with EXACTLY this content**

`.claude/skills/n2d-compose/SKILL.md`:
```markdown
---
name: n2d-compose
description: Stage 6 of novel2drama (剪映合成的脚本化替代) — assemble a finished episode 成片 from 视频/ clips + (可选)配音轨 + (可选)BGM(占位/文件/Suno) + 烧录双语字幕. Mixes voice with BGM ducking, burns subtitles via Pillow+overlay (本机 ffmpeg 无 libass). Writes _进度.md 成片 column. Use when asked to 合成, 合成成片, 成片, 加BGM, 加背景音乐, 烧字幕, 混音, 出成片, 导出成片. Triggers 合成, 成片, 加BGM, 背景音乐, 烧字幕, 混音, 导出, compose, 剪映.
---

# n2d-compose — 合成成片（剪映那步的脚本化替代）

把一集的 `视频/`(clips) + `配音/voice_*.wav`(可选) + BGM(可选) + 字幕 烧成 `成片_第N集_{mode}.mp4`。

## 核心原则
- **配音先行**：BGM 垫在配音下面并被配音 ducking（先有配音再压 BGM）。配音轨由 n2d-voice 在前置阶段产出，本 skill **只消费不生成**。
- **字幕烧录**：本机 Homebrew ffmpeg **无 libass**（无 subtitles/drawtext 滤镜）→ 用 Pillow 把 SRT 渲染成透明 PNG 再 overlay 烧录（render_subs.py）。
- **占位 BGM 为主**：默认程序化占位；可选真实文件覆盖。

## 输入前置
- `出视频/第N集/视频/` 有 clip MP4（n2d-video 产物）。否则报错建议先 /n2d-video。
- `出视频/第N集/配音/voice_{zh,en}.wav`（n2d-voice 产物，可选；无则纯 BGM+字幕）。
- `脚本/第N集/字幕_{中文,英文}.srt`。

## 加 BGM —— 给用户更丰富选项 + 接受自定义
到 BGM 环节，提示用户：
> 「BGM 怎么来？ⓐ 你用 Suno 生成一条给我文件 ⓑ 素材库选 ⓒ 指定本地文件 ⓓ 占位合成。也可以直接说你的想法（循环某首/某风格/某时长），我**鉴定合理可行**(文件存在/格式/时长够循环/版权)后按你的来；不可行说明原因给替代。」
用户给文件 → `BGMFILE=<路径>`；否则占位。

## 转场音效（可选层）
clip 已带即梦原生音效。额外「2~5 个转场音效」做成可选：用户给 SFX 文件就在 clip 边界铺，不给跳过。

## 行业参考（决定音频时展示给用户）
> 对于 90 秒左右的一集漫剧，很多工作室会准备：
> - 1 条背景音乐（全程循环）
> - 2~5 个转场音效
> - AI 角色配音

## 工作流
1. 归集 `视频/` clips → 统一 1080x1920/30fps → 拼接。
2. BGM：`BGMFILE` 文件(loop/trim+fade) 或 程序化占位。
3. 混音：配音(若有) + ducking BGM + clip 自带音效底。
4. 烧字幕（render_subs.py，模式 zh/en/bilingual）。
5. 输出 `成片_第N集_{mode}.mp4`；回写 `_进度.md` 成片列。

## 调用
见 references/usage.md。
```

- [ ] **Step 2: Commit**

```bash
cd /Users/lalala/learn/anime-armory
mkdir -p .claude/skills/n2d-compose/references
git add .claude/skills/n2d-compose/SKILL.md
git commit -m "feat(n2d-compose): skill skeleton + SKILL.md"
```

---

### Task 2: Port render_subs.py (Pillow subtitle renderer)

**Files:**
- Create: `.claude/skills/n2d-compose/render_subs.py` (from `出视频/_render_subs.py`)

- [ ] **Step 1: Copy as-is (it already has the smaller-font ZH_SIZE/EN_SIZE env fix)**

```bash
cd /Users/lalala/learn/anime-armory
cp 制漫剧/冷宫有妖气/出视频/_render_subs.py .claude/skills/n2d-compose/render_subs.py
```

- [ ] **Step 2: Verify it imports + Pillow present**

```bash
python3 -c "import PIL; print('Pillow',PIL.__version__)" && python3 -m py_compile .claude/skills/n2d-compose/render_subs.py && echo OK
```
Expected: `Pillow 11.x` then `OK`. (If Pillow missing: `python3 -m pip install --user Pillow`.)

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/n2d-compose/render_subs.py
git commit -m "feat(n2d-compose): port Pillow subtitle renderer"
```

---

### Task 3: Refactor compose.sh — consume 视频/+配音/, drop internal voice-gen, argv 作品根/集/mode

**Files:**
- Create: `.claude/skills/n2d-compose/compose.sh` (refactored from `出视频/_compose.sh`)
- Reference: existing `制漫剧/冷宫有妖气/出视频/_compose.sh` (READ IT — current version: argv MODE only; hard-coded 8-clip array; internally CALLS `_render_voice.py` to make the voice; calls `_render_subs.py`; placeholder/BGMFILE BGM; final mix with sidechaincompress ducking + overlay subs)

- [ ] **Step 1: Write the refactored compose.sh**

Create `.claude/skills/n2d-compose/compose.sh` with this content (it changes the argv, reads clips from `视频/`, reads the voice track from `配音/` instead of generating it, and uses the skill's own `render_subs.py`):

```bash
#!/usr/bin/env bash
# 合成成片：视频/clips + (可选)配音轨 + BGM + 烧字幕 → 成片_第N集_{mode}.mp4
# 用法: bash compose.sh <作品根> <第N集> [bilingual|zh|en]
# 可选: BGMFILE=/path/to/music.mp3   传真实BGM(否则程序化占位)
set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$1"; EP="$2"; MODE="${3:-bilingual}"
case "$MODE" in zh|bilingual) VLANG=zh;; en) VLANG=en;; *) echo "bad mode"; exit 1;; esac
BGMFILE="${BGMFILE:-}"
VID="$ROOT/出视频/$EP/视频"
VOICE="$ROOT/出视频/$EP/配音/voice_${VLANG}.wav"
ZH_SRT="$ROOT/脚本/$EP/字幕_中文.srt"; EN_SRT="$ROOT/脚本/$EP/字幕_英文.srt"
W="$ROOT/出视频/$EP/_work"; rm -rf "$W"; mkdir -p "$W"
OUT="$ROOT/出视频/$EP/成片_${EP}_${MODE}.mp4"

[ -d "$VID" ] || { echo "缺 $VID（先 /n2d-video）"; exit 1; }
mapfile -t CLIPS < <(ls "$VID"/*.mp4 | sort)
[ "${#CLIPS[@]}" -gt 0 ] || { echo "$VID 无 clip"; exit 1; }

echo "=== [1/6] 统一规格 1080x1920/30fps ==="
: > "$W/list.txt"; i=0
for c in "${CLIPS[@]}"; do
  ffmpeg -y -loglevel error -i "$c" \
    -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,fps=30,format=yuv420p" \
    -c:v libx264 -preset medium -crf 18 -c:a aac -ar 44100 -ac 2 "$W/n$i.mp4"
  echo "file 'n$i.mp4'" >> "$W/list.txt"; i=$((i+1))
done

echo "=== [2/6] 拼接 ==="
ffmpeg -y -loglevel error -f concat -safe 0 -i "$W/list.txt" -c copy "$W/concat.mp4"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$W/concat.mp4")
echo "成片时长 ${DUR}s"

echo "=== [3/6] BGM ==="
if [ -n "$BGMFILE" ] && [ -f "$BGMFILE" ]; then
  echo "真实BGM: $BGMFILE"; fo=$(python3 -c "print(max(0,$DUR-3))")
  ffmpeg -y -loglevel error -stream_loop -1 -i "$BGMFILE" -t "$DUR" \
    -af "afade=t=in:d=2,afade=t=out:st=${fo}:d=3,aresample=44100" -ac 2 "$W/bgm.wav"
else
  echo "占位氛围乐"
  ffmpeg -y -loglevel error \
    -f lavfi -i "sine=frequency=55:duration=$DUR" -f lavfi -i "sine=frequency=110:duration=$DUR" -f lavfi -i "sine=frequency=164.81:duration=$DUR" \
    -filter_complex "[0:a][1:a][2:a]amix=inputs=3:normalize=0,tremolo=f=5:d=0.25,lowpass=f=380,aecho=0.8:0.7:60:0.3,volume='0.35+0.5*t/${DUR%.*}':eval=frame,alimiter=limit=0.9" \
    -ar 44100 -ac 2 "$W/bgm.wav"
fi

echo "=== [4/6] 字幕 PNG ==="
cp "$ZH_SRT" "$W/zh.srt"; cp "$EN_SRT" "$W/en.srt"
python3 "$SKILL_DIR/render_subs.py" "$W" "$MODE"
PNG_INPUTS=(); while IFS= read -r p; do PNG_INPUTS+=(-i "$p"); done < "$W/inputs.txt"
NPNG=$(grep -c . "$W/inputs.txt"); VIDX=$((2+NPNG))
VFILTER=$(cat "$W/vfilter.txt")

echo "=== [5/6] 混音 + 烧字幕 ==="
if [ -f "$VOICE" ]; then
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" "${PNG_INPUTS[@]}" -i "$VOICE" \
    -filter_complex "
      [0:a]volume=0.45[sfx];
      [${VIDX}:a]asplit=2[voxA][voxB];
      [voxA]volume=1.0[vox];
      [1:a]volume=0.9[bgm0];
      [bgm0][voxB]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=400[bgmduck];
      [sfx][bgmduck][vox]amix=inputs=3:normalize=0:duration=first:dropout_transition=0,dynaudnorm[a];
      ${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
else
  echo "（无配音轨，纯 BGM+音效底+字幕）"
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" "${PNG_INPUTS[@]}" \
    -filter_complex "[0:a]volume=0.5[sfx];[1:a]volume=0.85[bgm];[sfx][bgm]amix=inputs=2:duration=first:dropout_transition=0,dynaudnorm[a];${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
fi

echo "=== [6/6] 完成: $OUT ==="
ls -la "$OUT"
```

- [ ] **Step 2: Make executable + bash syntax check**

```bash
cd /Users/lalala/learn/anime-armory
chmod +x .claude/skills/n2d-compose/compose.sh
bash -n .claude/skills/n2d-compose/compose.sh && echo SYNTAX_OK
```
Expected: `SYNTAX_OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/n2d-compose/compose.sh
git commit -m "feat(n2d-compose): compose.sh consume 视频/+配音/, drop internal voice-gen"
```

---

### Task 4: Smoke test on 第1集 (set up 视频/, run, verify 成片 + burned subs)

**Files:** test data under `制漫剧/冷宫有妖气/出视频/第1集/`

- [ ] **Step 1: Stage the 视频/ dir from the existing flat clips (n2d-video reorg is Plan 3; do it here for the test)**

```bash
cd /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气
mkdir -p 出视频/第1集/视频
cp 出视频/第1集/Clip*.mp4 出视频/第1集/视频/ 2>/dev/null
ls 出视频/第1集/视频/*.mp4 | wc -l
```
Expected: `8`. (Voice track `出视频/第1集/配音/voice_zh.wav` already exists from Plan 1's smoke.)

- [ ] **Step 2: Run compose (zh) — voice from 配音/, placeholder BGM, burned zh subs**

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
bash /Users/lalala/learn/anime-armory/.claude/skills/n2d-compose/compose.sh \
  /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气 第1集 zh 2>&1 | tail -4
```
Expected: ends with `完成: …/成片_第1集_zh.mp4` + `ls -la` line.

- [ ] **Step 3: Verify output has video+audio and a burned subtitle is visible**

```bash
cd /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气
V=出视频/第1集/成片_第1集_zh.mp4
ffprobe -v error -show_entries stream=codec_type -of csv=p=0 "$V" | sort -u   # expect: audio AND video
ffmpeg -y -loglevel error -ss 16 -i "$V" -frames:v 1 -vf "crop=1080:520:0:1330" /tmp/compose_subcheck.png
echo "字幕帧已抽 /tmp/compose_subcheck.png"
```
Then Read `/tmp/compose_subcheck.png` and confirm a Chinese subtitle is burned in (line 4 backstory text around t=16s). Expected: `audio` and `video` both listed; the cropped frame shows white Chinese subtitle with black outline, no English.

- [ ] **Step 4: Clean test scratch (do not commit episode media)**

```bash
rm -rf 出视频/第1集/_work
```

---

### Task 5: references/usage.md (invocation + BGM options + 转场音效 + 行业文案 + progress)

**Files:**
- Create: `.claude/skills/n2d-compose/references/usage.md`

- [ ] **Step 1: Write usage.md with EXACTLY**

```markdown
# 调用规范
默认双语字幕 + 中文配音：
    bash <skill>/compose.sh <作品根> 第N集 bilingual
单语出海/国内：
    bash <skill>/compose.sh <作品根> 第N集 zh    # 国内：中字+中配
    bash <skill>/compose.sh <作品根> 第N集 en    # 出海：英字+英配
真实 BGM：
    BGMFILE=/path/to/music.mp3 bash <skill>/compose.sh <作品根> 第N集 zh
产物：<作品根>/出视频/第N集/成片_第N集_{mode}.mp4

## 输入约定
- clips：<作品根>/出视频/第N集/视频/*.mp4（n2d-video 产物）
- 配音轨：<作品根>/出视频/第N集/配音/voice_{zh,en}.wav（n2d-voice 产物，可选）
- 字幕：<作品根>/脚本/第N集/字幕_{中文,英文}.srt

## BGM 来源（提示用户给丰富选项 + 鉴定可行）
ⓐ Suno 生成给文件 ⓑ 素材库 ⓒ 本地文件(BGMFILE) ⓓ 占位。用户自由描述需求 → 鉴定(存在/格式/时长够循环/版权)→ 可行照办，不可行说明并给替代。

## 转场音效（可选）
用户给 2~5 个 SFX 文件 → 在 clip 边界铺；不给跳过。

## 行业参考（决定音频时展示）
90 秒一集漫剧工作室标配：1 条循环 BGM + 2~5 个转场音效 + AI 角色配音。

## 进度回写
完成后把 <作品根>/common/_进度.md 该集「成片」列改 ✅（列若不存在，在表头末尾追加「成片」列）。

## 字幕字号微调
render_subs.py 支持 env：ZH_SIZE(默认50) / EN_SIZE(默认34)。
```

- [ ] **Step 2: Commit**

```bash
cd /Users/lalala/learn/anime-armory
git add .claude/skills/n2d-compose/references/usage.md
git commit -m "feat(n2d-compose): usage.md (BGM options + 行业文案 + 进度)"
```

---

### Task 6: Register check + final

**Files:** none (verification)

- [ ] **Step 1: Confirm skill structure + discoverable**

```bash
find /Users/lalala/learn/anime-armory/.claude/skills/n2d-compose -type f | sort
```
Expected: `SKILL.md`, `compose.sh`, `render_subs.py`, `references/usage.md`.

- [ ] **Step 2: Confirm git clean + log**

```bash
cd /Users/lalala/learn/anime-armory
git status --short .claude/skills/n2d-compose/
git log --oneline -5 | cat
```
Expected: clean (no unstaged), 5 commits for n2d-compose.

---

## Self-Review

**Spec coverage (spec §5.4 n2d-compose):**
- 归集 视频/ → 统一规格 → 拼接 → Task 3 compose.sh steps 1-2 (reads `视频/*.mp4`). ✅
- BGM 占位/文件/Suno文件 → Task 3 step 3 (BGMFILE or placeholder; Suno = user file via BGMFILE, documented). ✅
- 混音 + ducking + clip 音效底 → Task 3 step 5 (sidechaincompress; sfx 0.45; voice optional). ✅
- 烧字幕 Pillow+overlay → Task 2 (render_subs.py port) + Task 3 step 4-5. ✅
- 转场音效 可选 → documented in SKILL.md + usage.md (Task 1/5); not auto-built (YAGNI per spec §8). ✅
- BGM 丰富选项 + 鉴定可行 → SKILL.md + usage.md (Task 1/5). ✅
- 行业参考文案 → SKILL.md + usage.md. ✅
- 输出 成片_第N集_{mode}.mp4 + 进度成片列 → Task 3 (OUT path) + Task 5 (progress rule). ✅
- 配音轨「只消费不生成」→ Task 3 reads `配音/voice_<vlang>.wav`, no render_voice call. ✅

**Placeholder scan:** No TBD/TODO. The 视频/ dir is produced by n2d-video (Plan 3); Task 4 stages it from the existing flat clips for the smoke test (explicit, not a placeholder).

**Type/name consistency:** argv `<作品根> <第N集> [mode]` consistent (Task 3 compose.sh, Task 4 smoke, Task 5 usage). `成片_${EP}_${MODE}.mp4`, `voice_${VLANG}.wav`, `视频/`, `配音/` consistent with spec §3 and Plan 1 outputs. `render_subs.py` `inputs.txt`/`vfilter.txt`/`$MODE` interface matches the ported script (unchanged from this session's working version).

**Cross-plan dependency:** consumes Plan 1's `配音/voice_*.wav`; consumes Plan 3's `视频/` dir (staged manually in Task 4 until n2d-video is updated). 成片 progress column shares the `_进度.md` reorder finalized in Plan 3.
