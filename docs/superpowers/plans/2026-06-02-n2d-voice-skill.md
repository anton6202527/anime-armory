# n2d-voice Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `n2d-voice` skill — a multi-backend AI 配音 stage that turns a per-episode `voiceover.txt` into per-line audio + a stitched track + a `时长清单.json` (per-line measured durations) that downstream stages use to drive shot timing.

**Architecture:** A SKILL.md (instructions) + a refactored `_render_voice.py` (the multi-backend TTS engine, **window-fit compression removed**, **时长清单.json output added**) + `_voice_clone.py` (MiniMax 复刻) + reference docs (backend接入: CosyVoice/GPT-SoVITS local, demucs 人声分离, MiniMax/火山 cloud). Backends are pluggable via env detection (CosyVoice / GPT-SoVITS / MiniMax / 火山 / macOS say占位). Verification is a smoke-run on 第1集's real `voiceover.txt`.

**Tech Stack:** Python 3.9 (stdlib urllib/json/subprocess), ffmpeg/ffprobe (Homebrew), macOS `say`, MiniMax T2A v2 HTTP, optional demucs/soundfile, CosyVoice & GPT-SoVITS (local, user-run).

**This is skill-authoring (markdown + helper scripts), not app code.** "Tests" = smoke-runs on 第1集 real data (we have ground truth: 13 lines) + targeted pytest on the one pure function (manifest builder). Follow the established n2d skill pattern (SKILL.md + references/ + helper scripts); do NOT introduce a test framework the other n2d skills don't use beyond the single pytest noted.

**Paths** (skill lives in repo `.claude/skills/`; test data in the 冷宫有妖气 作品):
- Skill dir: `/Users/lalala/learn/anime-armory/.claude/skills/n2d-voice/`
- Test 作品: `/Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气/`
- Existing session scripts to port FROM: `制漫剧/冷宫有妖气/出视频/_render_voice.py`, `_voice_clone.py`

---

### Task 1: Skill skeleton + SKILL.md frontmatter

**Files:**
- Create: `.claude/skills/n2d-voice/SKILL.md`
- Create: `.claude/skills/n2d-voice/references/` (dir)

- [ ] **Step 1: Create skill dir + SKILL.md with frontmatter and core principles**

Create `.claude/skills/n2d-voice/SKILL.md`:

```markdown
---
name: n2d-voice
description: Stage 2 of novel2drama (前移到出图之前) — turn a 作品 episode's voiceover.txt into AI 角色配音：per-line audio + stitched voice track + 时长清单.json (每句实测时长，驱动下游镜头时长). Multi-backend pluggable (CosyVoice / GPT-SoVITS 本地克隆 / MiniMax / 火山 / macOS say 占位), with voice-cloning + demucs 人声分离. Writes _进度.md 配音 column. Use when asked to 配音, 生成配音, 角色配音, 声音克隆, CosyVoice, GPT-SoVITS, 时长清单. Triggers 配音, 角色配音, 声音克隆, 克隆音色, CosyVoice, GPT-SoVITS, MiniMax配音, 时长清单, voiceover.
---

# n2d-voice — 配音（前移到出图前）

你是 **AI 漫剧角色配音**。把一集的 `脚本/第N集/voiceover.txt` 变成：① 逐句音频 `配音/line_NN.wav` ② 整轨 `配音/voice_{zh,en}.wav` ③ **`配音/时长清单.json`**（每句实测时长 → 下游 n2d-script 阶段2 用它定稿镜头时长）。

## 核心原则
- **配音先行**：本阶段在出图/出视频**之前**跑。配音时长决定镜头时长（节奏可控、后期省成本），**不**在这里按窗口压速。
- **后端可插拔**：检测 env 决定后端，优先级 CosyVoice/GPT-SoVITS(本地克隆·质量优先) > MiniMax/火山(云·省事) > macOS say(占位)。缺凭证回退 say 并告警。
- **一角一色**：角色→音色映射，env 可覆盖。
- **统一电平**：每句 loudnorm 到 -16 LUFS。
- **时长清单是产线桥梁**：每句 ffprobe 量时长写入 `时长清单.json`，这是配音驱动镜头的关键产物。

## 输入前置
- `脚本/第N集/voiceover.txt` 存在（n2d-script 阶段1 产物）。否则报错建议先 /n2d-script。

## 工作流
1. 解析 voiceover.txt → 逐句(镜头·角色·情绪·文本)。
2. 选后端（见 references/backends.md）；按角色映射音色。
3. 逐句生成 → loudnorm -16 → 量时长。
4. 写 `配音/line_NN.wav` + 拼 `voice_{zh,en}.wav` + 写 `时长清单.json`。
5. 回写 `_进度.md` 该集「配音」列 ✅。

## 声音克隆
见 references/cloning.md（MiniMax 复刻 / GPT-SoVITS / CosyVoice 本地克隆 + demucs 人声分离清洗）。

## 详细参考
- 后端接入与凭证：references/backends.md
- 声音克隆 + 人声分离：references/cloning.md
- 调用规范：references/usage.md
```

