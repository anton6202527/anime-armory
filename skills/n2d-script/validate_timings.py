#!/usr/bin/env python3
# 时长一致性守门人：核对配音→字幕→镜头时长这条链是否对齐（治"成片时长对不上/字幕错位/镜头时长漂"）。
# 用法: validate_timings.py <作品根> <第N集> [--tol 0.5] [--target-seconds N | --no-target]
#       不给 --target-seconds 时默认从 _设置.md「拆集节奏」预设自动取软节奏目标做集长 WARN（--no-target 关闭）。
# 退出码: 0=全过 / 1=有硬不一致或缺文件（可接 CI）。所有检查仅读取，不改文件。
import sys, os, re, json, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'n2d', '_lib'))
from n2d_settings import is_native_av, get_setting  # 制作模式判定 + 选择点读取（单一真值源）
from n2d_route import placeholder_indices, voiceover_fingerprint  # 占位判定 + 配音源指纹（单一真值源）

# 拆集节奏 → 软节奏目标秒（仅用于 WARN，不作硬上下限；旧键「单集时长」兼容读取）。
# 「前长后短」第1集与其余集不同档：用 (ep1_target, rest_target)；其余预设第1集同其余集。
_DURATION_PRESET_TARGETS = {
    "前长后短": (150.0, 90.0),   # 第1集 soft 150 / 其余集 soft 90
    "均衡": (90.0, 90.0),        # soft 90
    "快节奏": (60.0, 60.0),      # soft 60
    "长集": (150.0, 150.0),      # soft 150
}
_EP_NUM_RE = re.compile(r"\d+")


def _episode_is_first(ep):
    m = _EP_NUM_RE.search(str(ep or ""))
    return m is not None and int(m.group(0)) == 1


def episode_target_seconds(root, ep):
    """从 _设置.md「拆集节奏」自动取本集软节奏目标秒；取不到返回 None（不引入新行为，向后兼容）。

    支持：预设名（前长后短/均衡/快节奏/长集，取兼容软秒数；前长后短第1集单独档）；
    参数化覆盖 `自定义(90s)` / `快节奏(85s)` 取括号内显式秒；`(60-120)` 取软范围中点。
    显式 --target-seconds 仍优先（main 里若已给就不调本函数）。"""
    raw = (get_setting(root, "拆集节奏", "") or "").strip()
    if not raw:
        raw = "前长后短"  # 内部默认（见 n2d/references/选择点与偏好.md）
    # 括号内显式参数优先（半/全角括号）：单值 90s 或区间 60-120。
    m = re.search(r"[（(]([^（）()]+)[)）]", raw)
    if m:
        inner = m.group(1)
        rng = re.findall(r"\d+(?:\.\d+)?", inner)
        if len(rng) >= 2:
            return (float(rng[0]) + float(rng[1])) / 2.0
        if len(rng) == 1:
            return float(rng[0])
    for name, (ep1, rest) in _DURATION_PRESET_TARGETS.items():
        if name in raw:
            return ep1 if _episode_is_first(ep) else rest
    return None

def validate_storyboard_contract(root, ep):
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'validate_storyboard_contract.py')
    proc = subprocess.run([sys.executable, script, root, ep], capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode

def ffdur(p):
    try:
        out = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p],
                             capture_output=True, text=True).stdout.strip()
        return float(out)
    except Exception:
        return None

def srt_blocks(path):
    if not os.path.exists(path): return []
    return [b for b in re.split(r'\n\s*\n', open(path,encoding='utf-8').read().strip()) if b.strip()]

def _srt_text(block):
    ls = [l for l in block.splitlines() if l.strip()]
    return " ".join(ls[2:]) if len(ls) >= 3 else ""

def _is_placeholder_en_blocks(blocks):
    if not blocks:
        return False
    joined = " ".join(_srt_text(b) for b in blocks).strip().lower()
    markers = (
        "todo",
        "placeholder",
        "待精修",
        "待填写",
        "english subtitles for overseas platforms",
        "timed to the storyboard",
    )
    return bool(joined) and any(m in joined for m in markers)

