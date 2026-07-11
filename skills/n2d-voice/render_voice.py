#!/usr/bin/env python3
# 逐句 TTS 配音 → gap 拼接 → voice.wav + 时长清单.json
# 后端优先级: 零样本克隆组(CosyVoice > FishSpeech > GPT-SoVITS > IndexTTS-2 > VoxCPM2，取第一个设了 URL 的) > MiniMax > 火山 > macOS say。
# 带持久缓存(同参数同文本不重复合成/调 API)——云端与本地零样本均缓存进 _voicecache/。
# 用法: render_voice.py <作品根> <第N集> <zh|en>
import sys, os, re, subprocess, json, base64, uuid, hashlib, urllib.request, shutil, time
from pathlib import Path
_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'n2d', '_lib'))
if _COMMON not in sys.path: sys.path.insert(0, _COMMON)
from n2d_settings import load_settings, get_setting  # noqa: E402
from n2d_const import PRODUCTION_MODE_DEFAULT  # noqa: E402  制作模式默认单一真值源（当前=混合自动路由）
from n2d_text_utils import clean_punctuation  # noqa: E402
from n2d_route import voiceover_fingerprint, manifest_is_placeholder, placeholder_rows  # noqa: E402  配音源指纹 + 占位判定单一真值源（治"配音后改 voiceover 导致清单过期" / 占位口径不一致）
from n2d_telemetry import record_event, Timer  # noqa: E402
try:
    from n2d_friction import log_friction  # noqa: E402  现场摩擦信号（自我优化闭环生产者；纯 stdlib）
except Exception:  # 采集绝不拖垮配音
    def log_friction(*a, **k):  # type: ignore
        return None
from voice_text import clean_text, parse_voiceover_line  # 念白文本清洗/格式解析（独立模块·带单测）
import voice_manifest as vmf  # 时长清单条目 + voice_key 音色留痕（独立模块·带单测；契约字段 VOICE_KEY_FIELD）
import voice_lexicon as vlex  # 专名/多音字读音词典（谐音只下到声学层，字幕/清单保留正名；独立模块·带单测）
from gptsovits_adapter import endpoint_candidates  # GPT-SoVITS 官方 API / CosyVoice 兼容端点适配
from voice_preproduction import (  # 声音选角锁 + 最终渲染守卫
    casting_backend,
    casting_blockers,
    casting_path,
    role_entry as casting_role_entry,
)

if len(sys.argv) < 4:
    print("usage: render_voice.py <作品根> <第N集> <zh|en>", file=sys.stderr)
    sys.exit(2)
ROOT, EP, LANG = sys.argv[1], sys.argv[2], sys.argv[3]
TIMER = Timer(); TIMER.__enter__()
VO = os.path.join(ROOT, '脚本', EP, 'voiceover.txt')
EN_SRT = os.path.join(ROOT, '脚本', EP, '字幕_英文.srt')
VOICE_PURPOSE = os.environ.get('N2D_VOICE_PURPOSE', 'final').strip().lower() or 'final'
GUIDE_PURPOSE = VOICE_PURPOSE in {'guide', 'performance_guide', '导引'}
W = os.path.join(ROOT, '合成', EP, '配音_导引' if GUIDE_PURPOSE else '配音'); os.makedirs(W, exist_ok=True)
FF = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'; FP = shutil.which('ffprobe') or '/opt/homebrew/bin/ffprobe'
CACHE = os.path.join(ROOT, '合成', EP, '_voicecache', LANG); os.makedirs(CACHE, exist_ok=True)

SETTINGS = load_settings(ROOT)
PROD_MODE = get_setting(ROOT, "制作模式", PRODUCTION_MODE_DEFAULT)
# 制作模式=原生音画：说话镜的台词由视频后端原生生成。
NATIVE_AV = ("原生音画" in PROD_MODE or "native_av" in PROD_MODE.lower())
HYBRID_MODE = ("混合自动路由" in PROD_MODE or "hybrid" in PROD_MODE.lower() or "mixed" in PROD_MODE.lower())
STRICT_NO_PLACEHOLDER_AUDIO = HYBRID_MODE

try:
    VOICE_CASTING = json.load(open(casting_path(Path(ROOT)), encoding='utf-8'))
except Exception:
    VOICE_CASTING = {}

def _casting_entry(role):
    return casting_role_entry(VOICE_CASTING, role) or {}

