#!/usr/bin/env python3
"""fit_voice_to_clips.py — 把【后期补录的真实配音】拟合到【已成片的镜头时长】。

仅用于 `制作模式 = 先出视频后配音`（快速 demo·不推荐，见 novel2drama SKILL「制作模式」节）。
在该模式下，视频是按**估算时长**锁死出的；真实配音补在最后，每句长短与锁定镜头不一致。
本脚本把真音逐镜头放回锁定时间轴，使配音轨总长 = 视频总长、不再渐进失步：

  - 真音 ≤ 镜头槽位     → `pad`     ：放在槽位起点，尾部补静音（无损）。
  - 槽位 < 真音 ≤ 槽位×MAX → `stretch` ：atempo 轻微提速塞进槽位（语速略快，已告警）。
  - 真音 > 槽位×MAX      → `overflow`：差太多，**不静默处理**——列出需回 n2d-video
                                       重出/重切（加长）的镜头，退出码 2 让用户定夺。

读：`脚本/第N集/镜头时长.json`（锁定槽位，驱动了 clip 长）
    `出视频/第N集/配音/时长清单.json`（补录真音的逐句时长 + line_wav；须 占位=false）
产（--apply）：`出视频/第N集/配音/voice_<lang>_fitted.wav`，交 compose.sh 用 VOICEFILE= 指向它。

纯标准库 + ffmpeg/ffprobe（仅 --apply 时调）。规划逻辑 plan() 不依赖 ffmpeg，可单测。

用法：
  python3 fit_voice_to_clips.py <作品根> <第N集> <lang>            # 只出对账计划（dry-run）
  python3 fit_voice_to_clips.py <作品根> <第N集> <lang> --apply    # 生成 fitted.wav
环境：FIT_MAX_STRETCH(默认1.25) FIT_TOL_FRAC(0.10) FIT_TOL_MIN(0.3)
"""
import json
import os
import re
import subprocess
import sys


def shot_num(name):
    """'镜头12' → 12；无数字 → 大数（排末尾）。"""
    m = re.search(r"(\d+)", str(name))
    return int(m.group(1)) if m else 10**9


def plan(slots, reals, max_stretch=1.25, tol_frac=0.10, tol_min=0.3):
    """纯函数：根据锁定槽位 + 真音时长算逐镜头拟合动作。

    slots: [(镜头名, 槽位秒)]，按时间轴顺序。
    reals: {镜头名: (真音秒, 源)}；源 = 该镜头的拼接素材（aggregate_reals 产的 parts 列表），
           或单 wav 路径（兼容旧调用），或 None=该镜头无台词→按静音填满槽位。
    返回逐行 dict：镜头/slot/real/wav/action(pad|stretch|overflow)/ratio/over(超出秒)/minor(是否微调)。
    """
    rows = []
    for shot, slot in slots:
        real, wav = reals.get(shot, (0.0, None))
        over = max(0.0, real - slot)
        tol = max(slot * tol_frac, tol_min)
        if real <= slot:
            action, ratio = "pad", 1.0
        elif real <= slot * max_stretch:
            action, ratio = "stretch", real / slot  # atempo>1 提速压进槽位
        else:
            action, ratio = "overflow", real / slot
        rows.append({"镜头": shot, "slot": round(slot, 3), "real": round(real, 3),
                     "wav": wav, "action": action, "ratio": round(ratio, 4),
                     "over": round(over, 3), "minor": over <= tol})
    return rows


# ---- 以下为 IO / ffmpeg 层（--apply 才用到）----

def ffdur(p):
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", p], text=True).strip()
        return float(out)
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return 0.0


