#!/usr/bin/env python3
# 逐句 TTS 配音 → gap 拼接 → voice.wav + 时长清单.json
# 后端优先级: 零样本克隆组(CosyVoice > FishSpeech > GPT-SoVITS > IndexTTS-2 > VoxCPM2，取第一个设了 URL 的) > MiniMax > 火山 > macOS say。
# 带持久缓存(同参数同文本不重复合成/调 API)——云端与本地零样本均缓存进 _voicecache/。
# 用法: render_voice.py <作品根> <第N集> <zh|en>
import sys, os, re, subprocess, json, base64, uuid, hashlib, urllib.request, shutil, time
_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common'))
if _COMMON not in sys.path: sys.path.insert(0, _COMMON)
from n2d_settings import load_settings, get_setting  # noqa: E402
from n2d_text_utils import clean_punctuation  # noqa: E402
from n2d_telemetry import record_event, Timer  # noqa: E402
from voice_text import clean_text  # 念白文本清洗（独立模块·带单测，治 ||→「。，」脏标点）

if len(sys.argv) < 4:
    print("usage: render_voice.py <作品根> <第N集> <zh|en>", file=sys.stderr)
    sys.exit(2)
ROOT, EP, LANG = sys.argv[1], sys.argv[2], sys.argv[3]
TIMER = Timer(); TIMER.__enter__()
VO = os.path.join(ROOT, '脚本', EP, 'voiceover.txt')
EN_SRT = os.path.join(ROOT, '脚本', EP, '字幕_英文.srt')
W = os.path.join(ROOT, '合成', EP, '配音'); os.makedirs(W, exist_ok=True)
FF = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'; FP = shutil.which('ffprobe') or '/opt/homebrew/bin/ffprobe'
CACHE = os.path.join(ROOT, '合成', EP, '_voicecache', LANG); os.makedirs(CACHE, exist_ok=True)

SETTINGS = load_settings(ROOT)
PROD_MODE = get_setting(ROOT, "制作模式", "配音先行")
# 制作模式=原生音画：说话镜的台词由视频后端原生生成。
NATIVE_AV = ("原生音画" in PROD_MODE or "native_av" in PROD_MODE.lower())

# 角色→音色持久映射（治"跨集同角色音色漂"）：可选 <作品根>/设定库/voicemap.json
#   {"角色子串": {"key":"LIU","mm":"female-chengshu","volc":"BV700_streaming","speed":0.96,"pitch":-2,"emo":"neutral"}}
# 缺文件=回退下面内置(demo)映射；有则该角色跨集稳定按此绑定，不再靠每次手动 export env。
def _load_voicemap():
    try: return json.load(open(os.path.join(ROOT,'设定库','voicemap.json'),encoding='utf-8'))
    except Exception: return {}
VOICEMAP=_load_voicemap()
def _vm_match(role):
    for sub,cfg in VOICEMAP.items():
        if sub and sub in role: return cfg
    return None

MM_KEY=os.environ.get('MINIMAX_API_KEY'); MM_GROUP=os.environ.get('MINIMAX_GROUP_ID')
MM_MODEL=os.environ.get('MINIMAX_MODEL','speech-02-hd')
MM_ENDPOINT=os.environ.get('MINIMAX_ENDPOINT','https://api.minimaxi.com/v1/t2a_v2')
USE_MM=bool(MM_KEY and MM_GROUP)
VOLC_APPID=os.environ.get('VOLC_APPID'); VOLC_TOKEN=os.environ.get('VOLC_TOKEN')
VOLC_CLUSTER=os.environ.get('VOLC_CLUSTER','volcano_tts'); VOLC_ENDPOINT=os.environ.get('VOLC_ENDPOINT','https://openspeech.bytedance.com/api/v1/tts')
# 零样本克隆后端：本地服务统一 GET /inference_zero_shot?text=&prompt_text=&prompt_wav= 契约（端点随 fork，见 backends.md）。
# (URL_env, 参考音 env 前缀, 显示名, HTTP 超时秒)，按优先级取第一个设了 URL 的；任一存在即优先于 MiniMax/火山。
ZS_SPECS=[('COSYVOICE_URL','COSY','CosyVoice',120),('FISHSPEECH_URL','FISH','FishSpeech',300),
          ('GPTSOVITS_URL','GSV','GPT-SoVITS',300),('INDEXTTS_URL','IDX','IndexTTS-2',300),
          ('VOXCPM_URL','VOX','VoxCPM2',300)]