# 角色→音色持久映射（治"跨集同角色音色漂"）：可选 <作品根>/设定库/voicemap.json
#   {"角色子串": {"key":"LIU","mm":"female-chengshu","volc":"BV700_streaming","speed":0.96,"pitch":-2,"emo":"neutral"}}
# 缺文件=回退下面内置(demo)映射；有则该角色跨集稳定按此绑定，不再靠每次手动 export env。
def _load_voicemap():
    try: return json.load(open(os.path.join(ROOT,'设定库','voicemap.json'),encoding='utf-8'))
    except Exception: return {}
VOICEMAP=_load_voicemap()
def _vm_match(role): return vmf.vm_match(role, VOICEMAP)  # 实现已抽到 voice_manifest.py（带单测）
LEXICON=vlex.load_lexicon(ROOT)  # 读音词典：缺则空词典=原样念，零副作用
import reverb_profile as rvb  # 场景空间声学/混响（对白轨）：缺 声学表.json=全 dry，零回归
ACOUSTIC=rvb.load_acoustic_table(ROOT)   # 缺/坏 → {} → 每句 line_reverb 恒为 ""（dry）
SHOT_SCENE=rvb._shot_scene_index(ROOT, EP)  # {镜头号/CLIP号 → 场景串}，解析不到 → {} → dry

MM_KEY=os.environ.get('MINIMAX_API_KEY'); MM_GROUP=os.environ.get('MINIMAX_GROUP_ID')
MM_MODEL=os.environ.get('MINIMAX_MODEL','speech-02-hd')
MM_ENDPOINT=os.environ.get('MINIMAX_ENDPOINT','https://api.minimaxi.com/v1/t2a_v2')
USE_MM=bool(MM_KEY and MM_GROUP)
VOLC_APPID=os.environ.get('VOLC_APPID'); VOLC_TOKEN=os.environ.get('VOLC_TOKEN')
VOLC_CLUSTER=os.environ.get('VOLC_CLUSTER','volcano_tts'); VOLC_ENDPOINT=os.environ.get('VOLC_ENDPOINT','https://openspeech.bytedance.com/api/v1/tts')
# 零样本克隆后端：本地服务统一 GET /inference_zero_shot?text=&prompt_text=&prompt_wav= 契约（端点随 fork，见 backends.md）。
# (URL_env, 参考音 env 前缀, 显示名, HTTP 超时秒)，按优先级取第一个设了 URL 的；任一存在即优先于 MiniMax/火山。
# 后端清单单一真值源在 skills/n2d/_lib/voice_backends.py（候选快照+适配层）；此处只取用，不再各抄一份。
try:
    from voice_backends import zs_specs_legacy as _zs_legacy  # noqa: E402
    ZS_SPECS=[tuple(t) for t in _zs_legacy()]
except Exception:  # 退化兜底：catalog 不可用时仍按内置优先级跑
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
    # 音色定妆照：voicemap 钉死的逐角色 canonical 参考音同样是「用参考音克隆」，与 env 参考音同级触发授权闸门，绝不因来源换成项目内文件就绕过合规。
    _vm_refs=sorted({f'voicemap[{sub}].ref' for sub,cfg in (VOICEMAP or {}).items() if isinstance(cfg,dict) and cfg.get('ref')})
    _casting_refs=sorted({
        f"voice_casting[{row.get('role')}].reference_audio"
        for row in (VOICE_CASTING.get('roles') or [])
        if isinstance(row, dict) and row.get('reference_audio')
    })
    _refs=sorted(set(_refs)|set(_vm_refs)|set(_casting_refs))
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
        sys.exit(f'⛔ 缺 {VO} —— 请先 n2d-script 产出 voiceover.txt（阶段1·剧本改编）。')
    for ln in open(VO,encoding='utf-8'):
        parsed=parse_voiceover_line(ln)
        if parsed:
            shot,role,desc,raw=parsed
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
if HYBRID_MODE and LANG == 'zh':
    purpose = 'guide' if GUIDE_PURPOSE else 'final'
    required_roles = [row[0] for row in items]
    blockers = casting_blockers(VOICE_CASTING, required_roles, purpose=purpose)
    if blockers:
        sys.exit(
            '⛔ 声音选角锁未通过，未生成任何配音 WAV。\n'
            + '\n'.join('   - ' + item for item in blockers[:30])
            + f'\n   先运行: python3 skills/n2d-voice/voice_preflight.py prepare {ROOT} {EP}'
            + '\n   试听确认后用 voice_preflight.py lock 锁角色；最终配音只在锁定后批量渲染。'
        )
    expected_backends = {
        casting_backend(_casting_entry(role)) for role in required_roles
        if casting_backend(_casting_entry(role))
    }
    active_backend = (
        casting_backend({'backend': ZS_LABEL}) if USE_ZS
        else 'minimax' if USE_MM
        else 'volcengine' if USE_VOLC
        else 'say'
    )
    if len(expected_backends) > 1:
        sys.exit(
            '⛔ 当前 render_voice 一批只能调用一个后端，但 voice_casting 锁了多个后端: '
            + ', '.join(sorted(expected_backends))
            + '。请按后端拆批/接适配器，不得静默换音色。'
        )
    if expected_backends and active_backend not in expected_backends:
        sys.exit(
            f'⛔ 选角锁要求后端={next(iter(expected_backends))}，当前探测后端={active_backend}。'
            '请启动/配置已锁后端，不能用自动 fallback 代替定妆音色。'
        )
