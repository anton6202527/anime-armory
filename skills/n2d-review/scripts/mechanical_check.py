#!/usr/bin/env python3
"""n2d-review 机检 —— 对一集的产物做**确定性**质检（秒级、可复跑）。

覆盖确定性问题：字幕文本/时间码对账、中英字幕错位、占位未精修、单行溢出、
配音↔字幕↔镜头时长三者一致、产物完整性、钩子/集尾留存信号缺失。

**不覆盖**需要语义判断的维度（崩脸/构图/景别/节奏体感/口型）——那些走
references/checklist.md 的「人判」清单，由 LLM 对照参考图与分镜语法判。
可选的脸部相似度度量需第三方库（insightface / face_recognition），缺库时
显式标「跳过」，绝不静默略过。

用法：
    python3 mechanical_check.py <作品根> 第N集 [--json] [--zh-max N] [--en-max N]
退出码：有 🔴 阻断级 → 1，否则 0。
"""
import sys, os, re, json, glob, subprocess

BLOCK, WARN, INFO = "🔴", "🟡", "🟢"
ZH_LINE_MAX = 20   # 中文单行字数上限（竖屏 9:16，超易溢出/换行难看）
EN_LINE_MAX = 42   # 英文单行字符上限
TIME_TOL = 0.30    # 字幕时间码 vs 配音时长清单 允许漂移（秒）

findings = []  # (sev, dim, loc, msg)
def add(sev, dim, loc, msg): findings.append((sev, dim, loc, msg))


def tc_to_sec(tc):
    h, m, rest = tc.strip().split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path):
    if not os.path.exists(path):
        return None
    raw = open(path, encoding="utf-8").read().strip()
    cues = []
    for b in re.split(r"\n\s*\n", raw):
        lines = [l for l in b.splitlines() if l.strip()]
        ti = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if ti is None or ti + 1 >= len(lines):
            continue
        try:
            a, z = lines[ti].split("-->")
            cues.append({"start": tc_to_sec(a), "end": tc_to_sec(z),
                         "text": "\n".join(lines[ti + 1:])})
        except ValueError:
            continue
    return cues


def voice_dir(root, ep):
    """配音目录：合成/<ep>/配音/（配音先行）或 出视频/<ep>/配音/（先出视频后配音）
    ——两处都探，返回第一个存在 时长清单.json 的；都没有则返回默认合成路径。"""
    for base in ("合成", "出视频"):
        d = os.path.join(root, base, ep, "配音")
        if os.path.isfile(os.path.join(d, "时长清单.json")):
            return d
    return os.path.join(root, "合成", ep, "配音")


def load_manifest(root, ep):
    p = os.path.join(voice_dir(root, ep), "时长清单.json")
    if not os.path.exists(p):
        return None, p
    try:
        return json.load(open(p, encoding="utf-8")), p
    except Exception as e:
        add(BLOCK, "完整性", p, f"时长清单.json 解析失败：{e}")
        return None, p


PLACEHOLDER = re.compile(r"待精修|占位|placeholder|TODO|（待")