ZS=next(((os.environ[e],pfx,lbl,to) for e,pfx,lbl,to in ZS_SPECS if os.environ.get(e)), None)
USE_ZS=bool(ZS)   # 零样本克隆优先于 MiniMax；若也设了 MiniMax，本地零样本赢
USE_VOLC=bool(VOLC_APPID and VOLC_TOKEN) and not USE_ZS and not USE_MM
USE_API=USE_ZS or USE_MM or USE_VOLC
ZS_URL,ZS_PREFIX,ZS_LABEL,ZS_TIMEOUT = ZS if ZS else (None,None,None,120)
if USE_ZS:
    # 合规闸门（项目约定：声音克隆 non-negotiable）：用参考音克隆他人嗓须先声明授权。
    # 只打印提示不够——这里与 voice_clone.py 同级硬闸门：检测到任一 <PREFIX>_REF_* 参考音即要求 VOICE_CLONE_AUTHORIZED=1。
    _refs=[k for k,v in os.environ.items() if v and (k==f'{ZS_PREFIX}_REF_AUDIO' or (k.startswith(f'{ZS_PREFIX}_REF_') and not k.endswith('_TEXT')))]
    if _refs and os.environ.get('VOICE_CLONE_AUTHORIZED')!='1':
        sys.exit(f'⛔ 合规闸门：{ZS_LABEL} 将用参考音克隆音色（{",".join(sorted(_refs))}），但未声明授权。\n'
                 f'   声音克隆仅限本人嗓 / 已授权他人嗓 / 纯合成音色（项目约定 non-negotiable，见 references/cloning.md）。\n'
                 f'   确认参考音合规后：VOICE_CLONE_AUTHORIZED=1 重跑；用默认嗓(不喂参考音)则无需授权。')
    print(f'⚠️ 零样本克隆后端 {ZS_LABEL}：参考音仅限本人嗓/已授权他人嗓/纯合成音色'
          + ('（已声明授权）' if _refs else '（未用参考音=默认嗓，无需授权）') + '。')

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
# clean_text 已抽到 voice_text.py（见顶部 import），便于单测、避免脚本不可导入

# items[i] = (role, text, emo_canonical, speed_mult, hook_kind)
items=[]; shots=[]
if LANG=='zh':
    if not os.path.isfile(VO):
        sys.exit(f'⛔ 缺 {VO} —— 请先 /n2d-script 产出 voiceover.txt（阶段1·剧本改编）。')
    for ln in open(VO,encoding='utf-8'):
        ln=ln.strip()
        m=re.match(r'\[(镜头[^·]*)·([^·]+)·([^\]]*)\]\s*(.+)',ln)
        if m:
            shot,role,desc,raw=m.group(1).strip(),m.group(2).strip(),m.group(3).strip(),m.group(4).strip()
            items.append((role,clean_text(raw),classify_emo(desc),speed_mult(desc),hook_kind(raw)))
            shots.append(shot)
else:
    # 英文字幕由 n2d-script 阶段2(分镜定稿, finalize_storyboard)产出，在配音之后；故 en 配音须在分镜定稿后才跑。
    if not os.path.isfile(EN_SRT):
        sys.exit(f'⛔ 缺 {EN_SRT} —— 英文配音需先跑 n2d-script 阶段2(分镜定稿)产出英文字幕，再跑 en。')
    for b in re.split(r'\n\s*\n', open(EN_SRT,encoding='utf-8').read().strip()):
        ls=[l for l in b.splitlines() if l.strip()]
        if len(ls)>=3: items.append(('',' '.join(ls[2:]),'neutral',1.0,''))
n=len(items)
if n==0:
    sys.exit('⛔ voiceover.txt 无可解析台词行（格式：[镜头N·角色·情绪] 台词）。' if LANG=='zh'
             else f'⛔ {EN_SRT} 无可解析字幕块。')
