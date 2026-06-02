# n2d Pipeline Re-order Implementation Plan (Plan 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Close the "配音驱动镜头时长" loop: split `n2d-script` into a pre-voice stage (草稿故事板, no locked durations) + a post-voice 定稿 stage that consumes `配音/时长清单.json` to lock storyboard Clip durations and generate real-timed SRTs; make `n2d-video` output to `视频/` and read voice-driven durations; reorder the `novel2drama` dispatcher stages + progress columns.

**Architecture:** One new pure-ish helper `finalize_storyboard.py` (the bridge: 时长清单.json + existing en-SRT text → re-timed `字幕_中/英.srt` + `镜头时长.json`), plus SKILL.md edits to three existing skills. The helper is the only new logic and is unit-tested; the rest is instruction-doc edits verified by a smoke run.

**Tech Stack:** Python 3.9 stdlib (json/re), pytest for the helper.

**This modifies EXISTING skills — follow their established patterns, change ONLY what the re-order requires. Do not restructure unrelated sections.**

**Paths:**
- New helper: `/Users/lalala/learn/anime-armory/.claude/skills/n2d-script/finalize_storyboard.py`
- Helper test: `/Users/lalala/learn/anime-armory/.claude/skills/n2d-script/test_finalize_storyboard.py`
- Edit: `.claude/skills/n2d-script/SKILL.md`, `.claude/skills/n2d-video/SKILL.md`, `.claude/skills/novel2drama/SKILL.md`
- Test data: `制漫剧/冷宫有妖气/出视频/第1集/配音/时长清单.json` (13 lines, from Plan 1 smoke), `制漫剧/冷宫有妖气/脚本/第1集/字幕_英文.srt`
- Git branch: `design/n2d-pipeline-reorder`

---

### Task 1: `finalize_storyboard.py` — the bridge (TDD)

**Files:**
- Create: `.claude/skills/n2d-script/test_finalize_storyboard.py`
- Create: `.claude/skills/n2d-script/finalize_storyboard.py`

The core pure function `build(manifest, en_texts, gap)` takes the 时长清单 list, a list of en subtitle texts (same length/order), and a gap (s). It returns `(zh_srt:str, en_srt:str, shot_durations:dict)` where each manifest line is one SRT cue placed back-to-back with `gap` between cues, and `shot_durations[镜头] = sum(line 时长 in that 镜头) + gap`.

- [ ] **Step 1: Write the failing test**

`.claude/skills/n2d-script/test_finalize_storyboard.py`:
```python
import finalize_storyboard as F

def test_build_srt_and_shots():
    manifest=[
        {"idx":0,"镜头":"镜头1","角色":"沈念","文本":"甲。","时长":2.0},
        {"idx":1,"镜头":"镜头1","角色":"沈念","文本":"乙。","时长":1.0},
        {"idx":2,"镜头":"镜头2","角色":"柳娘子","文本":"丙。","时长":3.0},
    ]
    en=["A.","B.","C."]
    zh_srt, en_srt, shots = F.build(manifest, en, gap=0.5)
    # 3 cues, back-to-back with 0.5s gaps: c0 0-2, c1 2.5-3.5, c2 4-7
    assert "00:00:00,000 --> 00:00:02,000" in zh_srt
    assert "甲。" in zh_srt
    assert "00:00:02,500 --> 00:00:03,500" in zh_srt
    assert "00:00:04,000 --> 00:00:07,000" in zh_srt
    assert "A." in en_srt and "C." in en_srt
    assert "00:00:04,000 --> 00:00:07,000" in en_srt  # same timecodes
    # shot durations: 镜头1 = 2+1 +gap = 3.5 ; 镜头2 = 3 +gap = 3.5
    assert abs(shots["镜头1"]-3.5)<1e-6
    assert abs(shots["镜头2"]-3.5)<1e-6
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd /Users/lalala/learn/anime-armory/.claude/skills/n2d-script && python3 -m pytest test_finalize_storyboard.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'finalize_storyboard'`).

- [ ] **Step 3: Implement finalize_storyboard.py**

