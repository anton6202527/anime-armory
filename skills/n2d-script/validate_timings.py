#!/usr/bin/env python3
# 时长一致性守门人：核对配音→字幕→镜头时长这条链是否对齐（治"成片时长对不上/字幕错位/镜头时长漂"）。
# 用法: validate_timings.py <作品根> <第N集> [--tol 0.5]
# 退出码: 0=全过 / 1=有硬不一致或缺文件（可接 CI）。所有检查仅读取，不改文件。
import sys, os, re, json, subprocess

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

def srt_last_end(path):
    last = None
    for b in srt_blocks(path):
        m = re.search(r'-->\s*(\d+):(\d+):(\d+)[,.](\d+)', b)
        if m:
            g = list(map(int, m.groups())); last = g[0]*3600+g[1]*60+g[2]+g[3]/1000.0
    return last

def main():
    root, ep = sys.argv[1], sys.argv[2]
    tol = float(sys.argv[sys.argv.index('--tol')+1]) if '--tol' in sys.argv else 0.5
    vd  = os.path.join(root,'出视频',ep,'配音')
    man_p = os.path.join(vd,'时长清单.json')
    voice = os.path.join(vd,'voice_zh.wav')
    zh_srt= os.path.join(root,'脚本',ep,'字幕_中文.srt')
    en_srt= os.path.join(root,'脚本',ep,'字幕_英文.srt')
    shots_p=os.path.join(root,'脚本',ep,'镜头时长.json')

    fails=[]; warns=[]; oks=[]
    if not os.path.exists(man_p):
        print(f"⛔ 缺 {man_p}（先 /n2d-voice）"); sys.exit(1)
    man = json.load(open(man_p,encoding='utf-8'))
    n = len(man)

    # 占位提示（非硬错，但下游会被闸门拦）
    ph = [r.get('idx',i) for i,r in enumerate(man) if r.get('占位')]
    if ph: warns.append(f"占位配音 {len(ph)}/{n} 句——正式出视频前须换真实配音重跑")

    # 1) ∑(时长+gap) ≈ voice_zh.wav 实测
    man_total = sum(float(r.get('时长',0))+float(r.get('gap_after',0)) for r in man)
    vdur = ffdur(voice) if os.path.exists(voice) else None
    if vdur is None:
        warns.append(f"voice_zh.wav 不存在或无法探测时长（{voice}）")
    elif abs(man_total - vdur) > tol:
        fails.append(f"时长清单累计 {man_total:.2f}s ≠ voice_zh.wav 实测 {vdur:.2f}s（差 {abs(man_total-vdur):.2f}s）→ 配音轨与清单不同步，重跑 /n2d-voice")
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
    if os.path.exists(shots_p):
        shots = json.load(open(shots_p,encoding='utf-8'))
        st = sum(float(v) for v in shots.values())
        if abs(st - base) > tol:
            fails.append(f"镜头时长.json 累计 {st:.2f}s ≠ 配音 {base:.2f}s → 故事板 Clip 时长会错，重跑 finalize_storyboard")
        else:
            oks.append(f"镜头时长累计 {st:.2f}s ≈ 配音 {base:.2f}s")
    else:
        warns.append("镜头时长.json 不存在（阶段2 未定稿）")

    # 4) manifest 句数 == 英文字幕块数（delete_shot 未同步删 EN 会错位）
    enb = srt_blocks(en_srt)
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