MM_EMO={'angry':'angry','fearful':'fearful','sad':'sad','happy':'happy','serious':'neutral','neutral':'neutral'}
vd=os.path.join(W,'voice'); os.makedirs(vd,exist_ok=True)

MM=dict(SHEN=os.environ.get('MM_SHEN','female-yujie'), NARR=os.environ.get('MM_NARR','audiobook_female_1'),
        LIU=os.environ.get('MM_LIU','female-chengshu'), XIAOHE=os.environ.get('MM_XIAOHE','female-shaonv'),
        TAIJIAN=os.environ.get('MM_TAIJIAN','male-qn-qingse'), SYS=os.environ.get('MM_SYS','presenter_female'),
        EN=os.environ.get('MM_EN','female-yujie'))
# 角色 → (voice, emotion, speed, pitch)  pitch 加强区分度
def mm_cfg(role):
    vm=_vm_match(role)
    if vm: return (vm.get('mm') or MM.get(vm.get('key','SHEN'), MM['SHEN']), vm.get('emo','neutral'), float(vm.get('speed',1.0)), int(vm.get('pitch',0)))
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
    vm=_vm_match(role)
    if vm: return (vm.get('volc') or V.get(vm.get('key','SHEN'), V['SHEN']), vm.get('emo'), float(vm.get('speed',1.0)))
    if '柳娘子' in role: return V['LIU'],'serious',0.92
    if '小禾' in role: return V['XIAOHE'],'sad',1.12
    if '太监' in role: return V['TAIJIAN'],None,1.15
    if '系统' in role: return V['SYS'],None,1.0
    return V['SHEN'],'neutral',1.0

# ── 零样本克隆(CosyVoice/FishSpeech) 按角色分音色：角色→音色键→参考音 env ──
# 角色名(含子串)归到音色键；注意 '沈念旁白' 走 SHEN(沈念内心)，纯 '旁白' 才走 NARR(旁白)
def role_key(role):
    vm=_vm_match(role)
    if vm and vm.get('key'): return vm['key']
    if '系统' in role:   return 'SYS'
    if '柳娘子' in role: return 'LIU'
    if '小禾' in role:   return 'XIAOHE'
    if '太监' in role:   return 'TAIJIAN'
    if '妖' in role:     return 'YAO'
    if role=='旁白':     return 'NARR'
    return 'SHEN'   # 沈念旁白 / 沈念 / 默认
# 取该角色的 (参考音wav, 逐字文本)：优先 <PREFIX>_REF_<KEY>，回退全局 <PREFIX>_REF_AUDIO，再回退 None=默认嗓
def role_ref(prefix, role):
    k=role_key(role)
    ref=os.environ.get(f'{prefix}_REF_{k}') or os.environ.get(f'{prefix}_REF_AUDIO')
    txt=os.environ.get(f'{prefix}_REF_{k}_TEXT') or os.environ.get(f'{prefix}_REF_TEXT','')
    return ref, txt

def http(url,body,hdr):
    req=urllib.request.Request(url,data=json.dumps(body).encode('utf-8'),headers=hdr)
    with urllib.request.urlopen(req,timeout=90) as r: return json.loads(r.read().decode('utf-8'))

def minimax(text,vid,emo,speed,pitch,out):
    vs={"voice_id":vid,"speed":speed,"vol":1.0,"pitch":pitch}  # vol=1.0：电平统一交给下游 loudnorm，避免源端先削波
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

def zeroshot_tts(url, text, ref_audio, ref_text, out_wav, timeout):
    # 本地零样本克隆统一契约：GET /inference_zero_shot?text=&prompt_text=&prompt_wav=
    # CosyVoice / FishSpeech(n2d_fish_server) / GPT-SoVITS / IndexTTS-2 / VoxCPM2 均包成此端点（端点随 fork，见 references/backends.md）
    import urllib.parse
    q=urllib.parse.urlencode({"text":text,"prompt_text":ref_text or "","prompt_wav":ref_audio or ""})
    req=urllib.request.Request(f"{url}/inference_zero_shot?{q}")
    with urllib.request.urlopen(req,timeout=timeout) as r: open(out_wav,'wb').write(r.read())