- [ ] **Step 2: Commit**

```bash
cd /Users/lalala/learn/anime-armory
git add .claude/skills/n2d-voice/SKILL.md
git commit -m "feat(n2d-voice): skill skeleton + SKILL.md core"
```

---

### Task 2: Port engine — `_render_voice.py` → skill, remove window-fit, add 时长清单

**Files:**
- Create: `.claude/skills/n2d-voice/render_voice.py` (ported from `制漫剧/冷宫有妖气/出视频/_render_voice.py`)
- Reference: existing `制漫剧/冷宫有妖气/出视频/_render_voice.py:1-180` (current multi-backend impl WITH window-fit)

- [ ] **Step 1: Copy the existing engine as the starting point**

```bash
cd /Users/lalala/learn/anime-armory
cp 制漫剧/冷宫有妖气/出视频/_render_voice.py .claude/skills/n2d-voice/render_voice.py
```

- [ ] **Step 2: Remove window-fit compression**

In `.claude/skills/n2d-voice/render_voice.py`, the per-line loop currently computes `win` and applies `atempo` to fit the subtitle window. DELETE the window-fit logic. Replace the per-line post step so the FX/level-normalized wav is the final `lNN.wav` directly:

Find the block (current lines ~ the `# 按窗口贴速` section):
```python
    # 按窗口贴速（留 0.12s 余量），消除与下一句重叠
    d=dur_of(tmp); target=max(win-0.12,0.5); out=os.path.join(vd,f'l{i:02d}.wav')
    if d>target:
        f=min(d/target,1.8)
        subprocess.run([FF,'-y','-loglevel','error','-i',tmp,'-af',f'atempo={f:.4f}','-ar','44100','-ac','2',out],check=True)
    else:
        os.replace(tmp,out)
    wavs.append((out,starts[i]))
```
Replace with (no compression; tmp IS the final line wav; record measured duration):
```python
    out=os.path.join(vd,f'l{i:02d}.wav'); os.replace(tmp,out)
    measured.append(dur_of(out))
    wavs.append((out,starts[i]))
```
Also DELETE the `wins=[...]` computation line near the top (no longer needed) and add `measured=[]` next to `wavs=[]`.

- [ ] **Step 3: Make line placement gap-based, not SRT-start-based**

Since timing now flows the OTHER way (durations → SRT, not SRT → audio), the stitched track should lay lines back-to-back with a small inter-line gap, NOT at SRT cue starts. Replace the final stitch block:
```python
inputs,filt,labels=[],[],[]
for k,(wav,st) in enumerate(wavs):
    inputs+=['-i',wav]; ms=int(st*1000)
    filt.append(f"[{k}:a]adelay={ms}|{ms}[a{k}]"); labels.append(f"[a{k}]")
filt.append(f"{''.join(labels)}amix=inputs={len(wavs)}:normalize=0:dropout_transition=0,apad,atrim=0:{DUR:.3f},aresample=44100[out]")
```
with sequential concat + a fixed 0.4s gap between lines (gap configurable via env `LINE_GAP`):
```python
GAP=float(os.environ.get('LINE_GAP','0.4'))
sil=os.path.join(vd,'_gap.wav')
subprocess.run([FF,'-y','-loglevel','error','-f','lavfi','-i',f'anullsrc=r=44100:cl=stereo','-t',str(GAP),sil],check=True)
concat=[]
for k,(wav,_) in enumerate(wavs):
    concat.append(wav)
    if k<len(wavs)-1: concat.append(sil)
listf=os.path.join(vd,'_concat.txt')
open(listf,'w').write('\n'.join(f"file '{os.path.abspath(p)}'" for p in concat))
subprocess.run([FF,'-y','-loglevel','error','-f','concat','-safe','0','-i',listf,'-c','copy',os.path.join(W,f'voice_{LANG}.wav')],check=True)
```

