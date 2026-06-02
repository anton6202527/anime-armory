#!/usr/bin/env python3
# 逐句 TTS 配音 → 按字幕窗口贴速对齐 → 拼 voice.wav
# 后端优先级: MiniMax > 火山 > macOS say。带持久缓存(同参数同文本不重复调API)。
# 用法: _render_voice.py <workdir> <zh|en> <dur_sec>
import sys, os, re, subprocess, json, base64, uuid, hashlib, urllib.request

W, LANG, DUR = sys.argv[1], sys.argv[2], float(sys.argv[3])
FF = "/opt/homebrew/bin/ffmpeg"; FP = "/opt/homebrew/bin/ffprobe"
CACHE = os.path.join('出视频/第1集/_voicecache', LANG); os.makedirs(CACHE, exist_ok=True)

MM_KEY=os.environ.get('MINIMAX_API_KEY'); MM_GROUP=os.environ.get('MINIMAX_GROUP_ID')
MM_MODEL=os.environ.get('MINIMAX_MODEL','speech-02-hd')
MM_ENDPOINT=os.environ.get('MINIMAX_ENDPOINT','https://api.minimaxi.com/v1/t2a_v2')
USE_MM=bool(MM_KEY and MM_GROUP)
VOLC_APPID=os.environ.get('VOLC_APPID'); VOLC_TOKEN=os.environ.get('VOLC_TOKEN')
VOLC_CLUSTER=os.environ.get('VOLC_CLUSTER','volcano_tts'); VOLC_ENDPOINT=os.environ.get('VOLC_ENDPOINT','https://openspeech.bytedance.com/api/v1/tts')
USE_VOLC=bool(VOLC_APPID and VOLC_TOKEN) and not USE_MM
USE_API=USE_MM or USE_VOLC

def srt_times(p):
    out=[]
    for b in re.split(r'\n\s*\n', open(p,encoding='utf-8').read().strip()):
        ls=[l for l in b.splitlines() if l.strip()]
        if len(ls)<2: continue
        m=re.search(r'(\d+):(\d+):(\d+)[,.](\d+)',ls[1]); g=list(map(int,m.groups()))
        out.append(g[0]*3600+g[1]*60+g[2]+g[3]/1000.0)
    return out
starts=srt_times(os.path.join(W,'zh.srt'))

items=[]; shots=[]
if LANG=='zh':
    for ln in open('脚本/第1集/voiceover.txt',encoding='utf-8'):
        m=re.match(r'\[(镜头[^·]*)·([^·]+)·[^\]]*\]\s*(.+)',ln.strip())
        if m: items.append((m.group(2).strip(),m.group(3).strip())); shots.append(m.group(1).strip())
else:
    for b in re.split(r'\n\s*\n', open(os.path.join(W,'en.srt'),encoding='utf-8').read().strip()):
        ls=[l for l in b.splitlines() if l.strip()]
        if len(ls)>=3: items.append(('',' '.join(ls[2:])))
n=min(len(items),len(starts))
vd=os.path.join(W,'voice'); os.makedirs(vd,exist_ok=True)

MM=dict(SHEN=os.environ.get('MM_SHEN','female-yujie'), NARR=os.environ.get('MM_NARR','audiobook_female_1'),
        LIU=os.environ.get('MM_LIU','female-chengshu'), XIAOHE=os.environ.get('MM_XIAOHE','female-shaonv'),
        TAIJIAN=os.environ.get('MM_TAIJIAN','male-qn-qingse'), SYS=os.environ.get('MM_SYS','presenter_female'),
        EN=os.environ.get('MM_EN','female-yujie'))
# 角色 → (voice, emotion, speed, pitch)  pitch 加强区分度
def mm_cfg(role):
    if '柳娘子' in role: return MM['LIU'],'neutral',0.96,-2
    if '小禾'   in role: return MM['XIAOHE'],'sad',1.05,3
    if '太监'   in role: return MM['TAIJIAN'],'neutral',1.05,2
    if '系统'   in role: return MM['SYS'],'neutral',1.0,-1
    if role=='旁白':     return MM['NARR'],'neutral',0.98,0
    return MM['SHEN'],'neutral',1.0,0
V=dict(SHEN=os.environ.get('VOICE_SHEN','BV700_streaming'),LIU=os.environ.get('VOICE_LIU','BV700_streaming'),
       XIAOHE=os.environ.get('VOICE_XIAOHE','BV700_streaming'),TAIJIAN=os.environ.get('VOICE_TAIJIAN','BV001_streaming'),
       SYS=os.environ.get('VOICE_SYS','BV001_streaming'),EN=os.environ.get('VOICE_EN','BV503_streaming'))
def volc_cfg(role):
    if '柳娘子' in role: return V['LIU'],'serious',0.92
    if '小禾' in role: return V['XIAOHE'],'sad',1.12
    if '太监' in role: return V['TAIJIAN'],None,1.15
    if '系统' in role: return V['SYS'],None,1.0
    return V['SHEN'],'neutral',1.0

def http(url,body,hdr):
    req=urllib.request.Request(url,data=json.dumps(body).encode('utf-8'),headers=hdr)
    with urllib.request.urlopen(req,timeout=90) as r: return json.loads(r.read().decode('utf-8'))

