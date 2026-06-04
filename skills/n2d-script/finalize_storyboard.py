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