MM_EMO={'angry':'angry','fearful':'fearful','sad':'sad','happy':'happy','serious':'neutral','neutral':'neutral'}
vd=os.path.join(W,'voice'); os.makedirs(vd,exist_ok=True)

MM=dict(SHEN=os.environ.get('MM_SHEN','female-yujie'), NARR=os.environ.get('MM_NARR','audiobook_female_1'),
        LIU=os.environ.get('MM_LIU','female-chengshu'), XIAOHE=os.environ.get('MM_XIAOHE','female-shaonv'),
        TAIJIAN=os.environ.get('MM_TAIJIAN','male-qn-qingse'), SYS=os.environ.get('MM_SYS','presenter_female'),
        EN=os.environ.get('MM_EN','female-yujie'))
# 角色 → (voice, emotion, speed, pitch)  pitch 加强区分度
def mm_cfg(role):
    cast=_casting_entry(role)
    if cast and casting_backend(cast)=='minimax' and cast.get('voice_id'):
        return (cast.get('voice_id'), cast.get('emotion','neutral'), float(cast.get('speed',1.0) or 1.0), int(cast.get('pitch',0) or 0))
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
    cast=_casting_entry(role)
    if cast and casting_backend(cast)=='volcengine' and cast.get('voice_id'):
        return (cast.get('voice_id'), cast.get('emotion'), float(cast.get('speed',1.0) or 1.0))
    vm=_vm_match(role)
    if vm: return (vm.get('volc') or V.get(vm.get('key','SHEN'), V['SHEN']), vm.get('emo'), float(vm.get('speed',1.0)))
    if '柳娘子' in role: return V['LIU'],'serious',0.92
    if '小禾' in role: return V['XIAOHE'],'sad',1.12
    if '太监' in role: return V['TAIJIAN'],None,1.15
    if '系统' in role: return V['SYS'],None,1.0
    return V['SHEN'],'neutral',1.0

# ── 零样本克隆(CosyVoice/FishSpeech) 按角色分音色：角色→音色键→参考音 env ──
# 角色名(含子串)归到音色键；实现已抽到 voice_manifest.role_key（带单测，'沈念旁白'走SHEN等规则见彼处）
def role_key(role): return vmf.role_key(role, VOICEMAP)
# 取该角色的 (参考音wav, 逐字文本)：优先 <PREFIX>_REF_<KEY>，回退全局 <PREFIX>_REF_AUDIO，再回退 None=默认嗓
def role_ref(prefix, role):
    k=role_key(role)
    ref=os.environ.get(f'{prefix}_REF_{k}') or os.environ.get(f'{prefix}_REF_AUDIO')
    txt=os.environ.get(f'{prefix}_REF_{k}_TEXT') or os.environ.get(f'{prefix}_REF_TEXT','')
    cast=_casting_entry(role)
    if not ref and cast:
        cast_ref=cast.get('reference_audio') or ''
        if cast_ref:
            ref=cast_ref if os.path.isabs(cast_ref) else os.path.abspath(os.path.join(ROOT, cast_ref))
            txt=txt or cast.get('reference_text','')
    # 音色定妆照（治"后端零样本每集重克隆漂"）：env 未指定参考音时，回退 voicemap 钉死的逐角色 canonical
    # 参考音——项目内冻结一条 wav 全篇/跨集复用为克隆源，等价图像层「共享定妆库先行」。env 仍可临时覆盖。
    if not ref:
        cfg=vmf.vm_match(role, VOICEMAP) or {}
        vmref=cfg.get('ref')
        if vmref:
            ref=vmref if os.path.isabs(vmref) else os.path.abspath(os.path.join(ROOT, vmref))
            txt=txt or cfg.get('ref_text','')
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