`.claude/skills/n2d-script/finalize_storyboard.py`:
```python
#!/usr/bin/env python3
# 配音时长 → 定稿：时长清单.json(+现有en字幕文本) → 重定时 字幕_中/英.srt + 镜头时长.json
# 用法: finalize_storyboard.py <作品根> <第N集> [gap]
import sys, os, re, json

def _ts(t):
    h=int(t//3600); m=int((t%3600)//60); s=int(t%60); ms=int(round((t-int(t))*1000))
    if ms==1000: s+=1; ms=0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def build(manifest, en_texts, gap=0.4):
    zh=[]; en=[]; shots={}; t=0.0
    for i,row in enumerate(manifest):
        d=float(row["时长"]); start=t; end=t+d
        zh.append(f"{i+1}\n{_ts(start)} --> {_ts(end)}\n{row['文本']}\n")
        etxt=en_texts[i] if i<len(en_texts) else ""
        en.append(f"{i+1}\n{_ts(start)} --> {_ts(end)}\n{etxt}\n")
        sh=row.get("镜头","")
        shots[sh]=shots.get(sh,0.0)+d
        t=end+gap
    for k in shots: shots[k]=round(shots[k]+gap,3)  # 每镜加一份留白
    return "\n".join(zh), "\n".join(en), shots

def _parse_srt_texts(path):
    out=[]
    if not os.path.exists(path): return out
    for b in re.split(r'\n\s*\n', open(path,encoding='utf-8').read().strip()):
        ls=[l for l in b.splitlines() if l.strip()]
        if len(ls)>=3: out.append(' '.join(ls[2:]))
    return out

def main():
    root, ep = sys.argv[1], sys.argv[2]
    gap = float(sys.argv[3]) if len(sys.argv)>3 else 0.4
    manifest=json.load(open(os.path.join(root,'出视频',ep,'配音','时长清单.json'),encoding='utf-8'))
    en_texts=_parse_srt_texts(os.path.join(root,'脚本',ep,'字幕_英文.srt'))
    zh_srt,en_srt,shots=build(manifest,en_texts,gap)
    open(os.path.join(root,'脚本',ep,'字幕_中文.srt'),'w',encoding='utf-8').write(zh_srt)
    open(os.path.join(root,'脚本',ep,'字幕_英文.srt'),'w',encoding='utf-8').write(en_srt)
    json.dump(shots, open(os.path.join(root,'脚本',ep,'镜头时长.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"定稿: {len(manifest)} 句重定时 → 字幕_中/英.srt；{len(shots)} 镜 → 镜头时长.json")

if __name__=='__main__': main()
```

- [ ] **Step 4: Run test, verify pass**

Run: `cd /Users/lalala/learn/anime-armory/.claude/skills/n2d-script && python3 -m pytest test_finalize_storyboard.py -q`
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/lalala/learn/anime-armory
git add .claude/skills/n2d-script/finalize_storyboard.py .claude/skills/n2d-script/test_finalize_storyboard.py
git commit -m "feat(n2d-script): finalize_storyboard.py — 配音时长→定稿SRT+镜头时长 (TDD)"
```

---

### Task 2: n2d-script SKILL.md — split into 阶段1(pre-voice) / 阶段2(定稿)

**Files:** Modify `.claude/skills/n2d-script/SKILL.md`

- [ ] **Step 1: Read the file** to locate "第 3 步 — 逐集精修 8 类素材" and its material list (items 1-7) + the "完成后…8 列" line.

- [ ] **Step 2: Replace the material-list section.** Change "第 3 步" so that 故事板 is produced as a DRAFT (no locked Clip durations) and SRT is NOT produced here. Replace the numbered list item 2 and item 7 and the completion line.

Replace item 2:
```
2. `故事板.md` — Clip 表（相邻分镜合成片段，AI 视频输入；写清人物运动 + 镜头运动 + 动态细节；Clip 时长/运镜按目标视频 AI 档案）
```
with:
```
2. `故事板.md`（**草稿**）— Clip 表（相邻分镜合成片段；写清人物运动 + 镜头运动 + 动态细节；**Clip 时长留空/标 TBD —— 时长在配音后由 /n2d-voice 的时长清单定稿，本步不锁**；运镜按目标视频 AI 档案）
```
Replace item 7:
```
7. `字幕_中文.srt` + `字幕_英文.srt` — **中英双语 SRT**（同一套时间码，时间轴依 `故事板.md` 时长 + `voiceover.txt` 台词推导）
```
with:
```
（注：`字幕_中文.srt` / `字幕_英文.srt` **不在本步生成**。它们的时间轴必须由真实配音时长决定 → 在 /n2d-voice 跑完后，于本 skill 的**阶段2 定稿**生成，见下。本步只产出英文字幕**文本草稿**供阶段2 重定时用。）
```
Replace the completion line:
```
完成后在 `_进度.md` 对应集勾选物料 8 列 ✅。
```
with:
```
完成后在 `_进度.md` 勾选阶段1 物料列：分镜剧本 / 草稿故事板 / 素材清单 / 配音文案(voiceover) / bgm / 封面 / 字幕英(草稿文本) ✅。**下一步是 /n2d-voice 配音**（不是出图）。
```

- [ ] **Step 3: Add the 阶段2 section.** After the "第 4 步 — 报告 + 推进" block, INSERT a new section:
```markdown
## 阶段2 — 故事板/字幕定稿（配音后回跑本 skill）