- [ ] **Step 4: Write 时长清单.json (zh only; carries per-line role+text+duration)**

After the stitch, before the final print, add (only for zh, since manifest drives shot timing from the Chinese script):
```python
if LANG=='zh':
    import json as _json
    manifest=[{"idx":i,"镜头":_shot_of(items[i][0]),"角色":items[i][0],"文本":items[i][1],"时长":round(measured[i],3),"line_wav":f"line_{i:02d}.wav"} for i in range(n)]
    out_dir=os.path.dirname(os.path.join(W,'voice_zh.wav'))  # = 配音/
    _json.dump(manifest, open(os.path.join(out_dir,'时长清单.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
```
And add a helper near the top (after imports) to pull the 镜头 tag from the role/line — since voiceover.txt lines are `[镜头N·角色·情绪] 文本`, capture 镜头 during parse. MODIFY the zh parse to also keep 镜头:
```python
# replace the zh parse block:
if LANG=='zh':
    for ln in open('脚本/第1集/voiceover.txt',encoding='utf-8'):
        m=re.match(r'\[(镜头[^·]*)·([^·]+)·[^\]]*\]\s*(.+)',ln.strip())
        if m: items.append((m.group(2).strip(), m.group(3).strip())); shots.append(m.group(1).strip())
```
Add `shots=[]` beside `items=[]`, and define `def _shot_of(role): return shots[len(_shot_seen)] ...` — simpler: index-align, so replace `_shot_of(items[i][0])` with `shots[i] if i<len(shots) else ''`. (Use `shots[i]` directly; drop the `_shot_of` helper.)

> NOTE: the episode path `脚本/第1集/` is currently hard-coded. Task 6 parameterizes it via argv. For now keep as-is to allow the Task 5 smoke run.

- [ ] **Step 5: Verify it still imports**