def zeroshot_tts(url, text, ref_audio, ref_text, out_wav, timeout, label, lang, speed=1.0):
    # 本地零样本克隆优先契约：GET /inference_zero_shot?text=&prompt_text=&prompt_wav=
    # 官方 GPT-SoVITS API 使用根路径 + refer_wav_path/text_language；endpoint_candidates 会在兼容端点失败后重试。
    errors=[]
    for _kind, candidate in endpoint_candidates(label, url, text, ref_audio, ref_text, text_language=lang, speed=speed):
        try:
            req=urllib.request.Request(candidate)
            with urllib.request.urlopen(req,timeout=timeout) as r: open(out_wav,'wb').write(r.read())
            return
        except Exception as ex:
            errors.append(f"{_kind}: {type(ex).__name__}: {ex}")
    raise RuntimeError(f"{label} endpoint unavailable; " + " | ".join(errors))

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

def estimate_spoken_duration(text, spd_m=1.0):
    cjk=len(re.findall(r'[\u3400-\u9fff]', text))
    ascii_words=len(re.findall(r'[A-Za-z0-9]+', text))
    punct=len(re.findall(r'[，。！？、；：,.!?;:]', text))
    ellipsis=text.count('……') + text.count('...')
    # Short-form narration target: roughly 4.8-5.8 CJK chars/sec, with small punctuation breath.
    d=(cjk/5.2 + ascii_words/2.6 + punct*0.10 + ellipsis*0.22) / max(0.55, spd_m)
    return max(1.1, min(12.0, d))

def _env_float(names, default):
    for name in names:
        v=os.environ.get(name)
        if v not in (None, ''):
            try: return float(v)
            except ValueError: pass
    return default

def _label_env_name(label):
    return re.sub(r'[^A-Z0-9]+', '', str(label or '').upper())

def zs_speed_for(role, spd_m):
    vm=_vm_match(role) or {}
    role_sp=float(vm.get('speed',1.0) or 1.0)
    base=_env_float([f'{ZS_PREFIX}_SPEED', f'{_label_env_name(ZS_LABEL)}_SPEED', 'ZS_SPEED'], 1.0)
    # GPT-SoVITS official API accepts higher speed values; Cosy/Fish wrappers are more conservative.
    hi=4.0 if ZS_LABEL and 'gpt' in ZS_LABEL.lower() and 'sovits' in ZS_LABEL.lower() else 1.5
    return round(min(hi,max(0.55,base*role_sp*spd_m)),3)

def make_silence(out, duration):
    subprocess.run([FF,'-y','-loglevel','error','-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-t',f'{duration:.3f}','-ar','44100','-ac','2',out],check=True)

