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
_COMMON = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_text_utils import is_placeholder  # noqa: E402  占位检测单一真值源
from seam_contract import (  # noqa: E402
    missing_evidence as seam_missing_evidence,
    needs_end_anchor,
    normalize_seam_mode,
    requires_boundary_frame,
)

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
    """配音目录：2026 出视频/合成 拆分后配音一律落 合成/<ep>/配音/（render_voice 无条件写此处，与制作模式无关）。
    出视频/<ep>/配音/ 是已废弃的历史路径，仅作防御性兜底探测；返回第一个存在 时长清单.json 的，都没有则返回默认合成路径。"""
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


def has_fitted_voice(root, ep):
    return bool(glob.glob(os.path.join(voice_dir(root, ep), "voice_*_fitted.wav")))


def check_subtitles(root, ep, manifest, zh_max, en_max):
    zh = parse_srt(os.path.join(root, "脚本", ep, "字幕_中文.srt"))
    en = parse_srt(os.path.join(root, "脚本", ep, "字幕_英文.srt"))
    if zh is None:
        add(WARN, "完整性", ep, "缺 字幕_中文.srt（未到分镜设计阶段则正常）")
        return
    # 占位未精修
    for i, c in enumerate(zh, 1):
        if is_placeholder(c["text"]):
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
    # 脏标点 lint（气口 || 清洗残留：。，/，，/行首逗号——即便字幕与配音"同样脏"、对账能过也单独抓）
    dirty = re.compile(r'[。！？…—；：、》」』）][，,]|[，,]{2,}')
    for i, c in enumerate(zh, 1):
        joined = c["text"].replace("\n", "")
        if dirty.search(joined) or joined[:1] in "，,":
            add(WARN, "字幕", f"中文 cue#{i}",
                f"脏标点(||气口残留:。，/，，/行首逗号)：{joined[:24]}——重跑 finalize_storyboard 自动清，或回 n2d-voice 重出时长清单")
    if manifest:
        for i, m in enumerate(manifest, 1):
            t = (m.get("文本") or "").strip()
            if dirty.search(t) or t[:1] in "，,":
                add(WARN, "配音", f"句#{i}",
                    f"时长清单文本脏标点：{t[:24]}——回 n2d-voice 重出(clean_text 已修)或手清")
    # 英文字幕脏标点（标点前空格 / 多空格 / 叠逗号 / 行首逗号——同套"审查即检出"，治英文文本卫生）
    if en:
        dirty_en = re.compile(r'\s[,;:!?]|\s\.(?!\.)|[ \t]{2,}|,\s*,')  # 省略号 ... 前空格合法，不抓
        for i, c in enumerate(en, 1):
            for ln in c["text"].splitlines():
                if dirty_en.search(ln) or ln.lstrip()[:1] == ",":
                    add(WARN, "字幕", f"英文 cue#{i}",
                        f"英文脏标点(标点前空格/多空格/叠逗号/行首逗号)：{ln[:30]}——重跑 finalize_storyboard 自动清")
                    break
    # 字幕 ↔ 配音时长清单 对账（文本 + 时间码）
    if manifest is not None:
        fitted_voice = has_fitted_voice(root, ep)
        if len(zh) != len(manifest):
            add(BLOCK, "字幕", ep,
                f"中文字幕条数({len(zh)}) ≠ 配音句数({len(manifest)})——字幕/配音脱节，重跑 finalize_storyboard")
        else:
            if fitted_voice:
                add(INFO, "字幕", ep,
                    "检测到 fitted 配音轨 voice_*_fitted.wav：逐句原始时长清单 start 不再代表成片时间轴，"
                    "跳过字幕起点漂移对账；以 compose/visual 的成片≈配音≈字幕末行对账为准。")
            for i, (c, m) in enumerate(zip(zh, manifest), 1):
                mt = (m.get("文本") or "").strip()
                if mt and mt.replace(" ", "") != c["text"].replace(" ", "").replace("\n", ""):
                    add(BLOCK, "字幕", f"中文 cue#{i}",
                        f"字幕文本≠配音文本｜字幕『{c['text'][:18]}』vs 配音『{mt[:18]}』")
                if (not fitted_voice) and "start" in m and abs(c["start"] - m["start"]) > TIME_TOL:
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
        if any(is_placeholder(str(m.get("占位"))) or m.get("占位") is True for m in manifest):
            add(BLOCK, "完整性", ep, "配音仍为占位音色（占位:true）——可用于出图 demo 的 rough timing；正式出视频/合成前必须换真实配音重定时")
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
        f"产物快照：配音句 {len(manifest) if manifest else 0} · 视频片段 {len(clips)} · 成片 {len(finals)}")


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