Run:
```bash
cd /Users/lalala/learn/anime-armory && python3 -m py_compile .claude/skills/n2d-voice/render_voice.py && echo COMPILE_OK
```
Expected: `COMPILE_OK`

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/n2d-voice/render_voice.py
git commit -m "feat(n2d-voice): port engine, drop window-fit, add 时长清单.json"
```

---

### Task 3: Smoke-run on 第1集 (say backend) — verify manifest + track

**Files:**
- Test data: `制漫剧/冷宫有妖气/脚本/第1集/voiceover.txt` (13 lines, ground truth)

- [ ] **Step 1: Run the ported engine with the say占位 backend (no API needed)**

The engine reads `zh.srt` from a workdir for timing-of-record only at parse; supply a workdir with the srt copied. Run:
```bash
cd /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
W=出视频/第1集/配音 ; mkdir -p "$W"
cp 脚本/第1集/字幕_中文.srt "$W/zh.srt"; cp 脚本/第1集/字幕_英文.srt "$W/en.srt"
unset MINIMAX_API_KEY MINIMAX_GROUP_ID VOLC_APPID VOLC_TOKEN
python3 /Users/lalala/learn/anime-armory/.claude/skills/n2d-voice/render_voice.py "$W" zh 56
```
Expected: prints `配音 zh: 13 句（后端=say...）`. Produces `$W/voice_zh.wav` and `$W/时长清单.json`.

- [ ] **Step 2: Verify the manifest has 13 entries with shot+role+duration**

Run:
```bash
python3 -c "import json;m=json.load(open('出视频/第1集/配音/时长清单.json'));print('lines',len(m));print(m[0]);assert len(m)==13;assert all('时长' in x and '镜头' in x and '角色' in x for x in m);print('MANIFEST_OK')"
```
Expected: `lines 13`, first entry shows 镜头1/沈念旁白/时长, `MANIFEST_OK`.

- [ ] **Step 3: Verify the stitched track is non-silent and ~ sum(durations)+gaps**

Run:
```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ffprobe -v error -show_entries format=duration -of csv=p=0 出视频/第1集/配音/voice_zh.wav
```
Expected: a duration > 30s (13 lines + 12×0.4s gaps), not 0.

- [ ] **Step 4: Commit (the smoke run produced no source changes; commit nothing or the .gitignore if needed)**

```bash
git status --short | grep -q . && echo "review changes" || echo "clean"
```
(配音/ artifacts are episode data, gitignored or untracked — do not commit them.)

---

### Task 4: Add CosyVoice backend

**Files:**
- Modify: `.claude/skills/n2d-voice/render_voice.py` (add backend branch)
- Create: `.claude/skills/n2d-voice/references/backends.md`

- [ ] **Step 1: Add CosyVoice env detection + a local-HTTP backend call**

CosyVoice is run by the user as a local server (FastAPI, default `http://localhost:9880` for the common CosyVoice2 API fork, or the official `cosyvoice/api`). Integrate by HTTP. Add near the other backend flags in `render_voice.py`:
```python
COSY_URL=os.environ.get('COSYVOICE_URL')  # e.g. http://localhost:9880
USE_COSY=bool(COSY_URL) and not (os.environ.get('MINIMAX_API_KEY') and os.environ.get('MINIMAX_GROUP_ID'))
```
Set backend priority so CosyVoice wins when its URL is set AND no MiniMax creds. Add a `cosy_tts(text, spk_ref, out_wav)` function:
```python
def cosy_tts(text, ref_audio, ref_text, out_wav):
    # zero-shot 接口（CosyVoice2 常见 fork：/tts 或 /inference_zero_shot）
    import urllib.parse
    q=urllib.parse.urlencode({"text":text,"prompt_text":ref_text,"prompt_wav":ref_audio})
    req=urllib.request.Request(f"{COSY_URL}/inference_zero_shot?{q}")
    with urllib.request.urlopen(req,timeout=120) as r: open(out_wav,'wb').write(r.read())
```
> NOTE: CosyVoice forks differ in endpoint/params. references/backends.md MUST document the exact endpoint per fork and that the user sets `COSYVOICE_URL` + `COSY_REF_AUDIO` + `COSY_REF_TEXT`. Treat this function as the adapter point.

Add the branch in the per-line loop BEFORE the MiniMax branch:
```python
    if USE_COSY:
        ref=os.environ.get('COSY_REF_AUDIO'); rtext=os.environ.get('COSY_REF_TEXT','')
        raw=os.path.join(vd,f'r{i:02d}.wav'); cosy_tts(text, ref, rtext, raw); sysfx=('系统' in role)
    elif USE_MM:
        ...
```

- [ ] **Step 2: Write references/backends.md**

Create `.claude/skills/n2d-voice/references/backends.md` documenting each backend: env vars, priority, voice/role mapping defaults, and the CosyVoice/GPT-SoVITS local-server setup (ports, endpoints, ref audio+text requirements). Include the table:

```markdown
# 配音后端

优先级：CosyVoice / GPT-SoVITS(本地·COSYVOICE_URL/GPTSOVITS_URL 设了) > MiniMax(MINIMAX_API_KEY+GROUP_ID) > 火山(VOLC_APPID+TOKEN) > macOS say(占位).

| 后端 | env | 说明 |
|---|---|---|
| CosyVoice | COSYVOICE_URL, COSY_REF_AUDIO, COSY_REF_TEXT | 本地零样本克隆服务；端点随 fork(常见 /inference_zero_shot) |
| GPT-SoVITS | GPTSOVITS_URL, GSV_REF_AUDIO, GSV_REF_TEXT | 本地 inference api；零样本/微调 |
| MiniMax | MINIMAX_API_KEY, MINIMAX_GROUP_ID, MINIMAX_MODEL | 云；t2a_v2；克隆见 cloning.md |
| 火山 | VOLC_APPID, VOLC_TOKEN, VOLC_CLUSTER | 云 |
| say | （无） | macOS 占位，仅冒烟用 |

角色→音色映射默认见 render_voice.py 的 MM/CosyVoice 表，均可 env 覆盖（MM_SHEN 等）。
```

