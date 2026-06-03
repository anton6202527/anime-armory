#!/usr/bin/env python3
# 逐句 TTS 配音 → gap 拼接 → voice.wav + 时长清单.json
# 后端优先级: CosyVoice > MiniMax > 火山 > macOS say。带持久缓存(同参数同文本不重复调API)。
# 用法: render_voice.py <作品根> <第N集> <zh|en>
import sys, os, re, subprocess, json, base64, uuid, hashlib, urllib.request, shutil

ROOT, EP, LANG = sys.argv[1], sys.argv[2], sys.argv[3]
VO = os.path.join(ROOT, '脚本', EP, 'voiceover.txt')
EN_SRT = os.path.join(ROOT, '脚本', EP, '字幕_英文.srt')
W = os.path.join(ROOT, '出视频', EP, '配音'); os.makedirs(W, exist_ok=True)
FF = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'; FP = shutil.which('ffprobe') or '/opt/homebrew/bin/ffprobe'
CACHE = os.path.join(ROOT, '出视频', EP, '_voicecache', LANG); os.makedirs(CACHE, exist_ok=True)

MM_KEY=os.environ.get('MINIMAX_API_KEY'); MM_GROUP=os.environ.get('MINIMAX_GROUP_ID')
MM_MODEL=os.environ.get('MINIMAX_MODEL','speech-02-hd')
MM_ENDPOINT=os.environ.get('MINIMAX_ENDPOINT','https://api.minimaxi.com/v1/t2a_v2')
USE_MM=bool(MM_KEY and MM_GROUP)
VOLC_APPID=os.environ.get('VOLC_APPID'); VOLC_TOKEN=os.environ.get('VOLC_TOKEN')
VOLC_CLUSTER=os.environ.get('VOLC_CLUSTER','volcano_tts'); VOLC_ENDPOINT=os.environ.get('VOLC_ENDPOINT','https://openspeech.bytedance.com/api/v1/tts')
USE_VOLC=bool(VOLC_APPID and VOLC_TOKEN) and not USE_MM
USE_API=USE_MM or USE_VOLC
COSY_URL=os.environ.get('COSYVOICE_URL')  # 本地 CosyVoice 服务，如 http://localhost:9880
USE_COSY=bool(COSY_URL) and not USE_MM   # CosyVoice 优先于 MiniMax；若也设了 MiniMax，CosyVoice 赢

# ── 表演标注解析（情绪/语速/停顿/钩子）→ 驱动念白，见 n2d-script formats §6 / 导演节奏.md §六 ──
# 规范情绪：angry/fearful/sad/happy/serious/neutral（关键词归类，兼容旧的自由情绪词）
def classify_emo(desc):
    if re.search(r'愤怒|怒|质问|逼问|斥|吼|暴|咆',desc): return 'angry'
    if re.search(r'惊恐|惊|恐|怕|慌|颤',desc):          return 'fearful'
    if re.search(r'悲|哀|哭|泣|痛|绝望|心碎|呜咽',desc): return 'sad'
    if re.search(r'喜|笑|窃喜|得意|欣|甜|雀跃',desc):    return 'happy'
    if re.search(r'冷冽|冷|阴狠|狠|讥|嘲|森|淡漠',desc): return 'serious'
    return 'neutral'
def speed_mult(desc):
    if '快' in desc: return 1.10
    if '慢' in desc: return 0.90
    return 1.0
def hook_kind(s):
    if '🪝' in s or '集尾' in s: return 'end'
    if '💥' in s or '爽点' in s: return 'climax'
    if '⚡' in s or '钩子' in s: return 'hook'
    return ''
def clean_text(t):
    t=re.sub(r'[⚡💥🪝]\s*[钩子爽点集尾]*','',t)  # 剥钩子标记（不念出来）
    t=t.replace('||','，')                          # 停顿一拍 → 逗号（TTS 自然气口）
    t=re.sub(r'[，,]\s*[，,]+','，',t)               # 收拢叠出的逗号
    t=re.sub(r'，\s+','，',t)                        # 中文逗号后不留空格
    return re.sub(r'\s+',' ',t).strip()

# items[i] = (role, text, emo_canonical, speed_mult, hook_kind)
items=[]; shots=[]
if LANG=='zh':
    for ln in open(VO,encoding='utf-8'):
        ln=ln.strip()
        m=re.match(r'\[(镜头[^·]*)·([^·]+)·([^\]]*)\]\s*(.+)',ln)
        if m:
            shot,role,desc,raw=m.group(1).strip(),m.group(2).strip(),m.group(3).strip(),m.group(4).strip()
            items.append((role,clean_text(raw),classify_emo(desc),speed_mult(desc),hook_kind(raw)))
            shots.append(shot)
else:
    for b in re.split(r'\n\s*\n', open(EN_SRT,encoding='utf-8').read().strip()):
        ls=[l for l in b.splitlines() if l.strip()]
        if len(ls)>=3: items.append(('',' '.join(ls[2:]),'neutral',1.0,''))
n=len(items)
MM_EMO={'angry':'angry','fearful':'fearful','sad':'sad','happy':'happy','serious':'neutral','neutral':'neutral'}
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

def cosy_tts(text, ref_audio, ref_text, out_wav):
    # CosyVoice2 常见 fork 的零样本端点；不同 fork 端点/参数可能不同，见 references/backends.md
    import urllib.parse
    q=urllib.parse.urlencode({"text":text,"prompt_text":ref_text or "","prompt_wav":ref_audio or ""})
    req=urllib.request.Request(f"{COSY_URL}/inference_zero_shot?{q}")
    with urllib.request.urlopen(req,timeout=120) as r: open(out_wav,'wb').write(r.read())

