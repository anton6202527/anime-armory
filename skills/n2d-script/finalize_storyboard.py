#!/usr/bin/env python3
# 配音时长 → 定稿：时长清单.json(+现有en字幕文本) → 重定时 字幕_中文.srt[+字幕_英文.srt] + 镜头时长.json
# 用法: finalize_storyboard.py <作品根> <第N集> [gap]
#   [gap] 仅对无 start/end 的旧清单回退路径生效；render_voice 现恒写 start/end/gap_after，新清单忽略它。
#   字幕语言看 ../_偏好约定.md 的「字幕语言」选择点：默认仅中文；中英双语/仅英文用 SUB_LANG=zh,en（或 en）开启。
#   未设 SUB_LANG 时：已存在非占位 字幕_英文.srt 译文就一并重定时，否则只产中文。
import sys, os, re, json, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
from n2d_route import placeholder_indices, manifest_path  # 占位判定/清单定位单一真值源
from n2d_settings import is_native_av  # 制作模式判定单一真值源（替代本地窄正则）

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

def _clean_punct(t):
    # 与 n2d-voice/voice_text.clean_text 标点清洗同源（仅标点·manifest 文本已无 emoji/钩子）：
    # 治 || 气口残留的 。，/，，/行首逗号，使重跑 finalize 即自动洗净字幕（不靠人记得扫）
    t=re.sub(r'[，,]\s*[，,]+','，',t)                          # 叠逗号
    t=re.sub(r'([。！？…—；：、》」』）])\s*[，,]\s*',r'\1',t)   # 句末标点后多余逗号(治「。，」)
    t=re.sub(r'^\s*[，,]\s*','',t)                            # 行首逗号
    return t

def _clean_en(t):
    # 英文字幕标点卫生（与中文同思路·生成即清洗）：标点前空格、叠逗号、行首逗号、多空格
    # 注意：省略号「...」前的空格是合法停顿(如 "eye) ...this")，不动——只清单个句末点前空格
    t=re.sub(r'\s+([,;:!?])',r'\1',t)                         # , ; : ! ? 前不留空格
    t=re.sub(r'\s+\.(?!\.)',r'.',t)                           # 单个句号前空格(不碰省略号 ...)
    t=re.sub(r',\s*,+',',',t)                                 # 叠逗号
    t=re.sub(r'^\s*,\s*','',t)                                # 行首逗号
    t=re.sub(r'[ \t]{2,}',' ',t)                              # 多空格
    return t.strip()

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
        zh.append(f"{i+1}\n{_ts(start)} --> {_ts(end)}\n{_wrap_zh(_clean_punct(row.get('文本','')))}\n")
        etxt=en_texts[i] if i<len(en_texts) else ""
        en.append(f"{i+1}\n{_ts(start)} --> {_ts(end)}\n{_wrap_en(_clean_en(etxt))}\n")
        sh=row.get("镜头","")
        shots[sh]=shots.get(sh,0.0)+(end-start)+gap_after  # 镜头占屏=台词时长+其后留拍；∑镜头 == voice.wav 时长
    shots={k:round(v,3) for k,v in shots.items()}
    return "\n".join(zh), "\n".join(en), shots

def _clip_duration(c):
    for k in ('duration', 'duration_sec', '时长', 'seconds'):
        v = c.get(k)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            m = re.search(r'\d+(?:\.\d+)?', v)
            if m:
                return float(m.group(0))
    return None

def build_from_storyboard(clips):
    # 原生音画：镜头时长来自脚本规划的 storyboard clips[].duration（不读配音清单）。
    # 一 clip 一条，∑ 与 ∑clip.duration 一致，供 validate_timings 对账与下游读取。
    shots = {}
    for c in clips:
        if not isinstance(c, dict):
            continue
        dur = _clip_duration(c)
        if dur is None:
            continue
        key = str(c.get('镜头') or c.get('id') or c.get('label') or f'clip{len(shots)+1}')
        shots[key] = round(shots.get(key, 0.0) + dur, 3)
    return shots

def _parse_srt_texts(path):
    out=[]
    if not os.path.exists(path): return out
    for b in re.split(r'\n\s*\n', open(path,encoding='utf-8').read().strip()):
        ls=[l for l in b.splitlines() if l.strip()]
        if len(ls)>=3: out.append(' '.join(ls[2:]))
    return out

def _is_placeholder_en_texts(texts):
    if not texts:
        return False
    joined = " ".join(texts).strip().lower()
    if not joined:
        return True
    markers = (
        "todo",
        "placeholder",
        "待精修",
        "待填写",
        "english subtitles for overseas platforms",
        "timed to the storyboard",
    )
    return any(m in joined for m in markers)