- [ ] **Step 3: Verify compile**

Run: `python3 -m py_compile .claude/skills/n2d-voice/render_voice.py && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/n2d-voice/render_voice.py .claude/skills/n2d-voice/references/backends.md
git commit -m "feat(n2d-voice): CosyVoice backend + backends.md"
```

---

### Task 5: Port cloning tooling + references (MiniMax clone + demucs)

**Files:**
- Create: `.claude/skills/n2d-voice/voice_clone.py` (from `出视频/_voice_clone.py`)
- Create: `.claude/skills/n2d-voice/references/cloning.md`

- [ ] **Step 1: Copy clone script**

```bash
cd /Users/lalala/learn/anime-armory
cp 制漫剧/冷宫有妖气/出视频/_voice_clone.py .claude/skills/n2d-voice/voice_clone.py
python3 -m py_compile .claude/skills/n2d-voice/voice_clone.py && echo OK
```
Expected: `OK`

- [ ] **Step 2: Write references/cloning.md (the verified workflow from this project)**

Create `.claude/skills/n2d-voice/references/cloning.md`:
```markdown
# 声音克隆 + 人声分离

## 参考音频要求
≥10s（30-60s 更佳）、女主单人声、BGM 越小越好、mp3/wav、≤20MB。

## 人声分离（参考带 BGM 时）
demucs（首次需 `pip install --user demucs soundfile`）：
    python3 -m demucs --two-stems=vocals -o <out> <input.wav>
产物 <out>/htdemucs/<name>/vocals.wav。再 loudnorm/silenceremove 规整。

## MiniMax 复刻
source 凭证后：
    python3 voice_clone.py <参考音频> <自定义voiceID(字母开头≥8位)>
得 voice_id → 填 MM_SHEN=<voiceID> 重生该角色。

## GPT-SoVITS / CosyVoice（本地·质量更高）
见 references/backends.md 的本地服务搭建；零样本传 ref音频+ref文本即可，微调需 1min+ 干净音。
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/n2d-voice/voice_clone.py .claude/skills/n2d-voice/references/cloning.md
git commit -m "feat(n2d-voice): clone tooling + cloning.md"
```

---

### Task 6: Parameterize episode path + write references/usage.md + progress writeback

**Files:**
- Modify: `.claude/skills/n2d-voice/render_voice.py` (episode path via argv)
- Create: `.claude/skills/n2d-voice/references/usage.md`

- [ ] **Step 1: Make the voiceover.txt path derive from a 作品根 + 集 argv**

Change argv to `render_voice.py <作品根> <第N集> <zh|en>` and derive paths:
```python
ROOT, EP, LANG = sys.argv[1], sys.argv[2], sys.argv[3]
VO = os.path.join(ROOT, '脚本', EP, 'voiceover.txt')
OUTDIR = os.path.join(ROOT, '出视频', EP, '配音'); os.makedirs(OUTDIR, exist_ok=True)
SRT = os.path.join(ROOT, '脚本', EP, '字幕_中文.srt')   # 仅 en 模式取 en.srt 文本；时间轴此阶段不依赖
```
Replace the hard-coded `'脚本/第1集/voiceover.txt'`, the workdir `W`, and the `zh.srt` parse source accordingly. The stitched track + manifest write to `OUTDIR`. (The en-line text still comes from `字幕_英文.srt`.) DELETE the now-unused `starts`/SRT-timing parse — line placement is gap-based (Task 2 Step 3), so SRT timing is not needed here at all.

- [ ] **Step 2: Re-run smoke with new argv**

```bash
cd /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"; unset MINIMAX_API_KEY MINIMAX_GROUP_ID
python3 /Users/lalala/learn/anime-armory/.claude/skills/n2d-voice/render_voice.py . 第1集 zh
python3 -c "import json;m=json.load(open('出视频/第1集/配音/时长清单.json'));print('OK',len(m))"
```
Expected: `配音 zh: 13 句…`, then `OK 13`.