def check_subtitles(root, ep, manifest, zh_max, en_max):
    zh = parse_srt(os.path.join(root, "脚本", ep, "字幕_中文.srt"))
    en = parse_srt(os.path.join(root, "脚本", ep, "字幕_英文.srt"))
    if zh is None:
        add(WARN, "完整性", ep, "缺 字幕_中文.srt（未到分镜设计阶段则正常）")
        return
    # 占位未精修
    for i, c in enumerate(zh, 1):
        if PLACEHOLDER.search(c["text"]):
            add(BLOCK, "字幕", f"中文 cue#{i}", f"字幕仍是占位未精修：{c['text'][:30]}…")
    # 中英 cue 数一致（finalize 按 index 取 EN 文本，错位是已知坑）
    if en is not None and len(en) != len(zh):
        add(BLOCK, "字幕", ep,
            f"中英字幕条数不一致（中{len(zh)}/英{len(en)}）——删镜未同步删 EN 块会逐条错位")
    # 单行溢出
    for i, c in enumerate(zh, 1):
        for ln in c["text"].splitlines():
            if len(ln) > zh_max:
                add(WARN, "字幕", f"中文 cue#{i}", f"单行 {len(ln)} 字 >{zh_max}，竖屏易溢出：{ln[:24]}…")
    if en:
        for i, c in enumerate(en, 1):
            for ln in c["text"].splitlines():
                if len(ln) > en_max:
                    add(WARN, "字幕", f"英文 cue#{i}", f"单行 {len(ln)} 字符 >{en_max}")
    # 单调不重叠
    for i in range(1, len(zh)):
        if zh[i]["start"] < zh[i - 1]["end"] - 0.05:
            add(WARN, "字幕", f"中文 cue#{i+1}", "时间码与上一条重叠")
    # 字幕 ↔ 配音时长清单 对账（文本 + 时间码）
    if manifest is not None:
        if len(zh) != len(manifest):
            add(BLOCK, "字幕", ep,
                f"中文字幕条数({len(zh)}) ≠ 配音句数({len(manifest)})——字幕/配音脱节，重跑 finalize_storyboard")
        else:
            for i, (c, m) in enumerate(zip(zh, manifest), 1):
                mt = (m.get("文本") or "").strip()
                if mt and mt.replace(" ", "") != c["text"].replace(" ", "").replace("\n", ""):
                    add(BLOCK, "字幕", f"中文 cue#{i}",
                        f"字幕文本≠配音文本｜字幕『{c['text'][:18]}』vs 配音『{mt[:18]}』")
                if "start" in m and abs(c["start"] - m["start"]) > TIME_TOL:
                    add(WARN, "字幕", f"中文 cue#{i}",
                        f"起点漂移 {c['start']-m['start']:+.2f}s（字幕{c['start']:.2f}/配音{m['start']:.2f}）")


def check_rhythm(ep, manifest):
    """留存信号：钩子密度 + 集尾 cliffhanger（确定性的部分；体感节奏走人判）。"""
    if not manifest:
        return
    hooks = [m for m in manifest if (m.get("钩子") or "").strip()]
    if not hooks:
        add(WARN, "节奏", ep, "全集无任何 钩子/爽点/集尾 标记——留存曲线可能没设计（见 导演节奏.md）")
    # 集尾：最后 2 句里应有收尾钩
    tail = manifest[-2:] if len(manifest) >= 2 else manifest
    if manifest and not any((m.get("钩子") or "").strip() for m in tail):
        add(WARN, "节奏", ep, "集尾 2 句无 cliffhanger 标记——结尾可能把戏讲完了，断不住")


def check_completeness(root, ep, manifest):
    def n(*p): return os.path.join(root, *p)
    # 配音
    if manifest is None:
        add(WARN, "完整性", ep, "缺 时长清单.json（未配音则正常）")
    else:
        vdir = voice_dir(root, ep)
        for m in manifest:
            w = os.path.join(vdir, m.get("line_wav", ""))
            if m.get("line_wav") and not os.path.exists(w):
                add(WARN, "完整性", f"{ep} {m['line_wav']}", "时长清单列了但 wav 不存在")
        if any(m.get("占位") for m in manifest):
            add(BLOCK, "完整性", ep, "配音仍为占位音色（占位:true）——出图/出视频前必须换真实配音重定时")
    # 故事板镜头 ⊆ 时长清单镜头
    sb = n("脚本", ep, "镜头时长.json")
    if os.path.exists(sb) and manifest:
        try:
            shots = set(json.load(open(sb, encoding="utf-8")).keys())
            voiced = {m.get("镜头") for m in manifest}
            missing = [s for s in shots if s not in voiced]
            if missing:
                add(WARN, "完整性", ep, f"镜头时长含未配音镜头：{', '.join(sorted(missing)[:6])}")
        except Exception:
            pass
    # 视频 clip / 成片 存在性（仅提示，非阻断）
    clips = glob.glob(n("出视频", ep, "视频", "*.mp4"))
    finals = glob.glob(n("*成片_" + ep + "*.mp4")) + glob.glob(n("合成", ep, "成片*.mp4"))
    add(INFO, "完整性", ep,
        f"产物快照：配音句 {len(manifest) if manifest else 0} · clip {len(clips)} · 成片 {len(finals)}")