def srt_last_end(path):
    last = None
    for b in srt_blocks(path):
        m = re.search(r'-->\s*(\d+):(\d+):(\d+)[,.](\d+)', b)
        if m:
            g = list(map(int, m.groups())); last = g[0]*3600+g[1]*60+g[2]+g[3]/1000.0
    return last

# 软节奏偏差容忍（∑镜头时长 偏离意图超此比例即 WARN，不硬拦）。默认 15%。
TARGET_DEVIATION_TOL = 0.15

def target_deviation_warn(shots_total, target_seconds, tol=TARGET_DEVIATION_TOL):
    """∑镜头时长 vs 软节奏意图：偏离超 tol 比例 → 返回一条 WARN 文案，否则 None。
    仅在显式给了正的 target 时生效（不给→无新行为，向后兼容）；不作为集长硬闸门。"""
    if target_seconds is None or target_seconds <= 0:
        return None
    dev = abs(shots_total - target_seconds) / target_seconds
    if dev > tol:
        sign = '长' if shots_total > target_seconds else '短'
        return (f"∑镜头时长 {shots_total:.2f}s 偏离软节奏意图 {target_seconds:.2f}s 达 {dev*100:.0f}%"
                f"（>{tol*100:.0f}% 容忍·偏{sign}）→ 仅作节奏 WARN；优先复核冲突→爽点→钩子闭环，必要时调台词篇幅或节奏目标")
    return None

def _fit_max_stretch():
    """逐镜头真音超槽容忍倍数：与 n2d-compose fit_voice_to_clips 共用同一环境变量/默认值
    （FIT_MAX_STRETCH，默认 1.25），保证「分镜阶段预检」与「合成阶段拟合」判定口径一致。"""
    try:
        return float(os.environ.get("FIT_MAX_STRETCH", "1.25"))
    except ValueError:
        return 1.25


def per_shot_overflow(man, shots, max_stretch=1.25):
    """逐镜头真音 vs 锁定槽位×max_stretch 预检（复刻 n2d-compose fit_voice_to_clips.plan 的 overflow 判定）。

    man:   时长清单.json 列表（逐句 dict，含 镜头/时长/gap_after）。
    shots: 镜头时长.json {镜头键: 锁定槽位秒}。
    返回 [(镜头, 真音秒, 槽位秒), ...]：真音(按镜头聚合 ∑(时长+gap)) > 槽位×max_stretch 的镜头。
    合计校验(∑clip≈∑镜头)会让单镜 +Δ 与另一镜 -Δ 相互抵消而漏过，这里逐镜兜住。纯函数·可测。"""
    real = {}
    for r in man:
        if not isinstance(r, dict):
            continue
        sh = r.get('镜头')
        if not sh:
            continue
        real[sh] = real.get(sh, 0.0) + float(r.get('时长', 0) or 0) + float(r.get('gap_after', 0) or 0)
    out = []
    for sh, slot in shots.items():
        try:
            slot = float(slot)
        except (TypeError, ValueError):
            continue
        r = real.get(sh)
        if r is None or slot <= 0:
            continue
        if r > slot * max_stretch:
            out.append((sh, round(r, 3), round(slot, 3)))
    out.sort(key=lambda x: str(x[0]))
    return out