- [ ] **Step 3: Write usage.md (invocation + progress writeback rule)**

Create `.claude/skills/n2d-voice/references/usage.md`:
```markdown
# 调用规范
源 env(可选): source <作品根>/出视频/.minimax_env
逐句生成 + 整轨 + 时长清单：
    python3 <skill>/render_voice.py <作品根> 第N集 zh
    python3 <skill>/render_voice.py <作品根> 第N集 en   # 出海配音(英文)
产物：<作品根>/出视频/第N集/配音/{line_NN.wav, voice_zh.wav, voice_en.wav, 时长清单.json}

## 进度回写
完成后把 <作品根>/common/_进度.md 该集「配音」列改 ✅（列若不存在，本 skill 首次跑时在表头「草稿故事板」后插入「配音」列）。

## 完成消息（驱动下一阶段）
配音完成后提示助手：「配音齐 → 下一步 /n2d-script <作品根> 第N集 用时长清单定稿故事板+SRT，再 /n2d-image」。
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/n2d-voice/render_voice.py .claude/skills/n2d-voice/references/usage.md
git commit -m "feat(n2d-voice): argv 作品根/集 + usage.md + 进度回写规则"
```

---

### Task 7: Register skill + smoke-run with real backend (MiniMax, optional) + final review

**Files:**
- Modify: `.claude/skills/n2d-voice/SKILL.md` (cross-link references; ensure triggers)

- [ ] **Step 1: Confirm skill is discoverable**

Run:
```bash
ls /Users/lalala/learn/anime-armory/.claude/skills/n2d-voice/
```
Expected: `SKILL.md  references/  render_voice.py  voice_clone.py` and `references/` has backends.md, cloning.md, usage.md.

- [ ] **Step 2: (Optional, if creds present) MiniMax smoke run reusing the cloned voice**

```bash
cd /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气
[ -f 出视频/.minimax_env ] && source 出视频/.minimax_env
python3 /Users/lalala/learn/anime-armory/.claude/skills/n2d-voice/render_voice.py . 第1集 zh
```
Expected: `后端=MiniMax`; 配音/ updated; 时长清单.json regenerated.

- [ ] **Step 3: Final commit**

```bash
cd /Users/lalala/learn/anime-armory
git add .claude/skills/n2d-voice/
git commit -m "feat(n2d-voice): finalize skill (skeleton + engine + clone + references)"
```

---

## Self-Review

**Spec coverage (spec §5.2 n2d-voice):**
- 多后端可插拔 → Tasks 2,4 (say/MiniMax/火山 ported; CosyVoice added; GPT-SoVITS documented in backends.md). ✅
- 声音克隆 + demucs → Task 5. ✅
- 角色→音色映射(env 覆盖) → ported in Task 2, documented Task 4. ✅
- 逐句生成 + loudnorm -16 → preserved from ported engine. ✅
- **量每句时长写 时长清单.json** → Task 2 Step 4, verified Task 3 Step 2. ✅
- 拼整轨 voice_{zh,en} → Task 2 Step 3. ✅
- **去掉按窗口压速** → Task 2 Step 2. ✅
- 进度「配音」列 → Task 6 Step 3 (rule documented; the actual column insert is shared with Plan 3 dispatcher reorder — flagged). ✅
- 可独立重生 → argv-driven (Task 6), env-overridable voices. ✅

**Placeholder scan:** CosyVoice endpoint is fork-dependent (Task 4 flags it as the adapter point + documents in backends.md) — this is a real external variability, not a plan placeholder; the adapter function + env contract are concrete. No TBD/TODO left.

**Type/name consistency:** `时长清单.json` schema (idx/镜头/角色/文本/时长/line_wav) defined Task 2, consumed by verification Task 3 — consistent. argv signature `<作品根> <第N集> <zh|en>` consistent across Tasks 6,7. `voice_{LANG}.wav`, `line_NN.wav` naming consistent.

**Cross-plan dependency:** the 配音 progress column + dispatcher reorder is fully realized in Plan 3; Plan 1 only writes the ✅ and documents insertion. The `时长清单.json` produced here is the input contract for Plan 3's n2d-script 阶段2. Flagged in both.