def minimax(text,vid,emo,speed,pitch,out):
    vs={"voice_id":vid,"speed":speed,"vol":1.6,"pitch":pitch}
    if emo and not os.environ.get('MINIMAX_NOEMO'): vs["emotion"]=emo
    j=http(f"{MM_ENDPOINT}?GroupId={MM_GROUP}",{"model":MM_MODEL,"text":text,"stream":False,"voice_setting":vs,
        "audio_setting":{"sample_rate":24000,"bitrate":128000,"format":"mp3","channel":1}},
        {"Authorization":f"Bearer {MM_KEY}","Content-Type":"application/json"})
    st=(j.get('base_resp') or {}).get('status_code',0); a=(j.get('data') or {}).get('audio')
    if st!=0 or not a: raise RuntimeError(f"MiniMax status={st} {(j.get('base_resp') or {}).get('status_msg')}")
    try: raw=bytes.fromhex(a)
    except ValueError: raw=base64.b64decode(a)
    open(out,'wb').write(raw)

def volc(text,vt,emo,speed,out):
    body={"app":{"appid":VOLC_APPID,"token":VOLC_TOKEN,"cluster":VOLC_CLUSTER},"user":{"uid":"n2d"},
          "audio":{"voice_type":vt,"encoding":"mp3","speed_ratio":speed,"loudness_ratio":1.0,"rate":24000},
          "request":{"reqid":str(uuid.uuid4()),"text":text,"operation":"query","text_type":"plain"}}
    if emo and not os.environ.get('VOLC_NOEMO'): body["audio"]["emotion"]=emo
    j=http(VOLC_ENDPOINT,body,{"Authorization":f"Bearer;{VOLC_TOKEN}","Content-Type":"application/json"})
    if j.get('code')!=3000 or not j.get('data'): raise RuntimeError(f"火山 code={j.get('code')} {j.get('message')}")
    open(out,'wb').write(base64.b64decode(j['data']))

def dur_of(p): return float(subprocess.run([FP,'-v','error','-show_entries','format=duration','-of','csv=p=0',p],capture_output=True,text=True).stdout.strip() or 0)

wavs=[]; measured=[]
for i in range(n):
    role,text=items[i]
    # 取原始音频(缓存)
    if USE_MM:
        if LANG=='en': vid,emo,sp,pit=MM['EN'],None,1.0,0
        else: vid,emo,sp,pit=mm_cfg(role)
        key=hashlib.md5(f"mm|{MM_MODEL}|{vid}|{emo}|{sp}|{pit}|{text}".encode()).hexdigest()
        raw=os.path.join(CACHE,key+'.mp3')
        if not os.path.exists(raw): minimax(text,vid,emo,sp,pit,raw)
        sysfx=('系统' in role)
    elif USE_VOLC:
        if LANG=='en': vt,emo,sp=V['EN'],None,1.0
        else: vt,emo,sp=volc_cfg(role)
        key=hashlib.md5(f"volc|{vt}|{emo}|{sp}|{text}".encode()).hexdigest(); raw=os.path.join(CACHE,key+'.mp3')
        if not os.path.exists(raw): volc(text,vt,emo,sp,raw)
        sysfx=('系统' in role)
    else:
        raw=os.path.join(vd,f'r{i:02d}.aiff'); r=158 if '柳娘子' in role else 208 if ('小禾' in role or '太监' in role) else 172 if '系统' in role else 182
        v='Samantha' if LANG=='en' else 'Tingting'; rr=185 if LANG=='en' else r
        subprocess.run(['say','-v',v,'-r',str(rr),'-o',raw,text],check=True); sysfx=('系统' in role and LANG!='en')
    # FX + 统一电平
    fx = "asetrate=44100*0.9,aresample=44100,atempo=1.111,aecho=0.6:0.5:24:0.35," if sysfx else ""
    tmp=os.path.join(vd,f't{i:02d}.wav')
    subprocess.run([FF,'-y','-loglevel','error','-i',raw,'-af',f'{fx}loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100','-ar','44100','-ac','2',tmp],check=True)
    out=os.path.join(vd,f'l{i:02d}.wav'); os.replace(tmp,out)
    measured.append(dur_of(out))
    wavs.append((out,starts[i]))

GAP=float(os.environ.get('LINE_GAP','0.4'))
sil=os.path.join(vd,'_gap.wav')
subprocess.run([FF,'-y','-loglevel','error','-f','lavfi','-i',f'anullsrc=r=44100:cl=stereo','-t',str(GAP),sil],check=True)
concat=[]
for k,(wav,_) in enumerate(wavs):
    concat.append(wav)
    if k<len(wavs)-1: concat.append(sil)
listf=os.path.join(vd,'_concat.txt')
open(listf,'w').write('\n'.join(f"file '{os.path.abspath(p)}'" for p in concat))
subprocess.run([FF,'-y','-loglevel','error','-f','concat','-safe','0','-i',listf,'-c','copy',os.path.join(W,f'voice_{LANG}.wav')],check=True)
if LANG=='zh':
    import json as _json
    manifest=[{"idx":i,"镜头":shots[i] if i<len(shots) else "","角色":items[i][0],"文本":items[i][1],"时长":round(measured[i],3),"line_wav":f"line_{i:02d}.wav"} for i in range(n)]
    out_dir=os.path.dirname(os.path.join(W,'voice_zh.wav'))
    _json.dump(manifest, open(os.path.join(out_dir,'时长清单.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"配音 {LANG}: {n} 句（后端={'MiniMax' if USE_MM else '火山' if USE_VOLC else 'say'}，顺序拼接 gap={GAP}s，无压速）→ voice_{LANG}.wav")