def _ffprobe(path):
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
            text=True)
        return json.loads(out)
    except Exception:
        return None


def _duration(path):
    data = _ffprobe(path)
    if not data:
        return None
    try:
        return float((data.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        return None


def _has_audio(path):
    data = _ffprobe(path)
    if not data:
        return None
    return any(s.get("codec_type") == "audio" for s in data.get("streams", []))


def check_storyboard_and_video(root, ep):
    """Machine-readable continuity contract + clip integrity checks."""
    sb_p = os.path.join(root, "脚本", ep, "storyboard.json")
    if not os.path.exists(sb_p):
        add(BLOCK, "故事板", sb_p, "缺机器可读 storyboard.json——下游无法稳定校验 continuity / need_endframe")
        return
    try:
        sb = json.load(open(sb_p, encoding="utf-8"))
    except Exception as e:
        add(BLOCK, "故事板", sb_p, f"storyboard.json 解析失败：{e}")
        return
    clips = sb.get("clips")
    if not isinstance(clips, list) or not clips:
        add(BLOCK, "故事板", sb_p, "storyboard.json 缺 clips[]")
        return
    prev_end = None
    need_endframes = 0
    for i, c in enumerate(clips, 1):
        cont = c.get("continuity") or {}
        loc = f"clip#{i}"
        if not isinstance(cont, dict):
            add(BLOCK, "故事板", loc, "continuity 不是对象")
            continue
        for k in ("start_state", "end_state", "transition", "need_endframe"):
            if k not in cont:
                add(BLOCK, "故事板", loc, f"continuity 缺字段：{k}")
        if prev_end and cont.get("start_state") != prev_end:
            add(BLOCK, "衔接", loc, "start_state 未原样继承上一 Clip 的 end_state")
        prev_end = cont.get("end_state")
        if cont.get("need_endframe") is True:
            need_endframes += 1
            endp = cont.get("endframe_png")
            full = os.path.join(root, endp) if endp and not os.path.isabs(endp) else endp
            if not endp or not os.path.exists(full):
                add(BLOCK, "尾帧", loc, "need_endframe=true 但 endframe_png 缺失或文件不存在")
    if need_endframes:
        add(INFO, "尾帧", ep, f"本集需要尾帧接力 {need_endframes} 处")

    mp4s = sorted(glob.glob(os.path.join(root, "出视频", ep, "视频", "*.mp4")))
    if mp4s and len(mp4s) != len(clips):
        add(WARN, "视频", ep, f"clip MP4 数 {len(mp4s)} 与 storyboard clips {len(clips)} 不一致")
    audio = [p for p in mp4s if _has_audio(p)]
    if audio:
        add(WARN, "原生音轨", audio[0], "clip 含原生音轨；compose 默认应丢弃，若混入需确认无原生人声")
    shots_p = os.path.join(root, "脚本", ep, "镜头时长.json")
    # 仅当整集 clip 都齐了(len(mp4s)==len(clips))才比总长——增量生产中只出了几个 clip 时
    # 拿部分对全集总时长会刷无意义的「差 N 秒」假警告。
    if os.path.exists(shots_p) and mp4s and len(mp4s) == len(clips):
        try:
            target = sum(float(v) for v in json.load(open(shots_p, encoding="utf-8")).values())
            ds = [_duration(p) for p in mp4s]
            if all(d is not None for d in ds):
                total = sum(d for d in ds if d is not None)
                if abs(total - target) > 1.0:
                    add(WARN, "时长", ep, f"clip 总长 {total:.2f}s 与镜头时长累计 {target:.2f}s 差 {abs(total-target):.2f}s")
        except Exception:
            pass


def check_watermark(root, ep):
    settings = os.path.join(root, "_设置.md")
    wm = "AI合规标识"
    if os.path.exists(settings):
        txt = open(settings, encoding="utf-8").read()
        m = re.search(r"水印\s*[:：]\s*([^\s#]+)", txt)
        if m:
            wm = m.group(1)
    if wm == "不打":
        add(WARN, "水印", settings, "水印设置为不打；正式投放 AI 合成内容建议保留 AI 合规标识")
        return
    finals = glob.glob(os.path.join(root, "合成", ep, f"成片_{ep}_*_水印.mp4"))
    plain = glob.glob(os.path.join(root, "合成", ep, f"成片_{ep}_*.mp4"))
    if plain and not finals:
        add(BLOCK, "水印", os.path.join(root, "合成", ep), f"水印设置为「{wm}」，但未找到 *_水印.mp4")


def check_face_consistency(root, ep):
    """可选·脸部一致性度量。缺库时显式标跳过（绝不静默）。"""
    try:
        import face_recognition  # noqa
    except Exception:
        try:
            import insightface  # noqa
        except Exception:
            add(INFO, "一致性", ep,
                "脸部相似度度量已跳过（未装 face_recognition/insightface）——崩脸暂由人判清单覆盖；"
                "装库后本项可自动给每镜 vs 定妆锚点打相似度分")
            return
    add(INFO, "一致性", ep, "检测到脸部识别库——可在此接入 定妆锚点 vs 镜头图 余弦相似度评分（阈值默认 0.45）")


def _opt_int(argv, name, default):
    """读 --name=N 或 --name N 两种写法的整数选项（任一无效则回默认）。"""
    for i, a in enumerate(argv):
        if a.startswith(name + "="):
            try: return int(a.split("=", 1)[1])
            except ValueError: return default
        if a == name and i + 1 < len(argv):
            try: return int(argv[i + 1])
            except ValueError: return default
    return default


def main():
    argv = sys.argv[1:]
    opts = [a for a in argv if a.startswith("--")]
    # 位置参数：剔除选项名(--x)及其紧随的值(--zh-max 8 里的 8)，避免把选项值当成 作品根/集号
    skip = set()
    for i, a in enumerate(argv):
        if a in ("--zh-max", "--en-max") and i + 1 < len(argv):
            skip.add(i + 1)
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and i not in skip]
    if len(args) < 2:
        print("用法：python3 mechanical_check.py <作品根> 第N集 [--json] [--zh-max N] [--en-max N]")
        sys.exit(2)
    root, ep = args[0], args[1]
    zh_max = _opt_int(argv, "--zh-max", ZH_LINE_MAX)
    en_max = _opt_int(argv, "--en-max", EN_LINE_MAX)
    if not os.path.isdir(root):
        print(f"作品根不存在：{root}"); sys.exit(2)

    manifest, _ = load_manifest(root, ep)
    check_completeness(root, ep, manifest)
    check_subtitles(root, ep, manifest, zh_max, en_max)
    check_rhythm(ep, manifest)
    check_storyboard_and_video(root, ep)
    check_watermark(root, ep)
    check_face_consistency(root, ep)

    if "--json" in opts:
        print(json.dumps([{"sev": s, "dim": d, "loc": l, "msg": m}
                          for s, d, l, m in findings], ensure_ascii=False, indent=2))
    else:
        order = {BLOCK: 0, WARN: 1, INFO: 2}
        nb = sum(1 for f in findings if f[0] == BLOCK)
        nw = sum(1 for f in findings if f[0] == WARN)
        print(f"\n=== n2d-review 机检：{root} {ep} ===")
        print(f"🔴 阻断 {nb} · 🟡 建议 {nw} · 🟢 信息 {sum(1 for f in findings if f[0]==INFO)}\n")
        for s, d, l, m in sorted(findings, key=lambda f: order[f[0]]):
            print(f"{s} [{d}] {l}: {m}")
        print("\n（语义维度——崩脸/构图/景别/节奏体感/口型——见 references/checklist.md 人判清单）")
    sys.exit(1 if any(f[0] == BLOCK for f in findings) else 0)


if __name__ == "__main__":
    main()