def dur_of(p): return float(subprocess.run([FP,'-v','error','-show_entries','format=duration','-of','csv=p=0',p],capture_output=True,text=True).stdout.strip() or 0)

def clamp_sp(x): return round(min(1.5,max(0.7,x)),3)
wavs=[]; measured=[]
for i in range(n):
    role,text,emo_c,spd_m,hk=items[i]
    # 取原始音频(缓存)
    if USE_COSY:
        ref=os.environ.get('COSY_REF_AUDIO'); rtext=os.environ.get('COSY_REF_TEXT','')
        raw=os.path.join(vd,f'r{i:02d}.wav'); cosy_tts(text, ref, rtext, raw); sysfx=('系统' in role)
    elif USE_MM:
        if LANG=='en': vid,emo,sp,pit=MM['EN'],None,1.0,0
        else:
            vid,emo,sp,pit=mm_cfg(role)
            if emo_c!='neutral': emo=MM_EMO[emo_c]   # 每句情绪覆盖角色默认（驱动念白表演）
            sp=clamp_sp(sp*spd_m)                     # 每句语速（快/慢）叠加到角色基速
        key=hashlib.md5(f"mm|{MM_MODEL}|{vid}|{emo}|{sp}|{pit}|{text}".encode()).hexdigest()
        raw=os.path.join(CACHE,key+'.mp3')
        if not os.path.exists(raw): minimax(text,vid,emo,sp,pit,raw)
        sysfx=('系统' in role)
    elif USE_VOLC:
        if LANG=='en': vt,emo,sp=V['EN'],None,1.0
        else: vt,emo,sp=volc_cfg(role); sp=clamp_sp(sp*spd_m)   # 火山保角色情绪、仅叠每句语速（emotion 兼容性更保守）
        key=hashlib.md5(f"volc|{vt}|{emo}|{sp}|{text}".encode()).hexdigest(); raw=os.path.join(CACHE,key+'.mp3')
        if not os.path.exists(raw): volc(text,vt,emo,sp,raw)
        sysfx=('系统' in role)
    else:
        raw=os.path.join(vd,f'r{i:02d}.aiff'); r=158 if '柳娘子' in role else 208 if ('小禾' in role or '太监' in role) else 172 if '系统' in role else 182
        v='Samantha' if LANG=='en' else 'Tingting'; rr=int((185 if LANG=='en' else r)*spd_m)   # say 用 rate 体现快/慢
        subprocess.run(['say','-v',v,'-r',str(rr),'-o',raw,text],check=True); sysfx=('系统' in role and LANG!='en')
    # FX + 统一电平
    fx = "asetrate=44100*0.9,aresample=44100,atempo=1.111,aecho=0.6:0.5:24:0.35," if sysfx else ""
    tmp=os.path.join(vd,f't{i:02d}.wav')
    subprocess.run([FF,'-y','-loglevel','error','-i',raw,'-af',f'{fx}loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100','-ar','44100','-ac','2',tmp],check=True)
    out=os.path.join(W,f'line_{i:02d}.wav'); os.replace(tmp,out)  # 最终逐句落 配音/line_NN.wav（与 manifest/spec 一致）
    measured.append(dur_of(out))
    wavs.append(out)

GAP=float(os.environ.get('LINE_GAP','0.4'))
# 句间留拍：钩子/爽点/集尾 后多留一拍"悬念呼吸"（导演节奏.md §一/§四 留白）
HOOK_GAP={'end':float(os.environ.get('GAP_END','1.0')),'climax':float(os.environ.get('GAP_CLIMAX','0.7')),'hook':float(os.environ.get('GAP_HOOK','0.6'))}
_silcache={}
def sil_for(d):
    if d not in _silcache:
        p=os.path.join(vd,f'_gap_{int(round(d*100))}.wav')
        subprocess.run([FF,'-y','-loglevel','error','-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-t',str(d),p],check=True)
        _silcache[d]=p
    return _silcache[d]
concat=[]
for k,wav in enumerate(wavs):
    concat.append(wav)
    if k<len(wavs)-1:
        hk=items[k][4] if k<len(items) else ''
        concat.append(sil_for(HOOK_GAP.get(hk,GAP)))
listf=os.path.join(vd,'_concat.txt')
open(listf,'w').write('\n'.join(f"file '{os.path.abspath(p)}'" for p in concat))
subprocess.run([FF,'-y','-loglevel','error','-f','concat','-safe','0','-i',listf,'-c','copy',os.path.join(W,f'voice_{LANG}.wav')],check=True)
if LANG=='zh':
    import json as _json
    manifest=[{"idx":i,"镜头":shots[i] if i<len(shots) else "","角色":items[i][0],"情绪":items[i][2],"钩子":items[i][4],"文本":items[i][1],"时长":round(measured[i],3),"line_wav":f"line_{i:02d}.wav"} for i in range(n)]
    out_dir=os.path.dirname(os.path.join(W,'voice_zh.wav'))
    _json.dump(manifest, open(os.path.join(out_dir,'时长清单.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"配音 {LANG}: {n} 句（后端={'CosyVoice' if USE_COSY else 'MiniMax' if USE_MM else '火山' if USE_VOLC else 'say'}，顺序拼接 gap={GAP}s，无压速）→ voice_{LANG}.wav")