def _validate_native_av(root, ep, shots_p, tol, target=None):
    """原生音画对账：无配音清单，改核 storyboard ∑clip.duration ≈ ∑镜头时长（finalize 从脚本推的）。
    返回退出码（0=过 / 1=硬不一致或缺件）。字幕走成片后 whisperx 词级对齐，本步不校验。"""
    fails=[]; warns=[]; oks=[]
    print(f"=== 时长一致性 {ep}（原生音画·tol={tol}s）===")
    if not os.path.exists(shots_p):
        print("  ⛔ 缺 镜头时长.json（原生音画下应由 finalize_storyboard 从 storyboard 推出——先跑 n2d-script 阶段2 分镜定稿）")
        return 1
    shots = json.load(open(shots_p,encoding='utf-8'))
    st = sum(float(v) for v in shots.values())
    tw = target_deviation_warn(st, target)
    if tw: warns.append(tw)
    sb_p = os.path.join(root,'脚本',ep,'storyboard.json')
    if os.path.exists(sb_p):
        try:
            sb = json.load(open(sb_p,encoding='utf-8'))
            cd = sum(float(c.get('duration',0)) for c in sb.get('clips',[]))
        except Exception as e:
            cd = None; warns.append(f"storyboard.json 不可解析（{e}）")
        if cd is not None:
            if abs(cd - st) > tol:
                fails.append(f"storyboard.json ∑clip.duration {cd:.2f}s ≠ 镜头时长累计 {st:.2f}s → finalize 未按 storyboard 重出，重跑 finalize_storyboard")
            else:
                oks.append(f"∑clip.duration {cd:.2f}s ≈ 镜头时长累计 {st:.2f}s")
    else:
        warns.append("storyboard.json 不存在（阶段2 未定稿）——无法核对 clip 时长")
    warns.append("原生音画：字幕未在本步校验，成片后用 whisperx 对原生台词做词级对齐")
    for s in oks:   print(f"  ✅ {s}")
    for s in warns: print(f"  ⚠️  {s}")
    for s in fails: print(f"  ⛔ {s}")
    if fails:
        print(f"\n{len(fails)} 处硬不一致 → 修复后再进出图/出视频/合成。"); return 1
    print("\n时长链一致（原生音画）。"); return 0


