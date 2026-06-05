#!/usr/bin/env python3
# 配音时长 → 定稿：时长清单.json(+现有en字幕文本) → 重定时 字幕_中/英.srt + 镜头时长.json
# 用法: finalize_storyboard.py <作品根> <第N集> [gap]
import sys, os, re, json, textwrap

def _ts(t):
    h=int(t//3600); m=int((t%3600)//60); s=int(t%60); ms=int(round((t-int(t))*1000))
    if ms==1000: s+=1; ms=0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def _wrap_zh(text, width=19):
    lines=[]; cur=""
    punct = "，。！？、；：——…"
    for idx,ch in enumerate(text):
        cur += ch
        next_ch = text[idx + 1] if idx + 1 < len(text) else ""
        if len(cur) >= width and ch in punct:
            lines.append(cur); cur=""
        elif len(cur) >= width and next_ch in punct:
            continue
        elif len(cur) >= width:
            lines.append(cur); cur=""
    if cur:
        lines.append(cur)
    return "\n".join(lines)

def _wrap_en(text, width=42):
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)) or text

def build(manifest, en_texts, gap=0.4):
    zh=[]; en=[]; shots={}
    # 优先消费 render_voice 写入的真实时间轴(start/end/gap_after)；旧 manifest 无则按同一套 HOOK_GAP 模型重建
    if manifest and all('start' in r and 'end' in r for r in manifest):
        spans=[(float(r['start']), float(r['end']), float(r.get('gap_after',0.0))) for r in manifest]
    else:
        HG={'end':1.0,'climax':0.7,'hook':0.6}   # 与 render_voice 默认 GAP_END/CLIMAX/HOOK 一致
        spans=[]; t=0.0; last=len(manifest)-1
        for i,r in enumerate(manifest):
            d=float(r["时长"]); g=0.0 if i==last else HG.get(r.get("钩子","") or "", gap)  # 末句不留拍
            spans.append((t, t+d, g)); t=t+d+g
    for i,row in enumerate(manifest):
        start,end,gap_after=spans[i]
        zh.append(f"{i+1}\n{_ts(start)} --> {_ts(end)}\n{_wrap_zh(row['文本'])}\n")
        etxt=en_texts[i] if i<len(en_texts) else ""
        en.append(f"{i+1}\n{_ts(start)} --> {_ts(end)}\n{_wrap_en(etxt)}\n")
        sh=row.get("镜头","")
        shots[sh]=shots.get(sh,0.0)+(end-start)+gap_after  # 镜头占屏=台词时长+其后留拍；∑镜头 == voice.wav 时长
    shots={k:round(v,3) for k,v in shots.items()}
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
    # 占位闸门：占位音色时长是估算值（与真实配音差 20~40%），定稿到镜头时长后会污染故事板 Clip 时长 → 出视频按错时长生成 → 大返工。
    # render_voice 已把占位句标 "占位":true；这里默认拒绝定稿，仅 rough preview 可用 FINALIZE_ALLOW_PLACEHOLDER=1 放行。
    ph=[r.get('idx',i) for i,r in enumerate(manifest) if r.get('占位')]
    if ph and os.environ.get('FINALIZE_ALLOW_PLACEHOLDER','')!='1':
        print('⛔ 拒绝定稿：本集配音仍是占位音色（'+str(len(ph))+'/'+str(len(manifest))+' 句，idx='+','.join(map(str,ph[:10]))+('…' if len(ph)>10 else '')+'）。')
        print('   占位时长是估算值，定稿后会锁进镜头时长.json/故事板 Clip 时长 → 出视频按错时长生成 → 返工。')
        print('   出图/出视频前务必：/n2d-voice '+root+' '+ep+' 换真实配音（CosyVoice/克隆/MiniMax）重跑，再回跑本步。')
        print('   仅想跑通时间轴 rough preview：FINALIZE_ALLOW_PLACEHOLDER=1 python3 finalize_storyboard.py ...（产物不可用于正式出视频）')
        sys.exit(2)
    en_texts=_parse_srt_texts(os.path.join(root,'脚本',ep,'字幕_英文.srt'))
    zh_srt,en_srt,shots=build(manifest,en_texts,gap)
    open(os.path.join(root,'脚本',ep,'字幕_中文.srt'),'w',encoding='utf-8').write(zh_srt)
    open(os.path.join(root,'脚本',ep,'字幕_英文.srt'),'w',encoding='utf-8').write(en_srt)
    json.dump(shots, open(os.path.join(root,'脚本',ep,'镜头时长.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"定稿: {len(manifest)} 句重定时 → 字幕_中/英.srt；{len(shots)} 镜 → 镜头时长.json")

if __name__=='__main__': main()