def dur_of(p):
    s=subprocess.run([FP,'-v','error','-show_entries','format=duration','-of','csv=p=0',p],capture_output=True,text=True).stdout.strip()
    try:
        d=float(s)
        return d if d>0 else 0.0
    except (TypeError, ValueError):
        return 0.0

def estimate_placeholder_duration(text, spd_m, hk):
    cjk=len(re.findall(r'[\u3400-\u9fff]', text))
    punct=len(re.findall(r'[，。！？、；：,.!?;:]', text))
    d=cjk/(5.0*spd_m)+punct*0.12
    if spd_m<1.0: d+=0.25
    if spd_m>1.0: d-=0.12
    if hk=='climax': d+=0.25
    if hk=='end': d+=0.35
    return max(1.15, min(8.0, d))

def make_silence(out, duration):
    subprocess.run([FF,'-y','-loglevel','error','-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-t',f'{duration:.3f}','-ar','44100','-ac','2',out],check=True)

def clamp_sp(x): return round(min(1.5,max(0.7,x)),3)
wavs=[]; measured=[]; placeholders=[]; placeholder_reason=''
for i in range(n):
    role,text,emo_c,spd_m,hk=items[i]
    # 取原始音频(缓存)
    if USE_ZS:
        ref,rtext=role_ref(ZS_PREFIX,role)
        # 本地零样本同样缓存：同后端+同参考音+同文本 → 不重复合成（本地 MPS/CPU 合成慢，缓存收益最大）
        key=hashlib.md5(f"zs|{ZS_LABEL}|{ref}|{rtext}|{text}".encode()).hexdigest(); raw=os.path.join(CACHE,key+'.wav')
        try:
            if not os.path.exists(raw): zeroshot_tts(ZS_URL, text, ref, rtext, raw, ZS_TIMEOUT)
        except Exception as ex:
            o=os.path.join(W,f'line_{i:02d}.wav'); dd=estimate_placeholder_duration(text,spd_m,hk)
            make_silence(o,dd); measured.append(dd); wavs.append(o); placeholders.append(i)
            placeholder_reason=placeholder_reason or f'{ZS_LABEL} 单句合成失败({type(ex).__name__});静音占位（其余句正常）'
            print(f'⚠️ 第{i}句({role}) {ZS_LABEL} 合成失败：{ex} → 静音占位，不中断整集'); continue
        sysfx=('系统' in role)
    elif USE_MM:
        if LANG=='en': vid,emo,sp,pit=MM['EN'],None,1.0,0
        else:
            vid,emo,sp,pit=mm_cfg(role)
            if emo_c!='neutral': emo=MM_EMO[emo_c]   # 每句情绪覆盖角色默认（驱动念白表演）
            sp=clamp_sp(sp*spd_m)                     # 每句语速（快/慢）叠加到角色基速
        key=hashlib.md5(f"mm|{MM_MODEL}|{vid}|{emo}|{sp}|{pit}|{text}".encode()).hexdigest()
        raw=os.path.join(CACHE,key+'.mp3')
        try:
            if not os.path.exists(raw): minimax(text,vid,emo,sp,pit,raw)
        except Exception as ex:
            o=os.path.join(W,f'line_{i:02d}.wav'); dd=estimate_placeholder_duration(text,spd_m,hk)
            make_silence(o,dd); measured.append(dd); wavs.append(o); placeholders.append(i)
            placeholder_reason=placeholder_reason or f'MiniMax 单句合成失败({type(ex).__name__});静音占位（其余句正常）'
            print(f'⚠️ 第{i}句({role}) MiniMax 合成失败：{ex} → 静音占位，不中断整集'); continue
        sysfx=('系统' in role)
    elif USE_VOLC:
        if LANG=='en': vt,emo,sp=V['EN'],None,1.0
        else: vt,emo,sp=volc_cfg(role); sp=clamp_sp(sp*spd_m)   # 火山保角色情绪、仅叠每句语速（emotion 兼容性更保守）
        key=hashlib.md5(f"volc|{vt}|{emo}|{sp}|{text}".encode()).hexdigest(); raw=os.path.join(CACHE,key+'.mp3')
        try:
            if not os.path.exists(raw): volc(text,vt,emo,sp,raw)
        except Exception as ex:
            o=os.path.join(W,f'line_{i:02d}.wav'); dd=estimate_placeholder_duration(text,spd_m,hk)
            make_silence(o,dd); measured.append(dd); wavs.append(o); placeholders.append(i)
            placeholder_reason=placeholder_reason or f'火山 单句合成失败({type(ex).__name__});静音占位（其余句正常）'
            print(f'⚠️ 第{i}句({role}) 火山 合成失败：{ex} → 静音占位，不中断整集'); continue
        sysfx=('系统' in role)
    else:
        raw=os.path.join(vd,f'r{i:02d}.aiff'); r=158 if '柳娘子' in role else 208 if ('小禾' in role or '太监' in role) else 172 if '系统' in role else 182
        v='Samantha' if LANG=='en' else 'Tingting'; rr=int((185 if LANG=='en' else r)*spd_m)   # say 用 rate 体现快/慢
        subprocess.run(['say','-v',v,'-r',str(rr),'-o',raw,text],check=True); sysfx=('系统' in role and LANG!='en')
        raw_dur=dur_of(raw)
        if LANG=='zh' and raw_dur<=0:
            out=os.path.join(W,f'line_{i:02d}.wav')
            d=estimate_placeholder_duration(text, spd_m, hk)
            make_silence(out, d)
            measured.append(d)
            wavs.append(out)
            placeholders.append(i)
            placeholder_reason='macOS say 中文语音输出为空;已自动生成静音占位时长轨'
            continue
    # FX + 统一电平（系统音"机械感"FX 可自定义/禁用：SYS_AUDIO_FX='' 关掉）
    fx = (os.environ.get('SYS_AUDIO_FX', 'asetrate=44100*0.9,aresample=44100,atempo=1.111,aecho=0.6:0.5:24:0.35,') if sysfx else "")
    tmp=os.path.join(vd,f't{i:02d}.wav')
    subprocess.run([FF,'-y','-loglevel','error','-i',raw,'-af',f'{fx}loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100','-ar','44100','-ac','2',tmp],check=True)
    out=os.path.join(W,f'line_{i:02d}.wav'); os.replace(tmp,out)  # 最终逐句落 配音/line_NN.wav（与 manifest/spec 一致）
    d=dur_of(out)
    if d<=0:
        d=dur_of(out)   # 重试一次：ffprobe 偶发管道/探测失败，不该把已合成的真实音频换成静音
    if d<=0:
        d=estimate_placeholder_duration(text, spd_m, hk)
        make_silence(out, d)
        placeholders.append(i)
        placeholder_reason=placeholder_reason or '音频时长探测失败;已自动生成静音占位时长轨'
    measured.append(d)
    wavs.append(out)