def main():
    if len(sys.argv) < 3:
        sys.exit('用法: validate_timings.py <作品根> <第N集> [--tol 0.5]')
    root, ep = sys.argv[1], sys.argv[2]
    tol = 0.5
    if '--tol' in sys.argv:
        i = sys.argv.index('--tol')
        if i + 1 >= len(sys.argv):
            sys.exit('⛔ --tol 后缺数值，例: --tol 0.5')
        try:
            tol = float(sys.argv[i + 1])
        except ValueError:
            sys.exit(f'⛔ --tol 数值无效: {sys.argv[i + 1]}')
    # 集长对账：显式 --target-seconds 优先；否则从 _设置.md「拆集节奏」预设自动取软节奏目标
    # （--no-target 显式关闭自动取）。∑镜头时长 偏离软目标超 15% 仅 WARN，不硬拦。
    target = None
    if '--target-seconds' in sys.argv:
        i = sys.argv.index('--target-seconds')
        if i + 1 >= len(sys.argv):
            sys.exit('⛔ --target-seconds 后缺数值，例: --target-seconds 90')
        try:
            target = float(sys.argv[i + 1])
        except ValueError:
            sys.exit(f'⛔ --target-seconds 数值无效: {sys.argv[i + 1]}')
    elif '--no-target' not in sys.argv:
        target = episode_target_seconds(root, ep)  # 自动取（取不到 → None → 无新行为）
    # 配音一律落 合成/（render_voice 与制作模式无关地写 合成/，见 2026 出视频↔合成分家）；出视频/ 为已废弃历史路径，仅防御性兜底探测
    vbase = next((b for b in ('合成','出视频') if os.path.isfile(os.path.join(root,b,ep,'配音','时长清单.json'))), '合成')
    vd  = os.path.join(root,vbase,ep,'配音')
    man_p = os.path.join(vd,'时长清单.json')
    voice = os.path.join(vd,'voice_zh.wav')
    zh_srt= os.path.join(root,'脚本',ep,'字幕_中文.srt')
    en_srt= os.path.join(root,'脚本',ep,'字幕_英文.srt')
    shots_p=os.path.join(root,'脚本',ep,'镜头时长.json')
    contract_code = validate_storyboard_contract(root, ep)

    fails=[]; warns=[]; oks=[]
    if not os.path.exists(man_p):
        # 原生音画：说话镜由视频后端一次出同步音画，没有逐句配音清单——改走 storyboard 驱动对账，不误报"先 n2d-voice"。
        if is_native_av(root):
            native_code = _validate_native_av(root, ep, shots_p, tol, target)
            sys.exit(1 if contract_code or native_code else 0)
        print(f"⛔ 缺 {man_p}（先 n2d-voice）"); sys.exit(1)
    man = json.load(open(man_p,encoding='utf-8'))
    n = len(man)

    # 占位提示（非硬错，但下游会被闸门拦）
    ph = placeholder_indices(man)
    if ph: warns.append(f"占位配音 {len(ph)}/{n} 句——正式出视频前须换真实配音重跑")

    # 0) 配音源指纹：voiceover.txt 在配音之后是否被改（改词/插句/删句）→ 时长清单/字幕/镜头时长会全部过期。
    #    delete_shot 的强制 gate 对账只覆盖删镜；改词/插句靠这条指纹兜底。
    meta_p = os.path.join(vd, '时长清单.meta.json')
    vo_p   = os.path.join(root, '脚本', ep, 'voiceover.txt')
    if os.path.exists(vo_p):
        if os.path.exists(meta_p):
            try:
                recorded = (json.load(open(meta_p, encoding='utf-8')) or {}).get('voiceover_fingerprint')
            except Exception:
                recorded = None
            current = voiceover_fingerprint(vo_p)
            if recorded and current and recorded != current:
                fails.append("voiceover.txt 在配音后被改动（台词指纹失配）→ 时长清单/字幕/镜头时长已过期，重跑 n2d-voice 再回跑 finalize_storyboard")
            elif recorded and current:
                oks.append("voiceover 指纹一致（配音后台词未改）")
        else:
            warns.append("无 时长清单.meta.json（旧配音产物或占位轨）——无法核对配音后 voiceover 改动，建议重跑 n2d-voice 生成指纹")

    # 1) ∑(时长+gap) ≈ voice_zh.wav 实测
    man_total = sum(float(r.get('时长',0))+float(r.get('gap_after',0)) for r in man)
    vdur = ffdur(voice) if os.path.exists(voice) else None
    if vdur is None:
        warns.append(f"voice_zh.wav 不存在或无法探测时长（{voice}）")
    elif abs(man_total - vdur) > tol:
        fails.append(f"时长清单累计 {man_total:.2f}s ≠ voice_zh.wav 实测 {vdur:.2f}s（差 {abs(man_total-vdur):.2f}s）→ 配音轨与清单不同步，重跑 n2d-voice")
    else:
        oks.append(f"清单累计 {man_total:.2f}s ≈ 配音轨 {vdur:.2f}s")

    # 2) voice 时长 ≈ 中文字幕末行 end
    last = srt_last_end(zh_srt)
    base = vdur if vdur is not None else man_total
    if last is None:
        warns.append(f"字幕_中文.srt 不存在或无时间码（先 finalize_storyboard）")
    elif abs(last - base) > tol:
        fails.append(f"字幕_中文.srt 末行 end {last:.2f}s ≠ 配音 {base:.2f}s → 字幕未按最新配音重定时，重跑 finalize_storyboard")
    else:
        oks.append(f"中文字幕末行 {last:.2f}s ≈ 配音 {base:.2f}s")

    # 3) ∑镜头时长 ≈ voice 时长
    st = None
    if os.path.exists(shots_p):
        shots = json.load(open(shots_p,encoding='utf-8'))
        st = sum(float(v) for v in shots.values())
        if abs(st - base) > tol:
            fails.append(f"镜头时长.json 累计 {st:.2f}s ≠ 配音 {base:.2f}s → 故事板 Clip 时长会错，重跑 finalize_storyboard")
        else:
            oks.append(f"镜头时长累计 {st:.2f}s ≈ 配音 {base:.2f}s")
        tw = target_deviation_warn(st, target)
        if tw: warns.append(tw)
    else:
        warns.append("镜头时长.json 不存在（阶段2 未定稿）")

    # 3.5) ∑clip.duration(storyboard.json) ≈ ∑镜头时长 —— 治"手填 duration 与配音驱动时长漂"
    sb_p = os.path.join(root,'脚本',ep,'storyboard.json')
    if os.path.exists(sb_p) and st is not None:
        try:
            sb = json.load(open(sb_p,encoding='utf-8'))
            cd = sum(float(c.get('duration',0)) for c in sb.get('clips',[]))
        except Exception as e:
            cd = None; warns.append(f"storyboard.json 不可解析（{e}）")
        if cd is not None:
            if abs(cd - st) > tol:
                fails.append(f"storyboard.json ∑clip.duration {cd:.2f}s ≠ 镜头时长累计 {st:.2f}s → Clip 时长手填臆造/未随配音更新，按 ∑所含镜头时长 回填 duration")
            else:
                oks.append(f"∑clip.duration {cd:.2f}s ≈ 镜头时长累计 {st:.2f}s")

    # 3.6) 逐镜头真音超槽（与 n2d-compose fit_voice_to_clips 同 max_stretch 口径）——治"总长对得上但单镜溢出"：
    #      3)/3.5) 仅核 ∑，A 镜 +Δ 与 B 镜 -Δ 能相互抵消而通过，却会在 compose 拟合阶段 A 镜判 overflow(exit 2)返工。
    #      在分镜阶段就逐镜预检，超限即 FAIL（与 compose 同等拦截力度），让用户在出图/出视频前调台词或镜头时长。
    #      占位轨不预检：compose 拟合也只对真音；占位下槽位由占位时长推出，不会真溢出（避免对占位噪报）。
    if not ph and st is not None and os.path.exists(shots_p):
        ms = _fit_max_stretch()
        ov = per_shot_overflow(man, shots, ms)
        if ov:
            head = "；".join(f"{sh} 真音{real:.2f}s>槽位{slot:.2f}s×{ms:g}" for sh, real, slot in ov[:5])
            more = f"（共 {len(ov)} 镜，余略）" if len(ov) > 5 else ""
            fails.append(f"逐镜头真音超槽 {len(ov)} 处：{head}{more} → compose 拟合会判 overflow(exit 2)返工；"
                         f"分镜阶段先调这些镜台词篇幅或 镜头时长.json 槽位（与 compose 同 max_stretch={ms:g} 口径）")
        else:
            oks.append(f"逐镜头真音均未超槽位×{ms:g}（与 compose 拟合同口径）")

    # 4) manifest 句数 == 英文字幕块数（delete_shot 未同步删 EN 会错位）
    enb = srt_blocks(en_srt)
    if _is_placeholder_en_blocks(enb):
        enb = []
    if enb and len(enb) != n:
        fails.append(f"时长清单 {n} 句 ≠ 字幕_英文.srt {len(enb)} 块 → 删镜未同步删 EN，字幕将错位（用 delete_shot.py 或重跑 finalize）")
    elif enb:
        oks.append(f"配音句数 {n} == 英文字幕块数 {len(enb)}")

    # 5) 每句 line_wav 存在
    miss = [r.get('line_wav') for r in man if r.get('line_wav') and not os.path.exists(os.path.join(vd, r['line_wav']))]
    if miss:
        warns.append(f"{len(miss)} 个 line_*.wav 缺失（如 {miss[0]}）——重拼配音轨前先补")

    if contract_code:
        fails.append("storyboard 契约校验未通过")

    print(f"=== 时长一致性 {ep}（tol={tol}s）===")
    for s in oks:   print(f"  ✅ {s}")
    for s in warns: print(f"  ⚠️  {s}")
    for s in fails: print(f"  ⛔ {s}")
    if fails:
        print(f"\n{len(fails)} 处硬不一致 → 修复后再进出图/出视频/合成。"); sys.exit(1)
    print("\n时长链一致。" + ("（有占位/缺件提示，见上）" if warns else "")); sys.exit(0)

if __name__=='__main__': main()
