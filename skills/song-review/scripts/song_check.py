#!/usr/bin/env python3
"""song-review 机检 —— 对一首歌的产物做**确定性**质检（秒级、可复跑）。

覆盖确定性问题：
  词     —— 占位未精修、有无副歌、段落数 vs _meta.structure 对账、同段字数离散过大（可唱性硬信号）。
  音频   —— 歌/song.wav 存在性、时长/采样率/声道、削波(clipping)、近静音/全静音、采样率过低、
            目标时长窗口、头尾静音、RMS 响度代理指标。
  挑版   —— 歌/takes_manifest.json 是否存在、selected_take 与 song.wav 对账。
  合规   —— _meta.vocal_source 合规字段缺失/未授权真人、_meta.rights_status 缺失、AI 使用披露留痕。
  完整性 —— 蓝图/进度/meta 齐全、产物快照。

**不覆盖**需要语义判断的维度（押韵自然度/hook 抓耳/曲风贴合/演唱情绪/原文照搬/AI味）——
那些走 references/checklist.md 的「人判」清单：词由 LLM 判，曲+演唱由用户试听清单判。

只用标准库（wave / array / json / re / os / glob）。无法解析的音频（非 WAV）显式标问题，绝不静默略过。

用法：
    python3 song_check.py <写歌作品根> [--json] [--spread N]
退出码：有 🔴 阻断级 → 1，否则 0。
"""
import sys, os, re, json, glob, wave, array
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SONG_UTILS_PATH = os.path.join(REPO, "skills", "song-craft", "scripts", "song_utils.py")