def aggregate_reals(man, vdir, dur_fn):
    """把 manifest 逐句【按镜头聚合】成 {镜头: (总真音秒, [(wav或None, 句时长, 句后留拍)])}。

    一个镜头常含多句台词；早先版本用 reals[shot]=(dur,wav) 逐句覆盖，只剩最后一句、
    前面几句的语音被静默丢弃。这里按 manifest 顺序把同一镜头的所有句子收进 parts 列表，
    总时长口径 = ∑(句时长 + 句后留拍)，与 finalize_storyboard 锁镜头槽位的口径一致
    （finalize: shots[sh] += (end-start) + gap_after，对该镜头每一句都累加）。

    dur_fn(wav路径)->秒：注入便于单测；生产传 ffdur（文件缺失/探测失败回 0）。
    """
    agg = {}
    for r in man:
        if not isinstance(r, dict):
            continue
        shot = r.get("镜头")
        if not shot:
            continue
        lw = r.get("line_wav")
        wav = os.path.join(vdir, lw) if lw else None
        d = dur_fn(wav) if wav else 0.0
        if d and d > 0:                       # 有可用真音 → 用实测时长
            line_dur, use_wav = d, wav
        else:                                  # 无 line_wav/探测失败 → 退回清单 时长 字段，按静音占位
            line_dur, use_wav = float(r.get("时长", 0) or 0), None
        gap = float(r.get("gap_after", 0) or 0)
        a = agg.setdefault(shot, {"dur": 0.0, "parts": []})
        a["dur"] += line_dur + gap
        a["parts"].append((use_wav, line_dur, gap))
    return {s: (round(a["dur"], 3), a["parts"]) for s, a in agg.items()}


def load_inputs(root, ep):
    shots_p = os.path.join(root, "脚本", ep, "镜头时长.json")
    man_p = os.path.join(root, "出视频", ep, "配音", "时长清单.json")
    if not os.path.isfile(shots_p):
        sys.exit(f"⛔ 缺 {shots_p}（阶段2 未定稿，无锁定镜头时长可拟合）")
    if not os.path.isfile(man_p):
        sys.exit(f"⛔ 缺 {man_p}（先 /n2d-voice 补录真实配音）")
    with open(shots_p, encoding="utf-8") as f:
        shots = json.load(f)
    with open(man_p, encoding="utf-8") as f:
        man = json.load(f)

    slots = sorted(((k, float(v)) for k, v in shots.items()),
                   key=lambda kv: shot_num(kv[0]))
    vdir = os.path.dirname(man_p)
    ph = [r for r in man if isinstance(r, dict) and r.get("占位")]
    reals = aggregate_reals(man, vdir, lambda p: ffdur(p) if (p and os.path.isfile(p)) else 0.0)
    return slots, reals, ph