def _final_master(root, ep):
    matches = sorted(glob.glob(os.path.join(root, "合成", ep, f"成片_{ep}_*.mp4")))
    return matches[-1] if matches else None


def _has_audio(path):
    data = _ffprobe(path)
    if not data:
        return None
    return any(s.get("codec_type") == "audio" for s in data.get("streams", []))


def _clip_number_from_text(text):
    match = re.search(r"(?i)(?:^|[^0-9A-Za-z])(?:EP\d+[_-])?CLIP[_-]?0*(\d+)(?=$|[^0-9A-Za-z])", text or "")
    return int(match.group(1)) if match else None


def _storyboard_clip_numbers(clips):
    numbers = []
    for idx, clip in enumerate(clips, 1):
        num = None
        if isinstance(clip, dict):
            for key in ("id", "clip_id", "shot_id", "label"):
                num = _clip_number_from_text(str(clip.get(key) or ""))
                if num is not None:
                    break
        numbers.append(num if num is not None else idx)
    return set(numbers)


def _video_clip_groups(paths):
    groups = {}
    unknown = []
    for path in sorted(paths):
        num = _clip_number_from_text(os.path.basename(path))
        if num is None:
            unknown.append(path)
            continue
        groups.setdefault(num, []).append(path)
    return groups, unknown


def _is_split_part(path):
    return re.search(r"(?i)(?:^|[_-])part0*\d+(?=\.[^.]+$|[_-])", os.path.basename(path)) is not None


def check_storyboard_and_video(root, ep):
    """Machine-readable continuity contract + clip integrity checks."""
    sb_p = os.path.join(root, "脚本", ep, "storyboard.json")
    if not os.path.exists(sb_p):
        add(BLOCK, "故事板", sb_p, "缺机器可读 storyboard.json——下游无法稳定校验 continuity / seam_mode / end_anchor")
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
        for k in ("start_state", "end_state", "transition"):
            if k not in cont:
                add(BLOCK, "故事板", loc, f"continuity 缺字段：{k}")
        if prev_end and cont.get("start_state") != prev_end:
            add(WARN, "衔接", loc, "start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，需无缝尾帧接力时再原样继承")
        prev_end = cont.get("end_state")
        if i < len(clips):
            mode_info = normalize_seam_mode(
                cont.get("seam_mode"), cont.get("transition"),
                need_endframe=bool(cont.get("need_endframe")),
            )
            mode = str(mode_info.get("mode") or "")
            if mode_info.get("source") != "explicit":
                add(BLOCK, "接缝分类", loc, "缺显式 seam_mode；旧 transition/need_endframe 不能代替剪辑决策")
            else:
                evidence = cont.get("seam_evidence") if isinstance(cont.get("seam_evidence"), dict) else {}
                missing = list(seam_missing_evidence(mode, evidence))
                if mode == "continuous_take_relay":
                    missing = [field for field in missing if field not in {"boundary_frame", "end_state", "start_state"}]
                if missing:
                    add(BLOCK, "接缝分类", loc, f"{mode} 缺 seam_evidence：{', '.join(missing)}")
                if bool(cont.get("need_endframe")) != requires_boundary_frame(mode):
                    add(BLOCK, "接缝分类", loc, f"need_endframe 与 seam_mode={mode} 不一致")
        if needs_end_anchor(c):
            need_endframes += 1
            endp = cont.get("endframe_png") or c.get("endframe_png") or c.get("last_frame")
            full = os.path.join(root, endp) if endp and not os.path.isabs(endp) else endp
            if not endp or not os.path.exists(full):
                add(BLOCK, "尾帧", loc, "镜头需要尾锚但 endframe_png 缺失或文件不存在")
    if need_endframes:
        add(INFO, "尾帧", ep, f"本集需要镜内尾锚/连续 take 边界帧 {need_endframes} 处")

    mp4s = sorted(glob.glob(os.path.join(root, "出视频", ep, "视频", "*.mp4")))
    expected_nums = _storyboard_clip_numbers(clips)
    video_groups, unknown_mp4s = _video_clip_groups(mp4s)
    logical_nums = set(video_groups)
    missing = sorted(expected_nums - logical_nums)
    extra = sorted(logical_nums - expected_nums)
    unsplit_dupes = {
        num: paths for num, paths in video_groups.items()
        if len(paths) > 1 and not all(_is_split_part(p) for p in paths)
    }
    if mp4s and (missing or extra or unknown_mp4s or unsplit_dupes):
        parts = []
        if missing:
            parts.append("缺逻辑镜头 " + ", ".join(f"Clip_{n:02d}" for n in missing[:8]))
        if extra:
            parts.append("多出逻辑镜头 " + ", ".join(f"Clip_{n:02d}" for n in extra[:8]))
        if unknown_mp4s:
            parts.append(f"无法识别镜头号 MP4 {len(unknown_mp4s)} 个")
        if unsplit_dupes:
            parts.append("疑似重复非 part MP4 " + ", ".join(f"Clip_{n:02d}" for n in sorted(unsplit_dupes)[:8]))
        add(WARN, "视频", ep, f"逻辑 clip 与 storyboard 不一致（物理 MP4 {len(mp4s)} / 逻辑 clip {len(logical_nums)} / storyboard {len(clips)}）：{'；'.join(parts)}")
    elif mp4s and len(mp4s) != len(logical_nums):
        add(INFO, "视频", ep, f"检测到 split-part 视频：物理 MP4 {len(mp4s)} / 逻辑 clip {len(logical_nums)} / storyboard {len(clips)}")
    audio = [p for p in mp4s if _has_audio(p)]
    if audio:
        add(WARN, "原生音轨", audio[0], "clip 含原生音轨；compose 默认应丢弃。若按 opt-in 混入环境声，需确认低风险、无口型、无原生人声")
    shots_p = os.path.join(root, "脚本", ep, "镜头时长.json")
    # 仅当整集逻辑 clip 都齐了才比总长。split part 会产生多个物理 MP4，
    # 不能再用 len(mp4s)==len(clips) 判整集是否齐。
    # 拿部分对全集总时长会刷无意义的「差 N 秒」假警告。
    if os.path.exists(shots_p) and mp4s and not missing and not extra and not unknown_mp4s and not unsplit_dupes:
        try:
            target = sum(float(v) for v in json.load(open(shots_p, encoding="utf-8")).values())
            ds = [_duration(p) for p in mp4s]
            if all(d is not None for d in ds):
                total = sum(d for d in ds if d is not None)
                if abs(total - target) > 1.0:
                    final = _final_master(root, ep)
                    final_d = _duration(final) if final and has_fitted_voice(root, ep) else None
                    if final_d is not None and abs(final_d - target) <= 1.0:
                        add(INFO, "时长", ep,
                            f"源 clip 物理总长 {total:.2f}s 与镜头时长累计 {target:.2f}s 差 {abs(total-target):.2f}s；"
                            f"已检测到 fitted 配音轨且成片 {final_d:.2f}s≈锁定槽位，split 时长已由 compose Time-Warp 修正。")
                    else:
                        add(WARN, "时长", ep, f"clip 总长 {total:.2f}s 与镜头时长累计 {target:.2f}s 差 {abs(total-target):.2f}s")
        except Exception:
            pass


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
                "装库后跑 scripts/face_consistency.py 自动给每镜 vs 定妆锚点打分")
            return
    add(INFO, "一致性", ep,
        "检测到脸部识别库——跑 `python3 scripts/face_consistency.py <作品根> 第N集` 出崩脸分档报告"
        "（**自标定 flag-band**：用本作定妆组内部互相余弦当'同一人下限'地板，再分 🔴/🟡/🟢，"
        "不用写死的单一阈值；详见该脚本头注）")