def clamp_sp(x): return round(min(1.5,max(0.7,x)),3)
wavs=[]; measured=[]; expected=[]; placeholders=[]; placeholder_reason=''
for i in range(n):
    role,text,emo_c,spd_m,hk=items[i]
    expected.append(estimate_spoken_duration(items[i][1], spd_m))
    text=vlex.to_spoken(text,LEXICON)  # 念白文本：专名/多音字谐音替换，只喂 TTS+缓存键；清单/字幕仍用 items[i][1] 正名
    # 取原始音频(缓存)
    if USE_ZS:
        ref,rtext=role_ref(ZS_PREFIX,role)
        zs_sp=zs_speed_for(role, spd_m)
        # 本地零样本同样缓存：同后端+同参考音+同文本 → 不重复合成（本地 MPS/CPU 合成慢，缓存收益最大）
        key=hashlib.md5(f"zs|{ZS_LABEL}|{ref}|{rtext}|{zs_sp}|{text}".encode()).hexdigest(); raw=os.path.join(CACHE,key+'.wav')
        try:
            if os.path.exists(raw) and dur_of(raw)<=0:
                os.remove(raw)
            if not os.path.exists(raw): zeroshot_tts(ZS_URL, text, ref, rtext, raw, ZS_TIMEOUT, ZS_LABEL, LANG, speed=zs_sp)
            if dur_of(raw)<=0:
                try: os.remove(raw)
                except OSError: pass
                raise RuntimeError(f'{ZS_LABEL} returned invalid audio')
        except Exception as ex:
            if STRICT_NO_PLACEHOLDER_AUDIO:
                sys.exit(f'⛔ 第{i}句({role}) {ZS_LABEL} 合成失败：{ex}。混合路由禁止生成静音/次品占位 WAV；修复已锁后端后重跑。')
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
            if STRICT_NO_PLACEHOLDER_AUDIO:
                sys.exit(f'⛔ 第{i}句({role}) MiniMax 合成失败：{ex}。混合路由禁止生成静音/次品占位 WAV；修复已锁后端后重跑。')
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
            if STRICT_NO_PLACEHOLDER_AUDIO:
                sys.exit(f'⛔ 第{i}句({role}) 火山合成失败：{ex}。混合路由禁止生成静音/次品占位 WAV；修复已锁后端后重跑。')
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
            if STRICT_NO_PLACEHOLDER_AUDIO:
                try: os.remove(raw)
                except OSError: pass
                sys.exit(f'⛔ 第{i}句({role}) macOS say 输出为空。混合路由禁止生成静音占位 WAV；请先锁定可用声音后端。')
            out=os.path.join(W,f'line_{i:02d}.wav')
            d=estimate_placeholder_duration(text, spd_m, hk)
            make_silence(out, d)
            placeholders.append(i)
            measured.append(d)
            wavs.append(out)
            placeholder_reason='macOS say 中文语音输出为空;已自动生成静音占位时长轨'
            continue
    # FX + 统一电平（系统音"机械感"FX 可自定义/禁用：SYS_AUDIO_FX='' 关掉）
    # 场景混响前置（对白空间声学）：按该句所属场景取 aecho 片段（dry=""），叠在系统FX前、loudnorm前
    _scene = rvb._resolve_scene(shots[i] if i < len(shots) else "", SHOT_SCENE)  # en 无 shots → ""=dry
    fx = rvb.line_reverb(_scene, ACOUSTIC) + (os.environ.get('SYS_AUDIO_FX', 'asetrate=44100*0.9,aresample=44100,atempo=1.111,aecho=0.6:0.5:24:0.35,') if sysfx else "")
    tmp=os.path.join(vd,f't{i:02d}.wav')
    subprocess.run([FF,'-y','-loglevel','error','-i',raw,'-af',f'{fx}loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100','-ar','44100','-ac','2',tmp],check=True)
    out=os.path.join(W,f'line_{i:02d}.wav'); os.replace(tmp,out)  # 最终逐句落 配音/line_NN.wav（与 manifest/spec 一致）
    d=dur_of(out)
    if d<=0:
        d=dur_of(out)   # 重试一次：ffprobe 偶发管道/探测失败，不该把已合成的真实音频换成静音
    if d<=0:
        if STRICT_NO_PLACEHOLDER_AUDIO:
            try: os.remove(out)
            except OSError: pass
            sys.exit(f'⛔ 第{i}句({role}) 最终音频无法探测有效时长。混合路由禁止以静音占位继续；请修复已锁后端后重跑。')
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
        cast=_casting_entry(role)
        if cast and cast.get('voice_id'):
            return f"{casting_backend(cast)}:{cast.get('voice_id')}"
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
    # 逐句条目形状（含契约字段 voice_key=实际应用音色键；say 占位记 say:<声音名>#placeholder）见 voice_manifest.manifest_entry
    manifest=[vmf.manifest_entry(i, shots[i] if i<len(shots) else "", items[i][0], items[i][2], items[i][4], items[i][1],
                                 measured[i], starts[i], ends[i], gaps[i], f"line_{i:02d}.wav",
                                 VOICEMAP, USE_API, _voice_id_for(items[i][0]), _emo_applied(items[i][0],items[i][2]),
                                 i in placeholders) for i in range(n)]
    manifest_placeholder_rows = placeholder_rows(manifest)
    placeholder_line_count = len(manifest_placeholder_rows)
    out_dir=os.path.dirname(os.path.join(W,'voice_zh.wav'))
    _json.dump(manifest, open(os.path.join(out_dir,'时长清单.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    
    # --- Emotional Flow Analysis (Optimization Point 3) ---
    try:
        from voice_analysis import analyze_emotion_flow
        emotion_flow_path = os.path.join(out_dir, 'emotion_flow.json')
        analyze_emotion_flow(W, manifest, emotion_flow_path)
        print(f"   [opt] 情感能量流已提取 → emotion_flow.json")
    except Exception as e:
        print(f"   [warn] 情感能量流提取失败: {e}")

    # 时长清单 sidecar：记录配音时 voiceover.txt 的台词指纹 + 后端 + 时间。
    # validate_timings 用它抓"配音之后又改 voiceover.txt（改词/插句/删句）→ 清单/字幕/镜头时长过期"，
    # 这条失配链 delete_shot 的强制 gate 对账（只管删镜）覆盖不到。清单本体保持纯 list，不破坏下游消费。
    _meta_prov = ZS_LABEL if USE_ZS else 'MiniMax' if USE_MM else '火山' if USE_VOLC else 'say'
    _json.dump(
        {"kind":"n2d.voice_manifest_meta","voiceover_fingerprint":voiceover_fingerprint(VO),
         "lines":n,"placeholder_lines":placeholder_line_count,"provider":_meta_prov,"lang":LANG,
         "purpose":VOICE_PURPOSE,
         "duration_sec":round(sum(measured)+sum(gaps),3),
         "expected_duration_sec":round(sum(expected)+sum(gaps),3),
         "duration_anomaly_lines":[
             {"idx":i,"duration_sec":round(measured[i],3),"expected_sec":round(expected[i],3)}
             for i in range(n)
             if measured[i] > max(12.0, expected[i]*2.8) and len(re.findall(r'[\u3400-\u9fff]', items[i][1])) >= 5
         ],
         "generated_at":time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())},
        open(os.path.join(out_dir,'时长清单.meta.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)

if 'manifest_placeholder_rows' in globals() and manifest_placeholder_rows:
    placeholder_reason = placeholder_reason or f'{_meta_prov} 占位音色;非注册真实配音'
    if "先出视频后配音" in PROD_MODE:
        warn = (
            '⚠️ 占位提示: ' + placeholder_reason +
            '。当前不是有声朗读,仅供后配音模式 rough timing;可先推进无声视频,合成前必须换真实配音并拟合。'
        )
        requirement = (
            "本项目制作模式=先出视频后配音: 可用于分镜/字幕时间轴 rough preview 和无声视频前置制作；"
            "合成前换 CosyVoice/克隆/MiniMax 等真实配音重跑,再拟合到已锁镜头。"
        )
    else:
        warn = (
            '⚠️ 占位提示: ' + placeholder_reason +
            '。当前不是有声朗读,仅供出图前 rough timing;出图前请换真实配音重跑 n2d-voice。'
        )
        requirement = (
            "本项目不是后配音默认流程: 跨过出图前,换 CosyVoice/克隆/MiniMax 等真实配音重跑,"
            "并用真实时长回跑 n2d-script 阶段2。"
        )
    open(os.path.join(W,'_占位说明.md'),'w',encoding='utf-8').write(
        f"# 本地占位配音\n\n{warn}\n\n用途: 跑通分镜/字幕时间轴 rough preview。\n要求: {requirement}\n"
    )
    # 自我优化闭环：配音后端不可用→被迫静音占位，是「n2d-voice 适配层该优化」的现场信号。
    # 落 作品根/生产数据/优化信号.jsonl，由 n2d-review 流程自审(self_audit --work)读进差距清单。
    if placeholders:
        log_friction(ROOT, 'n2d-voice',
                     f'{len(placeholders)}/{n} 句静音占位（非有声配音）：{placeholder_reason}',
                     kind='workaround', stage='配音', episode=EP,
                     evidence=os.path.join('合成', EP, '配音', '_占位说明.md'),
                     proposed='render_voice 缺真实后端时早探活并提示安装/换后端；或在 references/backends.md 补可跑通道',
                     severity='warn')

if LANG == 'zh' and os.environ.get('N2D_UPDATE_PROGRESS', '1') != '0':
    prog = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'n2d', 'progress.py'))
    try:
        # 占位判定走单一真值源：不仅静音回退算占位，say 占位级音色（voice_key=say:...）
        # 也算——否则 say 有声会误写 ✅，而 finalize/validate 用同一谓词判 12/12 占位、口径打架。
        _too_slow = (sum(measured)+sum(gaps)) > max(180.0, (sum(expected)+sum(gaps))*2.8)
        progress_value = '⏳rough' if (GUIDE_PURPOSE or manifest_is_placeholder(manifest) or _too_slow) else '✅'
        subprocess.run(['python3', prog, 'set', ROOT, EP, '配音', progress_value], check=False)
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
    meta={"lines": n, "placeholder_lines": len(placeholders), "purpose": VOICE_PURPOSE}
)

print(f"配音 {LANG}: {n} 句（purpose={VOICE_PURPOSE}，后端={ZS_LABEL if USE_ZS else 'MiniMax' if USE_MM else '火山' if USE_VOLC else 'say'}，顺序拼接 gap={GAP}s+钩子留拍，无压速）→ voice_{LANG}.wav")