def _silence_wav(path, dur, sr):
    subprocess.check_call(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", f"anullsrc=r={sr}:cl=mono", "-t", f"{max(dur, 0.001):.3f}", path])


def _shot_source(parts, work, idx, sr):
    """把一个镜头的多句（wav 或静音）按 manifest 顺序（含句间留拍）拼成一条源音轨，返回路径。

    parts: [(wav或None, 句时长, 句后留拍)]。None=该句无真音，用其估算时长的静音占位。
    每句之后追加 gap_after 静音，使源轨长 ≈ aggregate_reals 算出的镜头真音总长。
    """
    sub = os.path.join(work, f"src{idx}.parts")
    os.makedirs(sub, exist_ok=True)
    lst = os.path.join(sub, "list.txt")
    with open(lst, "w", encoding="utf-8") as lf:
        for j, (wav, ldur, gap) in enumerate(parts):
            p = os.path.join(sub, f"p{j}.wav")
            if wav:
                subprocess.check_call(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                     "-ac", "1", "-ar", str(sr), p])
            else:
                _silence_wav(p, ldur, sr)
            lf.write(f"file '{os.path.basename(p)}'\n")
            if gap and gap > 0:               # 句后留拍（镜头内）
                g = os.path.join(sub, f"g{j}.wav")
                _silence_wav(g, gap, sr)
                lf.write(f"file '{os.path.basename(g)}'\n")
    out = os.path.join(sub, "src.wav")
    subprocess.check_call(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", lst, "-c", "copy", out])
    return out


def build_fitted(rows, out_wav):
    """按 plan 逐镜头生成等于槽位长的片段并拼接。仅在无 overflow 时调用。"""
    work = out_wav + ".parts"
    os.makedirs(work, exist_ok=True)
    listf = os.path.join(work, "list.txt")
    SR = 44100
    with open(listf, "w", encoding="utf-8") as lf:
        for i, r in enumerate(rows):
            seg = os.path.join(work, f"s{i}.wav")
            slot = r["slot"]
            src = r["wav"]
            if isinstance(src, list):
                # 多句镜头：先把该镜头所有句子拼回一条源轨（不再只取最后一句）
                src = _shot_source(src, work, i, SR) if src else None
            if not src:  # 无台词镜头 → 整槽静音
                _silence_wav(seg, slot, SR)
            else:
                af = [f"aresample={SR}"]
                if r["action"] == "stretch":
                    af.append(f"atempo={r['ratio']:.4f}")
                # 先(必要时)提速，再补静音到槽位，最后硬裁到槽位长 → 片段=精确槽位
                af.append(f"apad=whole_dur={slot}")
                af.append(f"atrim=0:{slot}")
                subprocess.check_call(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", src,
                     "-af", ",".join(af), "-ac", "1", "-ar", str(SR), seg])
            lf.write(f"file '{os.path.basename(seg)}'\n")
    subprocess.check_call(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", listf, "-c", "copy", out_wav])


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    root, ep, lang = argv[0], argv[1], argv[2]
    apply = "--apply" in argv[3:]
    max_stretch = float(os.environ.get("FIT_MAX_STRETCH", "1.25"))
    tol_frac = float(os.environ.get("FIT_TOL_FRAC", "0.10"))
    tol_min = float(os.environ.get("FIT_TOL_MIN", "0.3"))

    slots, reals, ph = load_inputs(root, ep)
    if ph:
        sys.exit(f"⛔ 时长清单仍有 {len(ph)} 句占位音色——本脚本要拟合的是**真实配音**。"
                 "先 /n2d-voice 用 CosyVoice/克隆/MiniMax 补真音重跑，再来拟合。")

    rows = plan(slots, reals, max_stretch, tol_frac, tol_min)
    pad = sum(1 for r in rows if r["action"] == "pad")
    stretch = [r for r in rows if r["action"] == "stretch"]
    overflow = [r for r in rows if r["action"] == "overflow"]
    slot_total = sum(r["slot"] for r in rows)
    real_total = sum(r["real"] for r in rows)

    print(f"=== 真音拟合对账 {ep}（先出视频后配音模式）===")
    print(f"镜头 {len(rows)} | 锁定总长 {slot_total:.2f}s | 真音总长 {real_total:.2f}s "
          f"| 差 {real_total - slot_total:+.2f}s")
    print(f"pad(无损补静音) {pad} | stretch(轻微提速) {len(stretch)} | overflow(需重出) {len(overflow)}")
    for r in stretch:
        print(f"  ⚠️ {r['镜头']}: 真音 {r['real']:.2f}s > 槽位 {r['slot']:.2f}s "
              f"→ atempo×{r['ratio']:.2f} 提速塞入" + ("（微调，几乎无感）" if r["minor"] else "（语速会变快）"))
    for r in overflow:
        print(f"  🔴 {r['镜头']}: 真音 {r['real']:.2f}s 远超槽位 {r['slot']:.2f}s（超 {r['over']:.2f}s）"
              f" → 回 /n2d-video 重出/重切此镜头加长，或显式接受重度提速")

    if overflow:
        print(f"\n🔴 {len(overflow)} 个镜头真音严重超长，**不静默处理**。"
              "请二选一：①回 n2d-video 重出/重切上列镜头加长（推荐）"
              "②确认接受重度变速后调高 FIT_MAX_STRETCH 重跑。未决前不生成 fitted 轨。")
        return 2

    if not apply:
        print("\n（dry-run）以上可自动拟合，无 overflow。加 --apply 生成 fitted 轨。")
        return 0

    out_wav = os.path.join(root, "出视频", ep, "配音", f"voice_{lang}_fitted.wav")
    build_fitted(rows, out_wav)
    print(f"\n✅ 已生成拟合配音轨：{out_wav}（总长≈{slot_total:.2f}s，对齐已成片镜头）")
    print(f"   合成时指向它：VOICEFILE='{out_wav}' bash <skill>/compose.sh {root} {ep} {lang}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