def load_song_utils():
    spec = importlib.util.spec_from_file_location("song_utils", SONG_UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

song_utils = load_song_utils()

BLOCK, WARN, INFO = "🔴", "🟡", "🟢"
SPREAD_MAX = 6          # 同段各行字数极差上限（超 → 字数不齐，难唱）
MIN_RATE = 44100        # 投放建议最低采样率
CLIP_THRESH = 0.995     # 样本绝对值 ≥ 满量程该比例视作削波
CLIP_RATIO = 0.005      # 削波样本占比超此值 → 报警（0.5%）
SILENCE_DBFS = -40.0    # 峰值低于此 dBFS → 近静音
RMS_LOW_DBFS = -28.0    # RMS 代理响度偏低（非 LUFS，仅机检提示）
EDGE_SILENCE_WARN = 3.0 # 头尾静音超过该秒数 → 提醒
TARGET_DURATION_TOL = 0.25

findings = []  # (sev, dim, loc, msg)
def add(sev, dim, loc, msg): findings.append((sev, dim, loc, msg))

def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception as e:
        add(BLOCK, "完整性", path, f"JSON 解析失败：{e}")
        return None


def check_lyrics(root, meta, spread_max):
    path = os.path.join(root, "词", "lyrics.md")
    if not os.path.exists(path):
        add(WARN, "完整性", "词/lyrics.md", "缺歌词（未作词则正常）")
        return
    raw = open(path, encoding="utf-8").read()
    lines = raw.splitlines()

    # 占位未精修
    for i, ln in enumerate(lines, 1):
        if song_utils.PLACEHOLDER.search(ln):
            add(BLOCK, "词", f"lyrics.md 第{i}行", f"歌词仍是占位未精修：{ln.strip()[:30]}…")

    # 分段（[tag] 行切段），统计每段词行字数
    sections = []   # (tag, [(lineno, text, chars)])
    cur_tag, cur = None, []
    for i, ln in enumerate(lines, 1):
        m = song_utils.SECTION_RE.match(ln)
        if m:
            if cur_tag is not None:
                sections.append((cur_tag, cur))
            cur_tag, cur = m.group(1).strip().lower(), []
        elif cur_tag is not None:
            s = ln.strip()
            if s and not s.startswith("#") and not s.startswith(">") and not song_utils.STAGE_DIR.match(s):
                cur.append((i, s, song_utils.line_chars(s)))
    if cur_tag is not None:
        sections.append((cur_tag, cur))

    if not sections:
        add(WARN, "词", "lyrics.md", "未解析到任何 [段落标签]——歌词可能没结构化（见 songcraft.md §结构）")
        return

    tags = [t for t, _ in sections]
    # 有无副歌
    if not any("chorus" in t or "副歌" in t for t in tags):
        add(BLOCK, "词", "lyrics.md", "全曲无 [chorus] 副歌段——副歌是全曲核心与 hook 锚（songcraft.md §副歌）")

    # 段落数 vs _meta.structure
    if meta and isinstance(meta.get("structure"), list):
        exp = len(meta["structure"])
        if exp != len(sections):
            add(WARN, "完整性", "lyrics.md",
                f"段落数({len(sections)}) ≠ _meta.structure({exp})——词与蓝图结构不一致")

    # 同段字数离散（可唱性硬信号）——只看有 ≥2 词行的段
    for tag, rows in sections:
        nums = [c for _, _, c in rows if c > 0]
        if len(nums) >= 2:
            spread = max(nums) - min(nums)
            if spread > spread_max:
                lo = min(rows, key=lambda r: r[2] if r[2] > 0 else 999)
                hi = max(rows, key=lambda r: r[2])
                add(WARN, "词", f"[{tag}]",
                    f"同段字数极差 {spread}（{min(nums)}~{max(nums)}字），偏不齐易拗口难唱"
                    f"｜短:第{lo[0]}行『{lo[1][:14]}』 长:第{hi[0]}行『{hi[1][:14]}』")

    nwords = sum(c for _, rows in sections for _, _, c in rows)
    nchorus = sum(1 for t in tags if "chorus" in t or "副歌" in t)
    add(INFO, "词", "lyrics.md", f"产物快照：{len(sections)} 段 · 副歌×{nchorus} · 词约 {nwords} 字")


def parse_settings(root):
    path = os.path.join(root, "_设置.md")
    settings = {}
    if not os.path.exists(path):
        return settings
    pat = re.compile(r"^\s*-\s*([^:：]+)\s*[:：]\s*(.*?)\s*(?:#.*)?$")
    for line in open(path, encoding="utf-8"):
        m = pat.match(line)
        if m:
            settings[m.group(1).strip()] = m.group(2).strip()
    return settings


def lyric_char_count(root):
    path = os.path.join(root, "词", "lyrics.md")
    if not os.path.exists(path):
        return 0
    total = 0
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith(">") or song_utils.SECTION_RE.match(s) or song_utils.STAGE_DIR.match(s):
            continue
        total += song_utils.line_chars(s)
    return total


def check_audio(root, progress_text, meta=None):
    path = os.path.join(root, "歌", "song.wav")
    if not os.path.exists(path):
        # 未作曲（进度里没勾出歌）则正常
        composed = bool(re.search(r"song\.wav|作曲|出歌|song-compose", progress_text or ""))
        sev = WARN if composed else INFO
        add(sev, "音频", "歌/song.wav",
            "缺成品歌 song.wav" + ("（进度提到作曲但产物不在）" if composed else "（未作曲则正常）"))
        return
    try:
        dur, rate, ch, sw, peak, clip, rms, head_silence, tail_silence = song_utils._wav_peak_clip(path)
    except (wave.Error, EOFError) as e:
        add(BLOCK, "音频", "歌/song.wav", f"音频损坏/不可解析（非标准 WAV？）：{e}")
        return

    add(INFO, "音频", "歌/song.wav",
        f"产物快照：{dur:.1f}s · {rate}Hz · {'立体声' if ch == 2 else f'{ch}声道'} · {sw*8}bit")

    settings = parse_settings(root)
    target = song_utils.parse_seconds((meta or {}).get("target_duration_seconds")) or song_utils.parse_seconds(settings.get("目标时长"))
    if target and dur:
        low = target * (1.0 - TARGET_DURATION_TOL)
        high = target * (1.0 + TARGET_DURATION_TOL)
        if dur < low or dur > high:
            add(WARN, "音频", "歌/song.wav",
                f"时长 {dur:.1f}s 偏离目标 {target}s（容差±{int(TARGET_DURATION_TOL*100)}%）——确认用途/后端时长设置")

    if rate and rate < MIN_RATE:
        add(WARN, "音频", "歌/song.wav", f"采样率 {rate}Hz < {MIN_RATE}Hz，投放偏低（重生成/导出提采样率）")
    if dur and dur < 30:
        add(WARN, "音频", "歌/song.wav", f"时长仅 {dur:.1f}s——可能是 demo 片段而非整首成品（确认是否当成品用）")

    if peak is None:
        add(INFO, "音频", "歌/song.wav", f"非 16bit PCM（{sw*8}bit），跳过削波/静音幅度分析")
        return
    if peak < 1e-6:
        add(BLOCK, "音频", "歌/song.wav", "全静音（峰值≈0）——出歌失败，回 song-compose 重生成")
    else:
        import math
        dbfs = 20 * math.log10(peak)
        if dbfs < SILENCE_DBFS:
            add(BLOCK, "音频", "歌/song.wav", f"近静音（峰值 {dbfs:.1f}dBFS < {SILENCE_DBFS}）——疑出歌失败/几乎无声")
    if rms is not None and rms > 0:
        import math
        rms_dbfs = 20 * math.log10(rms)
        if rms_dbfs < RMS_LOW_DBFS:
            add(WARN, "音频", "歌/song.wav",
                f"RMS 响度代理 {rms_dbfs:.1f}dBFS 偏低（非 LUFS）——投放前建议重混/母带检查")
    if clip is not None and clip > CLIP_RATIO:
        sev = BLOCK if clip > 0.05 else WARN
        add(sev, "音频", "歌/song.wav",
            f"削波 clipping：{clip*100:.1f}% 样本贴满量程，已失真——回 song-compose 降增益/重生成")
    if head_silence is not None and head_silence > EDGE_SILENCE_WARN:
        add(WARN, "音频", "歌/song.wav",
            f"开头静音约 {head_silence:.1f}s，短视频/平台投放可能丢 hook——回 song-compose 或剪头")
    if tail_silence is not None and tail_silence > EDGE_SILENCE_WARN:
        add(WARN, "音频", "歌/song.wav",
            f"结尾静音约 {tail_silence:.1f}s，交 MV/发布前建议处理淡出或剪尾")
    chars = lyric_char_count(root)
    if dur and chars:
        density = chars / dur
        if density > 4.2:
            add(WARN, "词/音频", "lyrics.md + song.wav",
                f"歌词密度约 {density:.1f}字/秒，可能咬字过密难唱——回 song-lyrics 调短行或降 BPM")
        elif dur > 60 and density < 0.45:
            add(WARN, "词/音频", "lyrics.md + song.wav",
                f"歌词密度约 {density:.1f}字/秒，长时长但歌词偏稀——确认是否有长间奏/纯音乐段")


def check_take_manifest(root):
    song_path = os.path.join(root, "歌", "song.wav")
    manifest_path = os.path.join(root, "歌", "takes_manifest.json")
    if not os.path.exists(manifest_path):
        if os.path.exists(song_path):
            add(WARN, "挑版", "歌/takes_manifest.json",
                "成品歌存在但缺多版 take manifest——建议用 compose_song.py 登记来源/评分/selected_take")
        return
    try:
        manifest = json.load(open(manifest_path, encoding="utf-8"))
    except Exception as e:
        add(BLOCK, "挑版", "歌/takes_manifest.json", f"manifest 解析失败：{e}")
        return
    takes = manifest.get("takes") or []
    selected = manifest.get("selected_take")
    if not takes:
        add(WARN, "挑版", "歌/takes_manifest.json", "manifest 里没有 takes，无法回溯生成版")
        return
    registered = [t for t in takes if t.get("status") in ("registered", "selected")]
    add(INFO, "挑版", "歌/takes_manifest.json",
        f"产物快照：计划 {len(takes)} 版 · 已登记 {len(registered)} 版 · selected={selected or '未选'}")
    if os.path.exists(song_path) and not selected:
        add(WARN, "挑版", "歌/takes_manifest.json", "已有 song.wav 但 selected_take 为空——补 `compose_song.py --select take_NN`")
    if selected:
        hit = next((t for t in takes if t.get("take_id") == selected), None)
        if not hit:
            add(BLOCK, "挑版", "歌/takes_manifest.json", f"selected_take={selected} 不在 takes 列表")
        elif hit.get("audio_path") and not os.path.exists(os.path.join(root, hit["audio_path"])):
            add(BLOCK, "挑版", hit["audio_path"], "selected_take 对应音频不存在")


def check_compliance(root, meta):
    if meta is None:
        add(WARN, "完整性", "_meta.json", "缺 _meta.json，无法核对合规/权利字段")
        return
    vs = (meta.get("vocal_source") or "").strip().lower()
    has_song = os.path.exists(os.path.join(root, "歌", "song.wav"))
    if not vs:
        sev = BLOCK if has_song else WARN
        add(sev, "合规", "_meta.vocal_source",
            "演唱音色来源未记录——必须为 自有/授权/合成（克隆真人嗓需 2026 opt-in 授权）")
    else:
        # 合规标记（合成/授权/自有）优先：命中即视为合法，避免被 "no real-person cloning" 这类说明误伤
        ok = any(k in vs for k in ("synthetic", "合成", "authorized", "授权", "own vocal", "own voice", "自有", "self-"))
        risky = any(k in vs for k in ("real", "真人", "歌手", "singer", "clone", "克隆"))
        if ok:
            pass  # 明确标了合成/授权/自有 → 合法
        elif risky:
            add(BLOCK, "合规", "_meta.vocal_source", f"音色来源疑为未授权真人嗓：『{vs}』——需歌手授权，否则拒用")
        else:
            add(WARN, "合规", "_meta.vocal_source", f"音色来源表述不明：『{vs}』——确认属 自有/授权/合成")
    if not (meta.get("rights_status") or "").strip():
        add(WARN, "合规", "_meta.rights_status", "词曲权利状态未记录（original/licensed/…）")


def check_ai_usage(root, meta):
    if not os.path.exists(os.path.join(root, "歌", "song.wav")):
        return
    path = os.path.join(root, "合规", "ai_usage.json")
    if not os.path.exists(path):
        add(WARN, "合规", "合规/ai_usage.json",
            "成品歌存在但缺 AI 使用披露留痕——发布/交平台/交 MV 前跑 song-craft/scripts/ai_usage.py")
        return
    try:
        payload = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        add(BLOCK, "合规", "合规/ai_usage.json", f"AI 使用披露 JSON 解析失败：{e}")
        return
    audio_mode = payload.get("audio_mode")
    if audio_mode not in ("AI-generated", "AI-assisted", "未使用AI音频"):
        add(WARN, "合规", "合规/ai_usage.json", f"audio_mode 不在约定枚举内：{audio_mode}")
    else:
        add(INFO, "合规", "合规/ai_usage.json", f"AI 使用披露：audio_mode={audio_mode}")


def check_completeness(root):
    for f, sev in (("创作蓝图.md", WARN), ("_进度.md", WARN), ("_meta.json", WARN)):
        if not os.path.exists(os.path.join(root, f)):
            add(sev, "完整性", f, "缺文件")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) < 1:
        print("用法：python3 song_check.py <写歌作品根> [--json] [--spread N]")
        sys.exit(2)
    root = args[0]
    spread_max = next((int(o.split("=")[1]) for o in opts if o.startswith("--spread=")), SPREAD_MAX)
    if not os.path.isdir(root):
        print(f"作品根不存在：{root}"); sys.exit(2)

    meta = load_json(os.path.join(root, "_meta.json"))
    prog_path = os.path.join(root, "_进度.md")
    progress_text = open(prog_path, encoding="utf-8").read() if os.path.exists(prog_path) else ""

    check_completeness(root)
    check_lyrics(root, meta, spread_max)
    check_audio(root, progress_text, meta)
    check_take_manifest(root)
    check_compliance(root, meta)
    check_ai_usage(root, meta)

    if "--json" in opts:
        print(json.dumps([{"sev": s, "dim": d, "loc": l, "msg": m}
                          for s, d, l, m in findings], ensure_ascii=False, indent=2))
    else:
        order = {BLOCK: 0, WARN: 1, INFO: 2}
        nb = sum(1 for f in findings if f[0] == BLOCK)
        nw = sum(1 for f in findings if f[0] == WARN)
        ni = sum(1 for f in findings if f[0] == INFO)
        print(f"\n=== song-review 机检：{root} ===")
        print(f"🔴 阻断 {nb} · 🟡 建议 {nw} · 🟢 信息 {ni}\n")
        for s, d, l, m in sorted(findings, key=lambda f: order[f[0]]):
            print(f"{s} [{d}] {l}: {m}")
        print("\n（语义维度——押韵/hook/曲风贴合/演唱情绪/原文照搬/AI味——见 references/checklist.md：")
        print("　词走 LLM 人判，曲+演唱走用户试听清单）")
    sys.exit(1 if any(f[0] == BLOCK for f in findings) else 0)


if __name__ == "__main__":
    main()
