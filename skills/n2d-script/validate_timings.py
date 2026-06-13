#!/usr/bin/env python3
# 时长一致性守门人：核对配音→字幕→镜头时长这条链是否对齐（治"成片时长对不上/字幕错位/镜头时长漂"）。
# 用法: validate_timings.py <作品根> <第N集> [--tol 0.5]
# 退出码: 0=全过 / 1=有硬不一致或缺文件（可接 CI）。所有检查仅读取，不改文件。
import sys, os, re, json, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'n2d', '_lib'))
from n2d_settings import is_native_av  # 制作模式判定单一真值源
from n2d_route import placeholder_indices, voiceover_fingerprint  # 占位判定 + 配音源指纹（单一真值源）

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

def _validate_native_av(root, ep, shots_p, tol):
    """原生音画对账：无配音清单，改核 storyboard ∑clip.duration ≈ ∑镜头时长（finalize 从脚本推的）。
    返回退出码（0=过 / 1=硬不一致或缺件）。字幕走成片后 whisperx 词级对齐，本步不校验。"""
    fails=[]; warns=[]; oks=[]
    print(f"=== 时长一致性 {ep}（原生音画·tol={tol}s）===")
    if not os.path.exists(shots_p):
        print("  ⛔ 缺 镜头时长.json（原生音画下应由 finalize_storyboard 从 storyboard 推出——先跑 n2d-script 阶段2 分镜定稿）")
        return 1
    shots = json.load(open(shots_p,encoding='utf-8'))
    st = sum(float(v) for v in shots.values())
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
    warns.append("原生音画：字幕未在本步校验，成片后用 whisperx 对原生台词做词级对齐（参考 mv-lyric-sync）")
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
    # 配音一律落 合成/（render_voice 与制作模式无关地写 合成/，见 2026 出视频↔合成分家）；出视频/ 为已废弃历史路径，仅防御性兜底探测
    vbase = next((b for b in ('合成','出视频') if os.path.isfile(os.path.join(root,b,ep,'配音','时长清单.json'))), '合成')
    vd  = os.path.join(root,vbase,ep,'配音')
    man_p = os.path.join(vd,'时长清单.json')
    voice = os.path.join(vd,'voice_zh.wav')
    zh_srt= os.path.join(root,'脚本',ep,'字幕_中文.srt')
    en_srt= os.path.join(root,'脚本',ep,'字幕_英文.srt')
    shots_p=os.path.join(root,'脚本',ep,'镜头时长.json')

    fails=[]; warns=[]; oks=[]
    if not os.path.exists(man_p):
        # 原生音画：说话镜由视频后端一次出同步音画，没有逐句配音清单——改走 storyboard 驱动对账，不误报"先 n2d-voice"。
        if is_native_av(root):
            sys.exit(_validate_native_av(root, ep, shots_p, tol))
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

    print(f"=== 时长一致性 {ep}（tol={tol}s）===")
    for s in oks:   print(f"  ✅ {s}")
    for s in warns: print(f"  ⚠️  {s}")
    for s in fails: print(f"  ⛔ {s}")
    if fails:
        print(f"\n{len(fails)} 处硬不一致 → 修复后再进出图/出视频/合成。"); sys.exit(1)
    print("\n时长链一致。" + ("（有占位/缺件提示，见上）" if warns else "")); sys.exit(0)

if __name__=='__main__': main()