**触发**：该集 `配音` 列 ✅（/n2d-voice 已产 `出视频/第N集/配音/时长清单.json`）后，回跑本 skill 做定稿。`配音` 列未 ✅ 时拒绝定稿并提示先 /n2d-voice。

**做两件事**：
1. 生成真实时间轴的 SRT + 每镜时长：
   ```bash
   python3 <skill>/finalize_storyboard.py <作品根> 第N集
   ```
   产出 `脚本/第N集/字幕_{中文,英文}.srt`（按配音逐句实测时长重定时）+ `脚本/第N集/镜头时长.json`（每镜聚合时长）。
2. 用 `镜头时长.json` **锁定 `故事板.md` 的 Clip 时长**：每个 Clip 时长 = 其包含分镜的镜头时长之和；单 Clip 超目标视频 AI 上限（如即梦 ≤8s）则**拆 Clip**（尾帧=下一首帧）。
**完成后**：`_进度.md` 勾选 `故事板定稿` / `字幕中` / `字幕英` ✅。下一步 /n2d-image。
```

- [ ] **Step 4: Verify the edits are coherent** (no dangling references):
```bash
grep -nE "草稿|阶段2|finalize_storyboard|时长清单|配音 列" /Users/lalala/learn/anime-armory/.claude/skills/n2d-script/SKILL.md | head
```
Expected: shows the new 草稿/阶段2/finalize references.

- [ ] **Step 5: Commit**

```bash
cd /Users/lalala/learn/anime-armory
git add .claude/skills/n2d-script/SKILL.md
git commit -m "feat(n2d-script): split 阶段1(草稿) / 阶段2(配音后定稿故事板+SRT)"
```

---

### Task 3: n2d-video SKILL.md — 视频/ output dir + voice-driven Clip durations

**Files:** Modify `.claude/skills/n2d-video/SKILL.md`

- [ ] **Step 1: Read the file** to locate: the "prompt / 产物分离铁律" line (~line 13), the 输入前置条件, the 阶段 D 落档 paths, and the 调用规范 `--out` path.

- [ ] **Step 2: Change MP4 output location from flat to `视频/`.** Replace the 产物分离铁律 line:
```
- **prompt / 产物分离铁律**：每个 `出视频/` 目录（`common/` 跨集复用片段 或 `第N集/`）都分两层——所有 prompt md 进 `prompt/` 子目录，生成 MP4 **平铺**在 prompt/ 的同级父目录。详见 `novel2drama/references/architecture.md` "prompt / 产物分离铁律"章节。
```
with:
```
- **产物归集铁律**：所有 prompt md 进 `出视频/第N集/prompt/`；**生成的 clip MP4 全部落 `出视频/第N集/视频/`**（供 /n2d-compose 归集合成）。废片去 `common/废料/出视频/第N集/`。
```
Replace 阶段 D 落档 path:
```
1. MP4 落档到 `出视频/第N集/Clip<K>_<描述>.mp4`
```
with:
```
1. MP4 落档到 `出视频/第N集/视频/Clip<K>_<描述>.mp4`
```
Replace the 调用规范 `--out`:
```
       --out <出视频/第N集/ClipK_<描述>.mp4>
```
with:
```
       --out <出视频/第N集/视频/ClipK_<描述>.mp4>
