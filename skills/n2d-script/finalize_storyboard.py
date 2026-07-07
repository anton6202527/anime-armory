#!/usr/bin/env python3
# 配音时长 → 定稿：时长清单.json(+现有en字幕文本) → 重定时 字幕_中文.srt[+字幕_英文.srt] + 镜头时长.json
# 用法: finalize_storyboard.py <作品根> <第N集> [gap]
#   [gap] 仅对无 start/end 的旧清单回退路径生效；render_voice 现恒写 start/end/gap_after，新清单忽略它。
#   字幕语言看 ../skills/n2d/references/选择点与偏好.md 的「字幕语言」选择点：默认仅中文；中英双语/仅英文用 SUB_LANG=zh,en（或 en）开启。
#   未设 SUB_LANG 时：已存在非占位 字幕_英文.srt 译文就一并重定时，否则只产中文。
import sys, os, re, json, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'n2d', '_lib'))
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

def manifest_spans(manifest, gap=0.4):
    """Return [(start, end, gap_after)] using the same timing model as build()."""
    if manifest and all('start' in r and 'end' in r for r in manifest):
        return [(float(r['start']), float(r['end']), float(r.get('gap_after',0.0))) for r in manifest]
    # 旧 manifest 无真实时间轴时，按 render_voice 的留拍模型重建。
    HG={'end':1.0,'climax':0.7,'hook':0.6}
    spans=[]; t=0.0; last=len(manifest)-1
    for i,r in enumerate(manifest):
        d=float(r["时长"]); g=0.0 if i==last else HG.get(r.get("钩子","") or "", gap)
        spans.append((t, t+d, g)); t=t+d+g
    return spans

def build(manifest, en_texts, gap=0.4):
    zh=[]; en=[]; shots={}
    # 优先消费 render_voice 写入的真实时间轴(start/end/gap_after)；旧 manifest 无则按同一套 HOOK_GAP 模型重建
    if manifest:
        spans = manifest_spans(manifest, gap)
    else:
        spans = []
    for i,row in enumerate(manifest):
        start,end,gap_after=spans[i]
        zh.append(f"{i+1}\n{_ts(start)} --> {_ts(end)}\n{_wrap_zh(_clean_punct(row.get('文本','')))}\n")
        etxt=en_texts[i] if i<len(en_texts) else ""
        en.append(f"{i+1}\n{_ts(start)} --> {_ts(end)}\n{_wrap_en(_clean_en(etxt))}\n")
        sh=row.get("镜头","")
        shots[sh]=shots.get(sh,0.0)+(end-start)+gap_after  # 镜头占屏=台词时长+其后留拍；∑镜头 == voice.wav 时长
    shots={k:round(v,3) for k,v in shots.items()}
    return "\n".join(zh), "\n".join(en), shots