GAP=float(os.environ.get('LINE_GAP','0.4'))
# 句间留拍：钩子/爽点/集尾 后多留一拍"悬念呼吸"（导演节奏.md §一/§四 留白）；末句不留拍（concat 尾部不补静音）
HOOK_GAP={'end':float(os.environ.get('GAP_END','1.0')),'climax':float(os.environ.get('GAP_CLIMAX','0.7')),'hook':float(os.environ.get('GAP_HOOK','0.6'))}
# gaps[k]=第 k 句之后的留拍；concat 与 manifest 时间轴共用同一份，保证字幕/镜头时长 == voice.wav 实际拼接
gaps=[(HOOK_GAP.get(items[k][4] if k<len(items) else '', GAP) if k<n-1 else 0.0) for k in range(n)]
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
        concat.append(sil_for(gaps[k]))
listf=os.path.join(vd,'_concat.txt')
open(listf,'w').write('\n'.join(f"file '{os.path.abspath(p)}'" for p in concat))
subprocess.run([FF,'-y','-loglevel','error','-f','concat','-safe','0','-i',listf,'-c','copy',os.path.join(W,f'voice_{LANG}.wav')],check=True)
if LANG=='zh':
    import json as _json
    # 真实时间轴：逐句在 voice_zh.wav 中的 start/end + 其后留拍（measured 已含系统音变速，逐拍对齐）
    starts=[]; ends=[]; _t=0.0
    for i in range(n):
        starts.append(_t); _t+=measured[i]; ends.append(_t); _t+=gaps[i]
    # 音色绑定留痕（治"跨集同角色音色漂"——env 注入的绑定不落痕就无法机检）：
    # 音色键=角色音色槽（跨集应稳定）；voice_id=实际下发后端的音色；情绪_已应用=后端真正吃到的情绪（暴露火山不逐句驱动情绪）。
    def _voice_id_for(role):
        if USE_ZS:
            ref=role_ref(ZS_PREFIX, role)[0]
            return f'{ZS_LABEL}:{role_key(role)}:' + (os.path.basename(ref) if ref else '默认嗓')
        if USE_MM:   return f'MiniMax:{mm_cfg(role)[0]}'
        if USE_VOLC: return f'火山:{volc_cfg(role)[0]}'
        return 'say:Tingting'
    def _emo_applied(role, emo_c):
        if USE_MM:
            if os.environ.get('MINIMAX_NOEMO'): return '后端禁用(NOEMO)'
            return MM_EMO[emo_c] if emo_c!='neutral' else mm_cfg(role)[1]
        if USE_VOLC: return (volc_cfg(role)[1] or 'none') + '(角色固定·不接逐句情绪)'
        return '后端不接情绪'  # 零样本/say
    manifest=[{"idx":i,"镜头":shots[i] if i<len(shots) else "","角色":items[i][0],"情绪":items[i][2],"钩子":items[i][4],"文本":items[i][1],
               "时长":round(measured[i],3),"start":round(starts[i],3),"end":round(ends[i],3),"gap_after":round(gaps[i],3),"line_wav":f"line_{i:02d}.wav",
               "音色键":role_key(items[i][0]),"voice_id":_voice_id_for(items[i][0]),"情绪_已应用":_emo_applied(items[i][0],items[i][2]),
               **({"占位":True} if i in placeholders else {})} for i in range(n)]
    out_dir=os.path.dirname(os.path.join(W,'voice_zh.wav'))
    _json.dump(manifest, open(os.path.join(out_dir,'时长清单.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)

if placeholders:
    warn='⚠️ 占位提示: '+placeholder_reason+'。当前不是有声朗读,仅供出图前 rough timing;出图前请换真实配音重跑 n2d-voice。'
    open(os.path.join(W,'_占位说明.md'),'w',encoding='utf-8').write(
        f"# 本地占位配音\n\n{warn}\n\n用途: 跑通分镜/字幕时间轴 rough preview。\n要求: 跨过出图前,换 CosyVoice/克隆/MiniMax 等真实配音重跑,并用真实时长回跑 n2d-script 阶段2。\n"
    )

if LANG == 'zh' and os.environ.get('N2D_UPDATE_PROGRESS', '1') != '0':
    prog = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'novel2drama', 'progress.py'))
    try:
        subprocess.run(['python3', prog, 'set', ROOT, EP, '配音', '✅'], check=False)
    except Exception:
        pass
    if placeholders: print(warn)

# 记录生产数据 (P0)
PROVIDER = ZS_LABEL if USE_ZS else 'MiniMax' if USE_MM else '火山' if USE_VOLC else 'say'
record_event(
    ROOT, EP, stage="voice", event="generation",
    asset=os.path.join(W, f'voice_{LANG}.wav'),
    status="pass",
    duration_sec=TIMER.elapsed(),
    provider=PROVIDER,
    meta={"lines": n, "placeholder_lines": len(placeholders)}
)

print(f"配音 {LANG}: {n} 句（后端={ZS_LABEL if USE_ZS else 'MiniMax' if USE_MM else '火山' if USE_VOLC else 'say'}，顺序拼接 gap={GAP}s+钩子留拍，无压速）→ voice_{LANG}.wav")