```
And in 阶段 C 分支1: replace `定稿 MP4 → 出视频/第N集/Clip<K>_<描述>.mp4` → `定稿 MP4 → 出视频/第N集/视频/Clip<K>_<描述>.mp4`; in 分支2 replace `mv 到 出视频/第N集/` → `mv 到 出视频/第N集/视频/`.

- [ ] **Step 3: Make Clip durations voice-driven + update prerequisite.** Replace the 输入前置条件 line:
```
- 作品根存在，`_进度.md` 该集的 8 类素材 + `出图prompt` + `出图` 三组列均 ✅（出图列分子 = 分母）
```
with:
```
- `_进度.md` 该集 `配音` ✅ + `故事板定稿` ✅ + `出图` 列分子=分母。**Clip 时长读定稿 `故事板.md`（来自配音时长 `镜头时长.json`），不再用平台默认估**；平台档案只约束单 Clip 上限（如即梦 ≤8s，超限拆 Clip）。
```

- [ ] **Step 4: Verify edits:**
```bash
grep -nE "视频/|配音.*故事板定稿|镜头时长|平铺" /Users/lalala/learn/anime-armory/.claude/skills/n2d-video/SKILL.md | head
```
Expected: shows `出视频/第N集/视频/` paths and the new prerequisite; the old "平铺" line is gone.

- [ ] **Step 5: Commit**

```bash
cd /Users/lalala/learn/anime-armory
git add .claude/skills/n2d-video/SKILL.md
git commit -m "feat(n2d-video): clips → 视频/ 目录 + Clip时长读定稿故事板(配音驱动)"
```

---

### Task 4: novel2drama dispatcher — reorder stages + progress columns + routing

**Files:** Modify `.claude/skills/novel2drama/SKILL.md`

- [ ] **Step 1: Read the file** — locate the "四阶段全景" diagram (~lines 19-29), the progress-table-header line (~line 50), and the "读进度 → 路由" rules (~lines 52-58).

- [ ] **Step 2: Replace the 四阶段全景 with the six-stage order.** Replace the block from `## 四阶段全景` through the `↓ （Stage 4 …不在本流水线 skill 范围）` line with:
```markdown
## 六阶段全景（配音前移·时长驱动镜头）

```
小说
   ↓ /n2d-script  阶段1   分镜剧本 + voiceover文案 + 角色/场景/style + 草稿故事板(不锁时长) + 素材清单/封面/bgm/字幕英草稿
   ↓ /n2d-voice           配音文案 → 真实配音 + 时长清单.json（每句实测时长）
   ↓ /n2d-script  阶段2   读时长清单 → 故事板Clip时长定稿 + 字幕_中/英.srt(真实时间轴) + 镜头时长.json
   ↓ /n2d-image           出图 prompt + PNG
   ↓ /n2d-video           视频 prompt + clip MP4（落 出视频/第N集/视频/，Clip长=配音驱动）
   ↓ /n2d-compose         视频/ + 配音轨 + BGM + 烧字幕 → 成片_第N集_{mode}.mp4
```
每阶段按 **集** 推进；进度统一写 `<作品根>/common/_进度.md`。
```

- [ ] **Step 3: Replace the progress-table-header line.** Replace:
```
2. 进度表头形如：`| 集 | 字数 | raw | 分镜剧本 | 故事板 | 素材清单 | 配音 | BGM | 封面 | 字幕中 | 字幕英 | 出图prompt | 出图 |`
```
with:
```
2. 进度表头形如：`| 集 | 字数 | raw | 分镜剧本 | 草稿故事板 | 配音 | 故事板定稿 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |`
```

- [ ] **Step 4: Replace the routing rules** (the bullet list under "读进度 → 路由" that maps column-states to stages). Replace that bullet list with:
```
   - 阶段1 物料列（分镜剧本…素材清单/字幕英草稿）任一 ⬜ → 还在 /n2d-script 阶段1
   - 阶段1 齐、`配音` ⬜ → 该集等 /n2d-voice 配音
   - `配音` ✅、`故事板定稿` ⬜ → 回跑 /n2d-script 阶段2 定稿（故事板时长 + SRT）
   - `故事板定稿` ✅、`出图prompt`/`出图` 未满 → /n2d-image
   - `出图` 满、`视频` 未满 → /n2d-video
   - `视频` 满、`成片` ⬜ → /n2d-compose（合成；问用户 BGM/配音选项）
```