def sync_storyboard_durations_from_manifest(root, ep, manifest, gap=0.4):
    """Backfill storyboard clip durations from voiceover_indices after voice timing changes.

    validate_timings.py treats storyboard clips[].duration as the video time budget.
    If finalize updates only 镜头时长.json, the next gate fails or, worse, old clip
    durations leak into video generation. This sync is best-effort and only touches
    clips that explicitly declare 1-based voiceover_indices.
    """
    sb_p = os.path.join(root, '脚本', ep, 'storyboard.json')
    empty = {'duration': 0, 'frame_contract': 0, 'timeline': 0}
    if not os.path.isfile(sb_p):
        return empty
    try:
        data = json.load(open(sb_p, encoding='utf-8'))
    except (OSError, ValueError):
        return empty
    clips = data.get('clips')
    if not isinstance(clips, list):
        return empty
    spans = manifest_spans(manifest, gap)
    row_durations = [max(0.0, end - start) + max(0.0, gap_after) for start, end, gap_after in spans]
    duration_changed = 0
    frame_contract_changed = 0
    for clip in clips:
        if not isinstance(clip, dict):
            continue
        frame_contract_changed += normalize_clip_frame_contract(clip)
        indices = clip.get('voiceover_indices')
        if not isinstance(indices, list) or not indices:
            continue
        total = 0.0
        for raw in indices:
            try:
                idx = int(raw)
            except (TypeError, ValueError):
                continue
            if 1 <= idx <= len(row_durations):
                total += row_durations[idx - 1]
        if total <= 0:
            continue
        new_duration = round(total, 3)
        old = clip.get('duration')
        try:
            same = abs(float(old) - new_duration) < 0.001
        except (TypeError, ValueError):
            same = False
        if not same:
            clip['duration'] = new_duration
            duration_changed += 1
    timeline_changed, total_duration = normalize_storyboard_timeline(clips)
    try:
        total_same = abs(float(data.get('total_duration')) - total_duration) < 0.001
    except (TypeError, ValueError):
        total_same = False
    if not total_same:
        data['total_duration'] = total_duration
        timeline_changed += 1
    if duration_changed or frame_contract_changed or timeline_changed:
        json.dump(data, open(sb_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return {'duration': duration_changed, 'frame_contract': frame_contract_changed, 'timeline': timeline_changed}

def _same_second(value, expected):
    try:
        return abs(float(value) - expected) < 0.001
    except (TypeError, ValueError):
        return False

def normalize_storyboard_timeline(clips):
    """Rebuild cumulative start_sec/end_sec after clip durations change."""
    changed = 0
    cursor = 0.0
    for clip in clips:
        if not isinstance(clip, dict):
            continue
        dur = _clip_duration(clip)
        if dur is None:
            continue
        start = round(cursor, 3)
        end = round(cursor + dur, 3)
        if not _same_second(clip.get('start_sec'), start):
            clip['start_sec'] = start
            changed += 1
        if not _same_second(clip.get('end_sec'), end):
            clip['end_sec'] = end
            changed += 1
        cursor += dur
    return changed, round(cursor, 3)

def normalize_clip_frame_contract(clip):
    """Drop stale top-level frame paths contradicted by continuity policy."""
    if not isinstance(clip, dict):
        return 0
    continuity = clip.get('continuity')
    if not isinstance(continuity, dict):
        return 0
    changed = 0
    end_declared = any(k in continuity for k in ('need_endframe', 'need_end', 'endframe'))
    need_end = bool(continuity.get('need_endframe') or continuity.get('need_end') or continuity.get('endframe'))
    if end_declared and not need_end:
        for target in (clip, continuity):
            for key in ('endframe_png', 'lastframe_png', 'last_frame', 'endframe'):
                if key in target:
                    target.pop(key, None)
                    changed += 1
    midframe = continuity.get('midframe')
    anchors = continuity.get('anchors')
    has_mid = isinstance(midframe, dict) and bool(midframe)
    has_anchors = isinstance(anchors, list) and any(isinstance(a, dict) for a in anchors)
    mid_exempt = bool(continuity.get('midframe_exempt_reason')) or (isinstance(anchors, list) and not has_anchors and not has_mid)
    if mid_exempt and not has_mid and not has_anchors:
        for key in ('midframe_png', 'anchor_png'):
            if key in clip:
                clip.pop(key, None)
                changed += 1
    return changed

def normalize_storyboard_frame_contracts(root, ep):
    sb_p = os.path.join(root, '脚本', ep, 'storyboard.json')
    if not os.path.isfile(sb_p):
        return 0
    try:
        data = json.load(open(sb_p, encoding='utf-8'))
    except (OSError, ValueError):
        return 0
    clips = data.get('clips')
    if not isinstance(clips, list):
        return 0
    changed = 0
    for clip in clips:
        changed += normalize_clip_frame_contract(clip)
    if changed:
        json.dump(data, open(sb_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return changed

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
    # 缺 duration 的 clip 不静默丢（会变 0 长镜头·无时间预算出视频）——直接报错点名 clip。
    shots = {}
    for i, c in enumerate(clips, 1):
        if not isinstance(c, dict):
            continue
        dur = _clip_duration(c)
        key = str(c.get('镜头') or c.get('id') or c.get('label') or f'clip{i}')
        if dur is None:
            raise ValueError(f"clip「{key}」缺可解析的 duration（duration/duration_sec/时长/seconds 之一）——分镜设计时按脚本规划填 Clip duration。")
        shots[key] = round(shots.get(key, 0.0) + dur, 3)
    return shots

def _storyboard_subtitle_lines(clip):
    """从 storyboard clip 读取计划字幕行；最终成片仍以 whisperx 词级对齐为准。"""
    for key in ("subtitle_lines", "voiceover_lines", "lines"):
        value = clip.get(key)
        if isinstance(value, list):
            lines = [str(x).strip() for x in value if str(x).strip()]
            if lines:
                return lines
        if isinstance(value, str) and value.strip():
            return [x.strip() for x in re.split(r"\n+", value) if x.strip()]
    return []

def build_planned_srt_from_storyboard(clips):
    # 原生音画：阶段2仍需要给剪辑/审看一个中文字幕草稿；它是脚本计划时间轴，不冒充最终口型字幕。
    cues = []
    t = 0.0
    idx = 1
    for i, c in enumerate(clips, 1):
        if not isinstance(c, dict):
            continue
        dur = _clip_duration(c)
        key = str(c.get('镜头') or c.get('id') or c.get('label') or f'clip{i}')
        if dur is None:
            raise ValueError(f"clip「{key}」缺可解析的 duration（duration/duration_sec/时长/seconds 之一）——无法生成计划字幕。")
        lines = _storyboard_subtitle_lines(c)
        if not lines:
            t += dur
            continue
        span = max(0.8, dur / len(lines))
        for j, line in enumerate(lines):
            start = t + j * span
            end = t + dur if j == len(lines) - 1 else min(t + dur, start + span)
            if end <= start:
                end = start + 0.8
            cues.append(f"{idx}\n{_ts(start)} --> {_ts(end)}\n{_wrap_zh(_clean_punct(line))}\n")
            idx += 1
        t += dur
    return "\n".join(cues)

def _parse_srt_texts(path):
    out=[]
    if not os.path.exists(path): return out
    for b in re.split(r'\n\s*\n', open(path,encoding='utf-8').read().strip()):
        ls=[l for l in b.splitlines() if l.strip()]
        if len(ls)>=3: out.append(' '.join(ls[2:]))
    return out

# ── 投放→生成输入闭环（读端）：n2d-feedback 把 A/B 胜出的开场/断点写成机器可读先验，
#    阶段2 finalize 读它做开场/断点设计先验（第一方实测先验：本线投放实测，优先于通用经验）。
#    存在才读、缺则 no-op（向后兼容）；不臆造、不静默吞——读到就落 applied_creative_priors 证据 + 人可见提示。
CREATIVE_PRIORS_KIND = 'n2d_creative_priors'  # 与 n2d-feedback 同一真值（本线自定义·不进共享常量）
CREATIVE_PRIORS_FILENAME = 'creative_priors.json'

def load_creative_priors(root):
    """读 生产数据/creative_priors.json；缺/坏/kind 不符 → None（no-op，向后兼容）。"""
    path = os.path.join(root, '生产数据', CREATIVE_PRIORS_FILENAME)
    if not os.path.isfile(path):
        return None
    try:
        data = json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get('kind') != CREATIVE_PRIORS_KIND:
        return None
    priors = data.get('priors')
    if not isinstance(priors, dict) or not priors:
        return None  # 文件在但无胜出维度（样本不足）→ 等同无先验
    return data

def _adopted_variant(sb, field):
    """从 storyboard 读 阶段2 声明的本维度采用变体 + 理由。无声明→(None,'')。纯函数·可测。

    约定字段 `creative_variants_used`（兼容 `creative_variants`）：{field: {variant, reason?}} 或 {field: "变体名"}。"""
    cv = (sb or {}).get('creative_variants_used') or (sb or {}).get('creative_variants') or {}
    rec = cv.get(field) if isinstance(cv, dict) else None
    if isinstance(rec, dict):
        return (str(rec.get('variant') or rec.get('used') or rec.get('value') or '').strip(),
                str(rec.get('reason') or rec.get('why') or '').strip())
    if isinstance(rec, str):
        return rec.strip(), ''
    return None, ''

def creative_priors_evidence(data, sb=None):
    """先验 → applied_creative_priors 证据，**按 storyboard 真验证采纳**（非无脑盖章）。纯函数·可测。

    F2（2026-06-26 修真闭环）：此前每个维度无条件 status='applied'，让 beat_audit --strict 的
    creative_prior_not_acknowledged 形同虚设——跑一下 finalize 就「已确认」，第一方投放信号被橡皮图章吞掉。
    现按 storyboard 声明的 `creative_variants_used[field]` 真验证：采用胜出变体=applied；采用他变体+写理由
    =rejected(可解释)；采用他变体无理由 / 未声明=pending（beat_audit --strict 会拦，交分析师真决策）。
    **不自动改写内容**——尊重 analyst-in-loop（2026 SOTA：自动闭环尚不成立，结构化人审在环才是前沿）。"""
    priors = data.get('priors') or {}
    metrics = {}
    decisions = {}
    for field, p in priors.items():
        if not isinstance(p, dict):
            continue
        winner = str(p.get('winner') or '').strip()
        adopted, reason = _adopted_variant(sb, field)
        metrics[field] = {'winner': winner, 'paired_lift': p.get('paired_lift'),
                          'primary_metric': p.get('primary_metric'), 'n': p.get('n')}
        if adopted and winner and adopted == winner:
            decisions[field] = {'status': 'applied', 'winner': winner, 'adopted_variant': adopted,
                                'reason': 'storyboard 采用了 A/B 胜出变体', 'verified': True}
        elif adopted and winner and adopted != winner and reason:
            decisions[field] = {'status': 'rejected', 'winner': winner, 'adopted_variant': adopted,
                                'rejected_reason': reason, 'verified': True}
        elif adopted and winner and adopted != winner:
            decisions[field] = {'status': 'pending', 'winner': winner, 'adopted_variant': adopted,
                                'reason': '采用了非胜出变体但未写理由——采用胜出变体，或在 creative_variants_used 写 reason',
                                'verified': False}
        else:
            decisions[field] = {'status': 'pending', 'winner': winner,
                                'reason': 'storyboard 未在 creative_variants_used 声明本维度采用哪个变体——采用胜出变体或写拒绝理由',
                                'verified': False}
    return {
        'source': CREATIVE_PRIORS_FILENAME,
        'priors_generated_at': data.get('generated_at'),
        'prior_metrics': metrics,  # 改名（原 applied_creative_priors）：避免 beat_audit legacy 路径把元数据当 applied 自动盖章
        'decisions': decisions,
    }

def creative_priors_hint(data, ev=None):
    """人可见提示：胜出先验逐条点名 + 本集真验证的采纳状态（applied/rejected/⏳待决策），不静默吞。"""
    _LABEL = {
        'opening_variant': '开场',
        'cliffhanger_cut_variant': '集尾断点',
        'cover_variant': '封面',
        'title_variant': '标题文案',
    }
    priors = data.get('priors') or {}
    decisions = (ev or {}).get('decisions') or {}
    lines = [f"投放回灌先验（{data.get('generated_at') or '?'} 采集，A/B paired-lift 胜出·建议先验）："]
    pending = []
    for field, p in priors.items():
        if not isinstance(p, dict):
            continue
        label = _LABEL.get(field, field)
        lift = p.get('paired_lift')
        lift_s = f"+{lift*100:.1f}%" if isinstance(lift, (int, float)) else '—'
        st = (decisions.get(field) or {}).get('status', 'pending')
        mark = {'applied': '✅采用', 'rejected': '↩拒绝(有理由)', 'pending': '⏳待决策'}.get(st, st)
        lines.append(f"  - {label}优先复用 `{p.get('winner')}`：同集 paired-lift {lift_s}（{p.get('primary_metric')}，n={p.get('n')}）[{mark}]")
        if st == 'pending':
            pending.append(label)
    if pending:
        lines.append(f"  ⚠️ 未决策维度：{('、'.join(pending))}——在 storyboard.json 写 `creative_variants_used`:"
                     " {字段:{variant:采用的变体, reason?:不采用胜出时的理由}}，否则 beat_audit --strict 会拦"
                     "（投放胜出信号不能被橡皮图章吞掉）。")
    else:
        lines.append("  → 各维度均已真验证采纳/拒绝；设计下一批开场与集尾断点优先参考已被投放数据验证的胜出变体。")
    return "\n".join(lines)


def write_shot_intent_best_effort(root, ep):
    """StageC: finalize 后重建逐镜意图黑板。失败只提示，不阻断定稿。"""
    try:
        from n2d_intent import write_shot_intent
        write_shot_intent(root, ep)
        print("  逐镜意图黑板已重建 → 脚本/%s/shot_intent.json（作者可在 allowed_evolution field-tag 声明有意演进）" % ep)
    except Exception as _e:
        print(f"  （shot_intent 黑板重建跳过：{_e}）")

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
    # 投放回灌先验（闭环读端）：存在才读，缺则 None（no-op，向后兼容）。两条定稿路径末尾都落证据+提示。
    priors = load_creative_priors(root)
    def _apply_priors():
        if not priors:
            return
        # F2：读 storyboard 真验证采纳（非无脑盖章）。缺 storyboard → 全维 pending（交分析师决策）。
        sb = None
        try:
            sb = json.load(open(os.path.join(root,'脚本',ep,'storyboard.json'),encoding='utf-8'))
        except (OSError, ValueError):
            sb = None
        ev = creative_priors_evidence(priors, sb)
        json.dump(ev, open(os.path.join(root,'脚本',ep,'applied_creative_priors.json'),'w',encoding='utf-8'),
                  ensure_ascii=False, indent=2)
        print(creative_priors_hint(priors, ev))
    # 时长清单一律落 合成/（render_voice 与制作模式无关；出视频/ 为已废弃历史路径的兜底）——走 n2d_route 单一真值源
    man_p = manifest_path(root, ep)
    native_av = is_native_av(root)
    if not man_p:
        # 原生音画模式：说话镜由视频后端一次出同步音画，没有逐句配音清单——改从 storyboard 脚本时长定稿，不崩。
        if native_av:
            sb_p = os.path.join(root,'脚本',ep,'storyboard.json')
            if not os.path.isfile(sb_p):
                print('⛔ 原生音画模式但缺 storyboard.json，无法从脚本推镜头时长——请先 n2d-script 阶段2 分镜设计。'); sys.exit(2)
            clips = (json.load(open(sb_p,encoding='utf-8')) or {}).get('clips') or []
            try:
                shots = build_from_storyboard(clips)
                zh_srt = build_planned_srt_from_storyboard(clips)
            except ValueError as e:
                print('⛔ 原生音画定稿失败：'+str(e)); sys.exit(2)
            if not shots:
                print('⛔ 原生音画模式：storyboard.json clips 缺 duration，无法定稿镜头时长——分镜设计时按脚本规划填 Clip duration。'); sys.exit(2)
            json.dump(shots, open(os.path.join(root,'脚本',ep,'镜头时长.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
            if zh_srt.strip():
                open(os.path.join(root,'脚本',ep,'字幕_中文.srt'),'w',encoding='utf-8').write(zh_srt)
            print(f"原生音画定稿: 从 storyboard 取 {len(shots)} 镜时长 → 镜头时长.json。")
            if zh_srt.strip():
                print("  已按 storyboard 台词生成计划字幕_中文.srt；最终成片仍需 whisperx 词级对齐。")
            else:
                print("  storyboard 未提供 subtitle_lines/voiceover_lines；最终字幕请用 whisperx 对成片词级对齐。")
            _apply_priors()
            frame_contract_changed = normalize_storyboard_frame_contracts(root, ep)
            if frame_contract_changed:
                print(f"  storyboard.json 已清理 {frame_contract_changed} 个与 continuity 矛盾的旧帧路径。")
            write_shot_intent_best_effort(root, ep)
            sys.exit(0)
        print('⛔ 缺 时长清单.json（合成/'+ep+'/配音/ 或 出视频/'+ep+'/配音/）——请先 n2d-voice 配音。'); sys.exit(2)
    manifest=json.load(open(man_p,encoding='utf-8'))
    # 占位闸门：占位音色时长是估算值（与真实配音差 20~40%），定稿到镜头时长后会污染故事板 Clip 时长 → 出视频按错时长生成 → 大返工。
    # render_voice 已把占位句标 "占位":true；这里默认拒绝定稿，仅 rough preview 可用 FINALIZE_ALLOW_PLACEHOLDER=1 放行。
    ph=placeholder_indices(manifest)
    # 原生音画模式下，配音清单只覆盖旁白/非说话镜；占位不作硬闸（说话镜不靠它定时）。
    if ph and not native_av and os.environ.get('FINALIZE_ALLOW_PLACEHOLDER','')!='1':
        print('⛔ 拒绝定稿：本集配音仍是占位音色（'+str(len(ph))+'/'+str(len(manifest))+' 句，idx='+','.join(map(str,ph[:10]))+('…' if len(ph)>10 else '')+'）。')
        print('   占位时长是估算值，定稿后会锁进镜头时长.json/故事板 Clip 时长 → 出视频按错时长生成 → 返工。')
        print('   出图/出视频前务必：n2d-voice '+root+' '+ep+' 换真实配音（CosyVoice/克隆/MiniMax）重跑，再回跑本步。')
        print('   仅想跑通时间轴 rough preview：FINALIZE_ALLOW_PLACEHOLDER=1 python3 finalize_storyboard.py ...（产物不可用于正式出视频）')
        sys.exit(2)
    en_path=os.path.join(root,'脚本',ep,'字幕_英文.srt')
    en_texts=_parse_srt_texts(en_path)
    placeholder_en = _is_placeholder_en_texts(en_texts)
    if placeholder_en:
        en_texts=[]
    zh_srt,en_srt,shots=build(manifest,en_texts,gap)
    open(os.path.join(root,'脚本',ep,'字幕_中文.srt'),'w',encoding='utf-8').write(zh_srt)
    # 字幕语言是投放选择(见 ../skills/n2d/references/选择点与偏好.md)，不写死：默认仅中文(国内投放)。
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
    synced = sync_storyboard_durations_from_manifest(root, ep, manifest, gap)
    if synced.get('duration'):
        print(f"  storyboard.json 已按 voiceover_indices 回填 {synced.get('duration')} 个 Clip duration，并更新 total_duration。")
    if synced.get('timeline'):
        print(f"  storyboard.json 已同步 {synced.get('timeline')} 处 Clip start_sec/end_sec 时间轴。")
    if synced.get('frame_contract'):
        print(f"  storyboard.json 已清理 {synced.get('frame_contract')} 个与 continuity 矛盾的旧帧路径。")
    _apply_priors()
    # 逐镜意图黑板生产者（StageC）：分镜定稿后重建 shot_intent.json，让作者 override 通道(allowed_evolution)
    # 真存在、且派生字段与最新 storyboard 同步（陈旧自失效靠镜数对账）。best-effort：缺/异常不挡定稿。
    write_shot_intent_best_effort(root, ep)

if __name__=='__main__': main()