def main():
    if len(sys.argv) < 3:
        print("usage: finalize_storyboard.py <作品根> <第N集> [gap]", file=sys.stderr)
        return 2
    root, ep = sys.argv[1], sys.argv[2]
    gap = float(sys.argv[3]) if len(sys.argv)>3 else 0.4
    # 时长清单一律落 合成/（render_voice 与制作模式无关；出视频/ 为已废弃历史路径的兜底）——走 n2d_route 单一真值源
    man_p = manifest_path(root, ep)
    native_av = is_native_av(root)
    if not man_p:
        # 原生音画模式：说话镜由视频后端一次出同步音画，没有逐句配音清单——改从 storyboard 脚本时长定稿，不崩。
        if native_av:
            sb_p = os.path.join(root,'脚本',ep,'storyboard.json')
            if not os.path.isfile(sb_p):
                print('⛔ 原生音画模式但缺 storyboard.json，无法从脚本推镜头时长——请先 /n2d-script 阶段2 分镜设计。'); sys.exit(2)
            clips = (json.load(open(sb_p,encoding='utf-8')) or {}).get('clips') or []
            shots = build_from_storyboard(clips)
            if not shots:
                print('⛔ 原生音画模式：storyboard.json clips 缺 duration，无法定稿镜头时长——分镜设计时按脚本规划填 Clip duration。'); sys.exit(2)
            json.dump(shots, open(os.path.join(root,'脚本',ep,'镜头时长.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
            print(f"原生音画定稿: 从 storyboard 取 {len(shots)} 镜时长 → 镜头时长.json。")
            print("  说话镜台词由视频后端原生生成，字幕请用 whisperx 对成片词级对齐（参考 mv-lyric-sync），不在本步按配音重定时。")
            sys.exit(0)
        print('⛔ 缺 时长清单.json（合成/'+ep+'/配音/ 或 出视频/'+ep+'/配音/）——请先 /n2d-voice 配音。'); sys.exit(2)
    manifest=json.load(open(man_p,encoding='utf-8'))
    # 占位闸门：占位音色时长是估算值（与真实配音差 20~40%），定稿到镜头时长后会污染故事板 Clip 时长 → 出视频按错时长生成 → 大返工。
    # render_voice 已把占位句标 "占位":true；这里默认拒绝定稿，仅 rough preview 可用 FINALIZE_ALLOW_PLACEHOLDER=1 放行。
    ph=placeholder_indices(manifest)
    # 原生音画模式下，配音清单只覆盖旁白/非说话镜；占位不作硬闸（说话镜不靠它定时）。
    if ph and not native_av and os.environ.get('FINALIZE_ALLOW_PLACEHOLDER','')!='1':
        print('⛔ 拒绝定稿：本集配音仍是占位音色（'+str(len(ph))+'/'+str(len(manifest))+' 句，idx='+','.join(map(str,ph[:10]))+('…' if len(ph)>10 else '')+'）。')
        print('   占位时长是估算值，定稿后会锁进镜头时长.json/故事板 Clip 时长 → 出视频按错时长生成 → 返工。')
        print('   出图/出视频前务必：/n2d-voice '+root+' '+ep+' 换真实配音（CosyVoice/克隆/MiniMax）重跑，再回跑本步。')
        print('   仅想跑通时间轴 rough preview：FINALIZE_ALLOW_PLACEHOLDER=1 python3 finalize_storyboard.py ...（产物不可用于正式出视频）')
        sys.exit(2)
    en_path=os.path.join(root,'脚本',ep,'字幕_英文.srt')
    en_texts=_parse_srt_texts(en_path)
    placeholder_en = _is_placeholder_en_texts(en_texts)
    if placeholder_en:
        en_texts=[]
    zh_srt,en_srt,shots=build(manifest,en_texts,gap)
    open(os.path.join(root,'脚本',ep,'字幕_中文.srt'),'w',encoding='utf-8').write(zh_srt)
    # 字幕语言是投放选择(见 ../_偏好约定.md)，不写死：默认仅中文(国内投放)。
    # SUB_LANG 显式覆盖(zh|zh,en|en)；未设时按"已存在英文字幕源就重定时、没有就只产中文"——
    # 中英双语/仅英文模式下 SKILL 会先写好 字幕_英文.srt 译文(任意时间码)，故非占位 en_texts 非空即视为要英文。
    lang=os.environ.get('SUB_LANG','').strip().lower()
    want_en = ('en' in lang) if lang else bool(en_texts)
    if want_en:
        open(en_path,'w',encoding='utf-8').write(en_srt)
    elif placeholder_en and os.path.exists(en_path):
        os.remove(en_path)
    json.dump(shots, open(os.path.join(root,'脚本',ep,'镜头时长.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"定稿: {len(manifest)} 句重定时 → 字幕_中文.srt{'+字幕_英文.srt' if want_en else '(仅中文)'}；{len(shots)} 镜 → 镜头时长.json")

if __name__=='__main__': main()