- [ ] **Step 5: Update the description frontmatter routing mention** (if it enumerates only script/image/video). Read the `description:` line; if it says "routes the user to the right stage skill — `n2d-script` … `n2d-video`", append `/ n2d-voice / n2d-compose` to that enumeration. (Make a minimal edit — don't rewrite the whole description.)

- [ ] **Step 6: Verify edits:**
```bash
grep -nE "六阶段|n2d-voice|n2d-compose|草稿故事板|故事板定稿|成片" /Users/lalala/learn/anime-armory/.claude/skills/novel2drama/SKILL.md | head
```
Expected: shows the six-stage flow + new columns + both new skills.

- [ ] **Step 7: Commit**

```bash
cd /Users/lalala/learn/anime-armory
git add .claude/skills/novel2drama/SKILL.md
git commit -m "feat(novel2drama): 六阶段重排(配音前移) + 进度列 + 路由 + 收尾合成"
```

---

### Task 5: Smoke — finalize_storyboard.py on 第1集 real manifest

**Files:** test data (no source change)

- [ ] **Step 1: Back up the existing 第1集 SRTs** (they're hand-authored ground truth; the smoke OVERWRITES them with voice-timed ones — back up first so we don't lose the originals):
```bash
cd /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气/脚本/第1集
cp 字幕_中文.srt 字幕_中文.srt.orig; cp 字幕_英文.srt 字幕_英文.srt.orig
```

- [ ] **Step 2: Run finalize on the real 时长清单.json** (from Plan 1's say-backend smoke — 13 lines):
```bash
cd /Users/lalala/learn/anime-armory
python3 .claude/skills/n2d-script/finalize_storyboard.py 制漫剧/冷宫有妖气 第1集
```
Expected: `定稿: 13 句重定时 → 字幕_中/英.srt；N 镜 → 镜头时长.json`.

- [ ] **Step 3: Verify re-timed SRT + 镜头时长.json are coherent**
```bash
cd /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气/脚本/第1集
head -8 字幕_中文.srt
python3 -c "import json;s=json.load(open('镜头时长.json'));print('镜头数',len(s));print(s)"
# sanity: first cue starts at 0; last cue end ≈ sum(durations)+gaps
python3 -c "
import re
t=open('字幕_中文.srt',encoding='utf-8').read()
cues=re.findall(r'(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)',t)
print('cues',len(cues));assert len(cues)==13
assert cues[0][:4]==('00','00','00','000'),'first cue not at 0'
print('FINALIZE_OK')
"
```
Expected: 13 cues, first at 00:00:00,000, 镜头时长.json has the per-shot durations, `FINALIZE_OK`.

- [ ] **Step 4: Restore the original hand-authored SRTs** (this was a mechanics smoke; keep ground truth for the demo work):
```bash
cd /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气/脚本/第1集
mv 字幕_中文.srt.orig 字幕_中文.srt; mv 字幕_英文.srt.orig 字幕_英文.srt
rm -f 镜头时长.json
```
(Do not commit episode data.)

---

### Task 6: Register check + final

- [ ] **Step 1: Confirm all edits committed + skills coherent**
```bash
cd /Users/lalala/learn/anime-armory
git status --short .claude/skills/ && echo "(clean)"
git log --oneline -6 | cat
```
Expected: clean; commits for finalize_storyboard, n2d-script, n2d-video, novel2drama.

- [ ] **Step 2: Quick cross-skill consistency grep** (the new column names appear consistently across the 4 edited skills):
```bash
grep -rl "故事板定稿\|时长清单\|视频/" .claude/skills/n2d-script .claude/skills/n2d-video .claude/skills/novel2drama .claude/skills/n2d-voice .claude/skills/n2d-compose
```
Expected: lists the relevant SKILL.md files (consistent terminology).

---

## Self-Review

**Spec coverage (spec §5.1/5.3/5.5 + §4 time-manifest):**
- n2d-script 两阶段 → Task 2 (阶段1 草稿 + 阶段2 定稿 via finalize). ✅
- 时长清单 → SRT + 镜头时长 bridge → Task 1 (finalize_storyboard.py, TDD). ✅
- n2d-video 视频/ + 配音驱动时长 → Task 3. ✅
- 调度器 六阶段 + 进度列 + 路由 → Task 4. ✅
- 进度列重排为 spec §5.5 的顺序 → Task 4 Step 3. ✅
- 单 Clip 超上限拆 Clip → documented Task 2 (阶段2) + Task 3 (prereq). ✅

**Placeholder scan:** No TBD in the plan itself (the "TBD" in n2d-script item-2 edit is intentional document content marking draft-state Clip durations). No TODO.

**Type/name consistency:** column names `草稿故事板 / 配音 / 故事板定稿 / 成片` identical across Task 2/3/4. `镜头时长.json` produced by finalize (Task 1) and referenced by n2d-script 阶段2 + n2d-video prereq (Task 2/3) — consistent. `build(manifest, en_texts, gap)` signature defined in test (Task 1 Step 1) matches impl (Step 3). `视频/` path consistent with Plan 2's compose input and spec §3.

**Cross-plan dependency:** consumes Plan 1's `时长清单.json` (Task 1/5); `视频/` output (Task 3) is the input Plan 2's compose reads (Plan 2 Task 4 staged it manually — after this plan n2d-video produces it natively). 成片 column closes the progress table.