def check_voice_consistency(root, ep, manifest):
    """跨集同角色音色一致性：同一「角色」在别集映射到不同 voice_id → 跨集音色漂。

    起因：角色→音色绑定历史上靠每次手动 export env，未持久化（见 n2d-voice voicemap.json）。
    manifest 现记 voice_id/音色键，于是可机检；老清单无该字段则自动跳过（向后兼容）。
    """
    def role_voice(man):
        m = {}
        for r in man or []:
            role = (r.get("角色") or "").strip()
            vid = r.get("voice_id") or r.get("音色键")
            if role and vid:
                m.setdefault(role, set()).add(vid)
        return m
    cur = role_voice(manifest)
    if not cur:
        return
    others = {}
    for vbase in ("合成", "出视频"):
        for p in glob.glob(os.path.join(root, vbase, "第*集", "配音", "时长清单.json")):
            oep = os.path.basename(os.path.dirname(os.path.dirname(p)))
            if oep == ep:
                continue
            try:
                oman = json.load(open(p, encoding="utf-8"))
            except Exception:
                continue
            for role, vids in role_voice(oman).items():
                others.setdefault(role, set()).update(vids)
    for role, vids in cur.items():
        ov = others.get(role)
        if ov and not (vids & ov):
            add(WARN, "配音一致性", f"{ep}·{role}",
                f"角色「{role}」本集音色 {sorted(vids)} 与其它集 {sorted(ov)} 不一致——跨集音色会漂；"
                f"在 设定库/voicemap.json 固定该角色音色，别靠每次手动 export env")


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
    check_face_consistency(root, ep)
    check_voice_consistency(root, ep, manifest)

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
