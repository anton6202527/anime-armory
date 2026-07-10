#!/usr/bin/env bash
# 合成成片：视频/clips + (可选)配音轨 + BGM + 烧字幕 → 成片_第N集_{mode}.mp4
# 用法: bash compose.sh <作品根> <第N集> [bilingual|zh|en]
# 可选: BGMFILE=/path/to/music.mp3   传真实BGM(否则程序化占位)
#
# 交付矩阵子命令（G10·一母带→全平台）：成片母带产出后，从它派生 多比例 × 多时长 cutdown × 平台规格，
# 落 合成/交付/<集>/。读 _设置.md 的 目标平台/画幅/交付时长 选择点决定派生哪些规格；缺母带优雅报错。
#   bash compose.sh deliver <作品根> <第N集> [--run] [--aspects 9:16,16:9] [--durations 30s,15s]
set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
# 子命令分发：`deliver` → 交付矩阵（deliver.py），其余=合成主流程（默认）。
if [ "$1" = "deliver" ]; then
  shift
  exec python3 "$SKILL_DIR/deliver.py" "$@"
fi
ROOT="$1"; EP="$2"; MODE="${3:-bilingual}"
case "$MODE" in zh|bilingual) VLANG=zh;; en) VLANG=en;; *) echo "bad mode"; exit 1;; esac
BGMFILE="${BGMFILE:-}"
BGM_OFFSET="${BGM_OFFSET:-0}"   # 卡点：从 BGM 第几秒起播，让 drop/炸点落在爽点画面那一帧（导演节奏.md §五）
# 可调参数（默认=原行为）：转码质量 + BGM ducking。快速粗剪 VIDEO_CRF=26 VIDEO_PRESET=ultrafast；快节奏压狠 DUCK_RATIO=12；文艺温和 DUCK_RATIO=4
VIDEO_CRF="${VIDEO_CRF:-18}"; VIDEO_PRESET="${VIDEO_PRESET:-medium}"
DUCK_THRESHOLD="${DUCK_THRESHOLD:-0.05}"; DUCK_RATIO="${DUCK_RATIO:-8}"; DUCK_ATTACK="${DUCK_ATTACK:-20}"; DUCK_RELEASE="${DUCK_RELEASE:-400}"
# 张力感知 BGM 增益包络（爽点抬/细节压）：传 ffmpeg volume eval 表达式即按 Clip 张力随时间变 BGM 基准音量。
# 空=原固定行为(0.9/0.85)。生成：BGM_GAIN_EXPR="$(python3 tension_mix.py <作品根> 第N集 --expr)"
BGM_GAIN_EXPR="${BGM_GAIN_EXPR:-}"
if [ -n "$BGM_GAIN_EXPR" ]; then
  BGM_VOL_VOICE="volume='${BGM_GAIN_EXPR}':eval=frame"; BGM_VOL_NOVOICE="$BGM_VOL_VOICE"
  echo "BGM ducking：张力感知包络（按 Clip rhythm 抬/压）"
else
  BGM_VOL_VOICE="volume=0.9"; BGM_VOL_NOVOICE="volume=0.85"
fi
KEEP_CLIP_AUDIO="${KEEP_CLIP_AUDIO:-0}"  # 默认在 compose 工作缓存丢弃 AI clip 原生音频；设 1 才低音量混入环境音底。源 clip 不改写。
J_CUT_SEC="${J_CUT_SEC:-0.25}"           # 默认轻量 J-cut：基于 line_*.wav 提前入声；设 0 关闭。正面口型特写慎用
VIDEO_NATIVE_AUDIO_POLICY="${VIDEO_NATIVE_AUDIO_POLICY:-}"
# 使用 n2d/_lib/n2d_settings.py 的单一真值源
_GET_SETTING="PYTHONPATH=\"$SKILL_DIR/../n2d/_lib\" python3 -c \"import sys; from n2d_settings import get_setting; print(get_setting(sys.argv[1], sys.argv[2], sys.argv[3]))\""
if [ -z "$VIDEO_NATIVE_AUDIO_POLICY" ]; then
  VIDEO_NATIVE_AUDIO_POLICY=$(eval $_GET_SETTING "\"$ROOT\" \"视频原生音轨\" \"丢弃\"")
fi

SUBTITLE_SIZE_SETTING=$(eval $_GET_SETTING "\"$ROOT\" \"字幕字号\" \"小\"")
if [ -z "${ZH_SIZE:-}" ] && [ -z "${EN_SIZE:-}" ]; then
  case "$SUBTITLE_SIZE_SETTING" in
    小|small) export ZH_SIZE=38 EN_SIZE=28 ;;
    中|medium) export ZH_SIZE=46 EN_SIZE=32 ;;
    大|large) export ZH_SIZE=50 EN_SIZE=34 ;;
    *) : ;;
  esac
fi
AI_LABEL_MODE="${N2D_AI_LABEL_MODE:-$(eval $_GET_SETTING "\"$ROOT\" \"AI显式角标\" \"仅元数据\"")}"
if [ "$KEEP_CLIP_AUDIO" = "1" ] && [ "$VIDEO_NATIVE_AUDIO_POLICY" = "丢弃" ]; then
  echo "⚠️ 旧环境变量 KEEP_CLIP_AUDIO=1 覆盖了权威设置「视频原生音轨=丢弃」→ 改用「低音量混入环境声」。若非本意请 unset KEEP_CLIP_AUDIO 或在 _设置.md 显式写「视频原生音轨」。"
  VIDEO_NATIVE_AUDIO_POLICY="低音量混入环境声"
fi

# 制作模式=原生音画：说话镜的台词由视频后端原生生成、就在 clip 自带音轨里——绝不能丢弃，否则台词没了。
# 默认从单一真值源 n2d_const.PRODUCTION_MODE_DEFAULT 取（当前=先出视频后配音）——别在此硬编旧默认
# 「配音先行」：未写「制作模式」的原生音画项目会被误判成配音先行→跳过下面的保留台词轨守卫→台词丢失。
PROD_MODE_DEFAULT=$(PYTHONPATH="$SKILL_DIR/../n2d/_lib" python3 -c "from n2d_const import PRODUCTION_MODE_DEFAULT; print(PRODUCTION_MODE_DEFAULT)" 2>/dev/null || echo "先出视频后配音")
PROD_MODE=$(eval $_GET_SETTING "\"$ROOT\" \"制作模式\" \"$PROD_MODE_DEFAULT\"")
NATIVE_AV_MODE=$(python3 -c "m='$PROD_MODE'; print('1' if ('原生音画' in m or 'native_av' in m.lower()) else '0')")
if [ "$NATIVE_AV_MODE" = "1" ] && [ -z "${VIDEO_NATIVE_AUDIO_POLICY_EXPLICIT:-}" ] && [ "$VIDEO_NATIVE_AUDIO_POLICY" = "丢弃" ]; then
  echo "⚠️ 制作模式=原生音画：clip 自带原生人声台词，自动改 视频原生音轨=保留原片音轨（避免丢台词）。如确需丢弃请设 VIDEO_NATIVE_AUDIO_POLICY_EXPLICIT=1。"
  VIDEO_NATIVE_AUDIO_POLICY="保留原片音轨"
fi
case "$VIDEO_NATIVE_AUDIO_POLICY" in
  丢弃|discard|none|None) NATIVE_AUDIO_MODE="discard"; CLIP_AUDIO_GAIN="${CLIP_AUDIO_GAIN:-0}" ;;
  低音量混入环境声|低音量环境声|环境声|ambience|mix|low) NATIVE_AUDIO_MODE="ambience"; CLIP_AUDIO_GAIN="${CLIP_AUDIO_GAIN:-0.35}" ;;
  保留原片音轨|保留|keep|preserve) NATIVE_AUDIO_MODE="keep"; CLIP_AUDIO_GAIN="${CLIP_AUDIO_GAIN:-1.0}" ;;
  *) echo "bad 视频原生音轨: $VIDEO_NATIVE_AUDIO_POLICY（可选：丢弃 / 低音量混入环境声 / 保留原片音轨）"; exit 1 ;;
esac
# 画幅选择点（不写死，对齐 skills/n2d/references/选择点与偏好.md「画幅」）：env ASPECT(9:16|16:9) > _设置.md「画幅」> 默认 9:16(竖屏)
if [ "${ASPECT:-}" = "16:9" ]; then GEO="1920 1080"
elif [ "${ASPECT:-}" = "9:16" ]; then GEO="1080 1920"
else
  GEO=$(python3 -c "import re,os;p=os.path.join('$ROOT','_设置.md');t=open(p,encoding='utf-8').read() if os.path.isfile(p) else '';print('1920 1080' if re.search(r'画幅\s*[:：]\s*16\s*[:：]\s*9',t) else '1080 1920')")
fi
PXW=${GEO% *}; PXH=${GEO#* }
# clips 是「出视频」的唯一产物，仍读 出视频/；配音/成片/中间件都在「合成」文件夹下。
VID="$ROOT/出视频/$EP/视频"
if [ -f "$SKILL_DIR/../n2d-video/scripts/materialize_shared_clips.py" ]; then
  python3 "$SKILL_DIR/../n2d-video/scripts/materialize_shared_clips.py" "$ROOT" "$EP"
fi
# 默认用 n2d-voice 产的整轨；`制作模式=先出视频后配音` 时先跑 fit_voice_to_clips.py
# 把后期补录的真音拟合到已锁定视频镜头长，再用 VOICEFILE 指向 voice_<lang>_fitted.wav。
VOICE="${VOICEFILE:-$ROOT/合成/$EP/配音/voice_${VLANG}.wav}"
ZH_SRT="$ROOT/脚本/$EP/字幕_中文.srt"; EN_SRT="$ROOT/脚本/$EP/字幕_英文.srt"
W="$ROOT/合成/$EP/_work"; rm -rf "$W"; mkdir -p "$W"
OUT="$ROOT/合成/$EP/成片_${EP}_${MODE}.mp4"

[ -d "$VID" ] || { echo "缺 $VID（先 n2d-video）"; exit 1; }
CLIPS=("$VID"/*.mp4)
[ -e "${CLIPS[0]}" ] || { echo "$VID 无 clip"; exit 1; }

# 占位配音守门：除非显式用 VOICEFILE 指了别的轨（如拟合轨），否则不许把占位音色烧进成片。
# `制作模式=先出视频后配音` 时：先 n2d-voice 补真音 → fit_voice_to_clips.py → VOICEFILE=拟合轨。
MAN_J="$ROOT/合成/$EP/配音/时长清单.json"
if [ -z "${VOICEFILE:-}" ] && [ -f "$MAN_J" ] && [ "${ALLOW_PLACEHOLDER_COMPOSE:-0}" != "1" ]; then
  if PYTHONPATH="$SKILL_DIR/../n2d/_lib" python3 -c "import json,sys;from n2d_route import manifest_is_placeholder;sys.exit(0 if manifest_is_placeholder(json.load(open(sys.argv[1]))) else 1)" "$MAN_J"; then
    echo "⛔ 本集配音仍是占位音色，拒绝合成（占位轨与镜头时长不是真实时长，成片音画会错）。"
    echo "   · 配音先行：先 n2d-voice 换真实配音（CosyVoice/克隆/MiniMax）重跑。"
    echo "   · 先出视频后配音模式：n2d-voice 补真音后，跑 fit_voice_to_clips.py 出拟合轨，再 VOICEFILE=…/voice_${VLANG}_fitted.wav 合成。"
    echo "   · 仅要占位 rough preview：ALLOW_PLACEHOLDER_COMPOSE=1 重跑（产物不可用于交付）。"
    exit 1
  fi
fi

echo "=== [1/6] 时域插帧/裁切 + 统一规格 ${PXW}x${PXH}/30fps（含 clip 级缓存）==="
SOURCE_LIST="$W/source_clips.txt"
python3 - "$ROOT" "$EP" "$VID" "$SOURCE_LIST" "$SKILL_DIR" "$PXW" "$PXH" <<'PY'
import glob, json, os, re, subprocess, sys
root, ep, vid, out_path, skill_dir, pxw, pxh = sys.argv[1:8]
try:
    pxw, pxh = int(pxw), int(pxh)
except ValueError:
    pxw, pxh = 0, 0
# 打斗命中帧微震屏（P2·保时长·拼进本就发生的逐 clip 重编码·零额外成本）。导入失败→不加震屏。
sys.path.insert(0, os.path.join(skill_dir, "scripts"))
try:
    import combat_punch as _cp
except Exception:
    _cp = None
def _punch(clip):
    if _cp is None or not pxw or not pxh:
        return ""
    try:
        return _cp.clip_punch_fragment(clip, pxw, pxh)
    except Exception:
        return ""

def _clip_file_globs(vid, cid, *, part=False):
    suffix = "*part*.mp4" if part else "*.mp4"
    patterns = [os.path.join(vid, f"*{cid}*{suffix}")]
    m = re.search(r"clip[_ -]?0*(\d+)", str(cid or ""), re.I)
    if m:
        num = int(m.group(1))
        tokens = (f"Clip_{num:02d}", f"Clip{num:02d}", f"CLIP_{num:02d}", f"CLIP{num:02d}")
        patterns.extend(os.path.join(vid, f"*{token}*{suffix}") for token in tokens)
    out = []
    seen = set()
    for pat in patterns:
        for path in sorted(glob.glob(pat)):
            if path not in seen:
                seen.add(path)
                out.append(path)
    return out

def _ffprobe_duration(path):
    try:
        raw = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        value = float(raw)
        return value if value > 0 else None
    except Exception:
        return None

def _video_manifest_index(root, ep):
    by_target = {}
    by_clip = {}
    pattern = os.path.join(root, "生产数据", f"video_batch_{ep}_*.json")
    for manifest_path in sorted(glob.glob(pattern)):
        try:
            payload = json.load(open(manifest_path, encoding="utf-8"))
        except Exception:
            continue
        for item in payload.get("items") or []:
            if not isinstance(item, dict):
                continue
            target = os.path.basename(str(item.get("target") or ""))
            if target:
                by_target[target] = item
            clip_id = str(item.get("clip") or "")
            if clip_id:
                by_clip[clip_id] = item
    return by_target, by_clip

manifest_by_target, manifest_by_clip = _video_manifest_index(root, ep)

def _manifest_item_for_path(path):
    name = os.path.basename(path)
    if name in manifest_by_target:
        return manifest_by_target[name]
    stem = os.path.splitext(name)[0]
    for target, item in manifest_by_target.items():
        if os.path.splitext(target)[0] == stem:
            return item
    return None

storyboard_path = os.path.join(root, "脚本", ep, "storyboard.json")
try:
    data = json.load(open(storyboard_path, encoding="utf-8"))
except Exception:
    data = {}

ordered = []
clips = data.get("clips") or []
if clips:
    for clip in clips:
        path = clip.get("video_out")
        if path:
            path = os.path.join(root, path)

        cid = clip.get("id")
        if cid:
            # 优先找 part 拆段 (automated split relay)
            parts = _clip_file_globs(vid, cid, part=True)
            if parts:
                try:
                    target_duration = float(clip.get("duration")) if clip.get("duration") not in (None, "", "None") else None
                except (TypeError, ValueError):
                    target_duration = None
                src_durations = [_ffprobe_duration(p) for p in parts]
                total_src = sum(d for d in src_durations if d)
                for p in parts:
                    # v2 直接消费 runner manifest 的 edit_target_duration；后端为了满足 4/5/6/8s
                    # 等离散档位多生成的尾巴只裁掉，不再按成片原始时长比例整段变速。
                    # 拆段子文件不加震屏（命中秒是相对整镜的，映射到 part 偏移过复杂·保守跳过）
                    part_duration = None
                    manifest_item = _manifest_item_for_path(p)
                    if manifest_item:
                        value = manifest_item.get("edit_target_duration")
                        if value in (None, "") and isinstance(manifest_item.get("duration_plan"), dict):
                            value = manifest_item["duration_plan"].get("edit_target_sec")
                        try:
                            part_duration = float(value) if value not in (None, "") else None
                        except (TypeError, ValueError):
                            part_duration = None
                    if part_duration is None and target_duration and total_src:
                        src_duration = src_durations[parts.index(p)] or (total_src / len(parts))
                        part_duration = target_duration * src_duration / total_src
                    ordered.append((p, f"{part_duration:.6f}" if part_duration else "None",
                                    "trim", ""))
                continue

            # 无拆段时，尝试精确匹配或模糊匹配
            if not path or not os.path.exists(path):
                cands = _clip_file_globs(vid, cid)
                if cands: path = cands[0]

        if path and os.path.exists(path):
            manifest_item = _manifest_item_for_path(path) or manifest_by_clip.get(str(cid or ""))
            duration = clip.get("duration", "None")
            speed_mode = clip.get("speed_mode", "trim")
            if manifest_item:
                duration = manifest_item.get("edit_target_duration")
                if duration in (None, "") and isinstance(manifest_item.get("duration_plan"), dict):
                    duration = manifest_item["duration_plan"].get("edit_target_sec")
                speed_mode = manifest_item.get("speed_mode", "trim")
            ordered.append((path, duration, speed_mode, _punch(clip)))
else:
    for p in sorted(glob.glob(os.path.join(vid, "*.mp4"))):
        ordered.append((p, "None", "trim", ""))

with open(out_path, "w", encoding="utf-8") as f:
    for p, d, s, pv in ordered:
        f.write(f"{p}\t{d}\t{s}\t{pv}\n")
PY

if [ ! -s "$SOURCE_LIST" ]; then
  echo "⛔ $VID 找不到对应 clip"
  exit 1
fi

CACHE="$ROOT/合成/$EP/_clipcache"; mkdir -p "$CACHE"
: > "$W/list.txt"
CLIPS=() # 重置 CLIPS 以确保后续读取原生音频的顺序也是排好的
while IFS=$'\t' read -r c dur speed_mode punch_vf; do
  [ -f "$c" ] || continue
  CLIPS+=("$c")
  key=$(python3 -c "import os,hashlib,sys;p=sys.argv[1];print(hashlib.md5(f'{os.path.basename(p)}:{os.path.getmtime(p)}:{sys.argv[2]}:{sys.argv[3]}:{sys.argv[4]}:{sys.argv[5]}'.encode()).hexdigest()[:16])" "$c" "${PXW}x${PXH}:${VIDEO_CRF}:${VIDEO_PRESET}" "$dur" "$speed_mode" "$punch_vf")
  clip_tag=$(python3 -c "import os,re,sys;name=os.path.basename(sys.argv[1]);m=re.search(r'(Clip[_ -]*0*\\d+)(?:[^A-Za-z0-9]+part\\s*0*(\\d+))?', name, re.I);base=(m.group(1).replace(' ','_').replace('-','_') if m else 'clip');part=(('_part'+m.group(2)) if (m and m.group(2)) else '');print((base+part).lower())" "$c")
  nf="$CACHE/${clip_tag}_n_${key}.mp4"
  
  if [ ! -f "$nf" ]; then
    TRIM_OPT=""
    SETPTS_OPT=""
    
    if [ -n "$dur" ] && [ "$dur" != "None" ]; then
      TRIM_OPT="-t $dur"
      if [ "$speed_mode" = "warp" ]; then
        SRC_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$c" || echo "")
        if [ -n "$SRC_DUR" ]; then
          FACTOR=$(python3 -c "print(round(float('$dur') / float('$SRC_DUR'), 4))" 2>/dev/null || echo "")
          if [ -n "$FACTOR" ]; then
            SETPTS_OPT="setpts=${FACTOR}*PTS,"
            echo "  ⏱️ 显式整段变速(Time-Warp): $(basename "$c") ($SRC_DUR s -> ${dur}s, ${FACTOR}x)"
          else
            echo "  ✂️ 精确裁切: $(basename "$c") -> ${dur}s"
          fi
        else
          echo "  ✂️ 精确裁切: $(basename "$c") -> ${dur}s"
        fi
      else
        echo "  ✂️ 精确裁切: $(basename "$c") -> ${dur}s"
      fi
    fi

    # [NEW] 动态色调匹配 (Color Match) - 缓解多模型混剪的色彩断层
    COLOR_FILTER=""
    if [ "${#CLIPS[@]}" -gt 1 ]; then
      # 以第一条 Clip 为基准参考色调
      REF_CLIP="${CLIPS[0]}"
      C_MATCH=$(python3 "$SKILL_DIR/scripts/color_match.py" "$c" "$REF_CLIP" 2>/dev/null || echo "")
      if [ -n "$C_MATCH" ]; then
        COLOR_FILTER=",${C_MATCH}"
        echo "  🎨 Color Match: $(basename "$c") 匹配基准色调"
      fi
    fi

    # 打斗命中帧微震屏（P2·保时长·拼进既有逐 clip -vf 链尾·零额外重编码）。
    # 只对 fight_exchange/magic_burst 且有命中秒的镜非空；crop 抖动在 PXWxPXH 上做再 scale 回原尺寸。
    PUNCH_FILTER=""
    [ -n "$punch_vf" ] && PUNCH_FILTER=",${punch_vf}"
    # 只在 compose 的规格化缓存中 -an；出视频目录里的 AI 原片保持不变。
    ffmpeg -nostdin -y -loglevel error -i "$c" \
      -vf "${SETPTS_OPT}scale=${PXW}:${PXH}:force_original_aspect_ratio=decrease,pad=${PXW}:${PXH}:(ow-iw)/2:(oh-ih)/2:black,fps=30${COLOR_FILTER}${PUNCH_FILTER},format=yuv420p" \
      $TRIM_OPT -c:v libx264 -preset "$VIDEO_PRESET" -crf "$VIDEO_CRF" -an "$nf.tmp.mp4" && mv "$nf.tmp.mp4" "$nf"
  else
    echo "  ♻ 复用规格化缓存 $(basename "$c") -> ${dur}s"
  fi
  echo "file '$nf'" >> "$W/list.txt"
done < "$SOURCE_LIST"

echo "=== [2/6] 拼接（按转场接缝：硬切/微溶解/缺空镜报警）==="
SB="$ROOT/脚本/$EP/storyboard.json"
# seam_concat.py：无溶解接缝时等价 concat -c copy；有溶解接缝才局部 xfade；内部 ffmpeg 失败已自回退。
# 兜底/溶解秒可用环境变量覆盖（SEAM_FALLBACK=硬切|微溶解|报警，默认硬切=旧行为；SEAM_DISSOLVE_SEC 默认 0.25）。
if ! python3 "$SKILL_DIR/seam_concat.py" --list "$W/list.txt" --out "$W/concat.mp4" \
      --storyboard "$SB" --fallback "${SEAM_FALLBACK:-硬切}" --dissolve-sec "${SEAM_DISSOLVE_SEC:-0.25}" \
      --report "$W/接缝报告.md"; then
  echo "⚠️ 接缝引擎不可用 → 回退 concat -c copy"
  ffmpeg -y -loglevel error -f concat -safe 0 -i "$W/list.txt" -c copy "$W/concat.mp4"
fi
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$W/concat.mp4")
echo "成片时长 ${DUR}s"

if [ -f "$VOICE" ] && [ -z "${VOICEFILE:-}" ] && [ -f "$MAN_J" ]; then
  if python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) > 0 else 1)" "$J_CUT_SEC"; then
    echo "=== [2.5/6] 可选 J-cut 配音轨（提前 ${J_CUT_SEC}s 入声）==="
    echo "注意：J-cut 只适合旁白/系统音/背身或侧脸转场；正面口型特写请保持 J_CUT_SEC=0。"
    # 优雅降级：旧清单缺 start/line_wav 等导致 J-cut 构建失败时，退回原整轨继续合成（不因 set -e 整体中断）。
    if python3 "$SKILL_DIR/build_jcut_voice.py" "$MAN_J" "$ROOT/合成/$EP/配音" "$J_CUT_SEC" "$DUR" "$W/voice_jcut.wav"; then
      VOICE="$W/voice_jcut.wav"
    else
      echo "⚠️ J-cut 构建失败（清单可能缺 start/line_wav 字段）→ 退回原配音轨继续合成：$VOICE"
    fi
  fi
fi

echo "=== [3/6] BGM ==="
if [ -n "$BGMFILE" ] && [ -f "$BGMFILE" ]; then
  echo "真实BGM: $BGMFILE (offset=${BGM_OFFSET}s)"; fo=$(python3 -c "print(max(0,$DUR-3))")
  ffmpeg -y -loglevel error -ss "$BGM_OFFSET" -stream_loop -1 -i "$BGMFILE" -t "$DUR" \
    -af "afade=t=in:d=2,afade=t=out:st=${fo}:d=3,aresample=44100" -ac 2 "$W/bgm.wav"
else
  echo "占位氛围乐"
  ffmpeg -y -loglevel error \
    -f lavfi -i "sine=frequency=55:duration=$DUR" -f lavfi -i "sine=frequency=110:duration=$DUR" -f lavfi -i "sine=frequency=164.81:duration=$DUR" \
    -filter_complex "[0:a][1:a][2:a]amix=inputs=3:normalize=0,tremolo=f=5:d=0.25,lowpass=f=380,aecho=0.8:0.7:60:0.3,volume='0.35+0.5*t/${DUR%.*}':eval=frame,alimiter=limit=0.9" \
    -ar 44100 -ac 2 "$W/bgm.wav"
fi

if [ "$NATIVE_AUDIO_MODE" != "discard" ]; then
  if [ "$NATIVE_AUDIO_MODE" = "keep" ] && [ -f "$VOICE" ]; then
    if [ "${ALLOW_DOUBLE_VOICE:-0}" != "1" ] && [ "${ALLOW_NATIVE_AV_VOICEOVER:-0}" != "1" ]; then
      echo "⛔ clip 原生音频策略=保留原片音轨，且检测到配音轨 $VOICE；正式合成会有双人声风险，已阻断。"
      echo "   · 配音先行：把 视频原生音轨 改为「丢弃」或「低音量混入环境声」。"
      echo "   · 原生音画 + 旁白层：先通过 compose gate/sidecar 确认配音轨仅为旁白，再显式 ALLOW_NATIVE_AV_VOICEOVER=1 重跑。"
      echo "   · 仅内部预览且自担风险：ALLOW_DOUBLE_VOICE=1 重跑。"
      exit 1
    fi
    echo "⚠️ 已显式允许保留原片音轨 + 配音轨（ALLOW_DOUBLE_VOICE/ALLOW_NATIVE_AV_VOICEOVER）；确认不会形成角色双人声。"
  fi
  echo "clip 原生音频：策略=${VIDEO_NATIVE_AUDIO_POLICY}（gain=${CLIP_AUDIO_GAIN}）"
  : > "$W/alist.txt"; i=0
  for c in "${CLIPS[@]}"; do
    if ffprobe -v error -select_streams a:0 -show_entries stream=index -of csv=p=0 "$c" | grep -q .; then
      ffmpeg -y -loglevel error -i "$c" -vn -t "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$c")" \
        -af "volume=${CLIP_AUDIO_GAIN},aresample=44100" -ar 44100 -ac 2 "$W/a$i.wav"
    else
      d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$c")
      ffmpeg -y -loglevel error -f lavfi -i "anullsrc=r=44100:cl=stereo" -t "$d" "$W/a$i.wav"
    fi
    echo "file 'a$i.wav'" >> "$W/alist.txt"; i=$((i+1))
  done
  ffmpeg -y -loglevel error -f concat -safe 0 -i "$W/alist.txt" -c copy "$W/clip_audio.wav"
else
  echo "clip 原生音频：策略=丢弃（避免原生台词与配音双人声）"
  ffmpeg -y -loglevel error -f lavfi -i "anullsrc=r=44100:cl=stereo" -t "$DUR" "$W/clip_audio.wav"
fi

echo "=== [3.5/6] V2A Foley 拟音 (Next Gen) ==="
FOLEY_WAV="$W/foley_mix.wav"
# 原生音画后端去双层：把已解析的 clip 原生音轨保留态 + 制作模式意图传给 foley_agent。
# 原生音画后端（Veo3.1/Kling3/Vidu Q3）自带同步音效，clip 音轨被保留时 foley_agent 自动抑制 compose foley。
# 强制叠加：FORCE_COMPOSE_FOLEY=1（环境变量自动继承，无需在此显式传）。
if [ "$NATIVE_AUDIO_MODE" != "discard" ]; then N2D_FOLEY_CLIP_AUDIO_PRESERVED=1; else N2D_FOLEY_CLIP_AUDIO_PRESERVED=0; fi
export N2D_FOLEY_CLIP_AUDIO_PRESERVED
export N2D_FOLEY_NATIVE_AV_INTENDED="$NATIVE_AV_MODE"
if python3 "$SKILL_DIR/scripts/foley_agent.py" "$ROOT" "$EP"; then
  echo "  🔊 Foley SFX 已就绪"
else
  ffmpeg -y -loglevel error -f lavfi -i "anullsrc=r=44100:cl=stereo" -t "$DUR" "$FOLEY_WAV"
fi

echo "=== [4/6] 系统面板母题 overlay + 字幕 PNG ==="
# 系统面板 overlay（穿越/系统流母题）：AI 出空光幕底框，等级/属性数值在此叠成清晰文字层。
# 无 motif_registry.json 或本集无 system_panel 镜 → render_panel 写空文件、行为与旧版逐字节一致。
: > "$W/panel_inputs.txt"; : > "$W/panel_vfilter.txt"
PANEL_BASE=4 SUB_W="$PXW" SUB_H="$PXH" python3 "$SKILL_DIR/render_panel.py" "$ROOT" "$EP" "$W" || \
  echo "⚠️ 系统面板 overlay 渲染失败 → 跳过（成片只缺面板数值层，不中断合成）"
# 空文件时 grep -c 打印 0 且 exit 1；命令替换赋值不触发 set -e，故不需 `|| echo 0`（那会双打印 0）。
NPANEL=$(grep -c . "$W/panel_inputs.txt" 2>/dev/null || true); NPANEL=${NPANEL:-0}
# 字幕可选：默认仅中文（finalize_storyboard 仅在有英文译文时才产 字幕_英文.srt），EN 缺失不算错。
# 注意 set -e：缺文件时 cp 会整体中断合成，故每个 cp 先判存在。render_subs.parse_srt 对缺轨已容错。
[ -f "$ZH_SRT" ] && cp "$ZH_SRT" "$W/zh.srt" || echo "（无中文字幕 $ZH_SRT，跳过）"
[ -f "$EN_SRT" ] && cp "$EN_SRT" "$W/en.srt" || true
# 复制时长清单供字幕样式分级（旁白/系统→灰小字，爽点→暖金大字）；缺则字幕全 normal
MANIFEST="$ROOT/合成/$EP/配音/时长清单.json"; [ -f "$MANIFEST" ] && cp "$MANIFEST" "$W/manifest.json" || true
# ffmpeg 输入序：0-3 固定(concat/bgm/clip_audio/foley) → 面板 PNG(从 4) → 字幕 PNG(从 4+NPANEL)。
# 有面板时字幕链从 [vpanel] 起（叠在面板之上）；无面板时从 [0:v] 起（与旧版一致）。
SUB_BASE=$((4+NPANEL))
if [ "$NPANEL" -gt 0 ]; then SUB_FIRST="[vpanel]"; else SUB_FIRST="[0:v]"; fi
PNG_INPUT_BASE=$SUB_BASE SUB_FIRST_INPUT="$SUB_FIRST" SUB_W="$PXW" SUB_H="$PXH" python3 "$SKILL_DIR/render_subs.py" "$W" "$MODE"
PNG_INPUTS=()
while IFS= read -r p; do [ -n "$p" ] && PNG_INPUTS+=(-i "$p"); done < "$W/panel_inputs.txt"
while IFS= read -r p; do [ -n "$p" ] && PNG_INPUTS+=(-i "$p"); done < "$W/inputs.txt"
NSUB=$(grep -c . "$W/inputs.txt" 2>/dev/null || true); NSUB=${NSUB:-0}; VIDX=$((4+NPANEL+NSUB))
# 合并 overlay 链：面板链([0:v]->[vpanel]) ; 字幕链([vpanel]->[v])；无面板时只字幕链。
SUB_VFILTER=$(cat "$W/vfilter.txt")
PANEL_VFILTER=$(cat "$W/panel_vfilter.txt" 2>/dev/null || true)
if [ -n "$PANEL_VFILTER" ]; then VFILTER="${PANEL_VFILTER};${SUB_VFILTER}"; else VFILTER="$SUB_VFILTER"; fi

echo "=== [5/6] 混音 + 烧字幕 ==="
if [ -f "$VOICE" ]; then
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" -i "$W/clip_audio.wav" -i "$FOLEY_WAV" "${PNG_INPUTS[@]}" -i "$VOICE" \
    -filter_complex "
      [${VIDX}:a]asplit=2[voxA][voxB];
      [voxA]volume=1.0[vox];
      [1:a]${BGM_VOL_VOICE}[bgm0];
      [bgm0][voxB]sidechaincompress=threshold=${DUCK_THRESHOLD}:ratio=${DUCK_RATIO}:attack=${DUCK_ATTACK}:release=${DUCK_RELEASE}[bgmduck];
      [2:a]volume=1.0[clip_a];
      [3:a]volume=1.0[foley];
      [clip_a][foley][bgmduck][vox]amix=inputs=4:normalize=0:duration=first:dropout_transition=0,dynaudnorm[a];
      ${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
elif [ "$NATIVE_AV_MODE" = "1" ] && [ "$NATIVE_AUDIO_MODE" != "discard" ]; then
  echo "（原生音画模式：使用 clip 原生音频作为侧链 ducking 源）"
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" -i "$W/clip_audio.wav" -i "$FOLEY_WAV" "${PNG_INPUTS[@]}" \
    -filter_complex "
      [2:a]asplit=2[sfx][sfxB];
      [1:a]${BGM_VOL_VOICE}[bgm0];
      [bgm0][sfxB]sidechaincompress=threshold=${DUCK_THRESHOLD}:ratio=${DUCK_RATIO}:attack=${DUCK_ATTACK}:release=${DUCK_RELEASE}[bgmduck];
      [3:a]volume=1.0[foley];
      [sfx][foley][bgmduck]amix=inputs=3:normalize=0:duration=first:dropout_transition=0,dynaudnorm[a];
      ${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
else
  echo "（无配音轨，纯 BGM+音效底+字幕）"
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" -i "$W/clip_audio.wav" -i "$FOLEY_WAV" "${PNG_INPUTS[@]}" \
    -filter_complex "
      [2:a]volume=1.0[clip_a];
      [3:a]volume=1.0[foley];
      [1:a]${BGM_VOL_NOVOICE}[bgm];
      [clip_a][foley][bgm]amix=inputs=3:duration=first:dropout_transition=0,dynaudnorm[a];
      ${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
fi


echo "=== [6/6] 完成: $OUT ==="
ls -la "$OUT"

# 主题动机（leitmotif）确定性铺设：缺 设定库/motif.json → 空规划 → no-op，$OUT 一字不动
python3 "$SKILL_DIR/motif_registry.py" "$ROOT" "$EP" --mix "$OUT" || true

# 集成响度（LUFS）达标巡检：量成片集成响度/真峰 vs 平台目标（advisory，不阻断；超标给整改提示）
python3 "$SKILL_DIR/loudness_conform.py" "$ROOT" "$EP" --platform "${PLATFORM:-default}" || true

# AI 标识 best-effort 后处理：默认内部预览只写元数据，不烤可见角标；发布需要时设 AI显式角标=开启。
# 铁律：AI 标识/披露/水印不得阻断 compose、进度回写或 dashboard；失败仅作为发布待办提示。
case "$AI_LABEL_MODE" in
  开启|visible|on|1|true)
    python3 "$SKILL_DIR/ai_label.py" "$ROOT" "$EP" "$OUT" || true
    ;;
  仅元数据|metadata|metadata_only|metadata-only)
    python3 "$SKILL_DIR/ai_label.py" "$ROOT" "$EP" "$OUT" --metadata-only || true
    ;;
  关闭|off|0|false|none)
    echo "AI 标识：跳过可见角标与元数据写入（AI显式角标=关闭；发布前按目标平台补齐）"
    ;;
  *)
    echo "AI 标识：未知模式「$AI_LABEL_MODE」→ 按仅元数据处理"
    python3 "$SKILL_DIR/ai_label.py" "$ROOT" "$EP" "$OUT" --metadata-only || true
    ;;
esac

# 回写进度
if [ "${N2D_UPDATE_PROGRESS:-1}" != "0" ]; then
  PYTHONPATH="$SKILL_DIR/../n2d/_lib" python3 "$SKILL_DIR/../n2d/progress.py" set "$ROOT" "$EP" "成片" "✅" || true
fi

# 记录生产数据 (P0)
python3 "$SKILL_DIR/../n2d-dashboard/scripts/dashboard.py" record "$ROOT" \
  --episode "$EP" --stage compose --event generation \
  --asset "$OUT" --status pass \
  --duration-sec "$SECONDS" --provider local-ffmpeg \
  --meta native_audio_policy="$VIDEO_NATIVE_AUDIO_POLICY" || true

# 时长对账（非阻断）：成片 ≈ 配音 ≈ 字幕末行。amix=duration=first 会静默把超长配音裁到视频长——
# 配音先行上游漂移、或先出视频后配音漏跑 fit 时音画错位，这里至少报出来。
python3 - "$OUT" "$VOICE" "$ZH_SRT" <<'PY' || true
import sys, os, re, subprocess
def ffdur(p):
    if not p or not os.path.isfile(p): return None
    try: return float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p],capture_output=True,text=True).stdout.strip())
    except Exception: return None
out, voice, srt = sys.argv[1], sys.argv[2], sys.argv[3]
od, vd = ffdur(out), ffdur(voice)
last = None
if os.path.isfile(srt):
    for m in re.finditer(r'-->\s*(\d+):(\d+):(\d+)[,.](\d+)', open(srt, encoding='utf-8').read()):
        g = list(map(int, m.groups())); last = g[0]*3600+g[1]*60+g[2]+g[3]/1000.0
msgs = []
if od and vd and abs(od-vd) > 1.0:
    msgs.append(f'成片 {od:.2f}s vs 配音 {vd:.2f}s 差 {abs(od-vd):.2f}s（amix=duration=first 可能裁掉超长配音）')
if od and last and abs(od-last) > 1.0:
    msgs.append(f'成片 {od:.2f}s vs 字幕末行 {last:.2f}s 差 {abs(od-last):.2f}s')
if msgs:
    print('⚠️ 时长对账：')
    for m in msgs: print('   - ' + m)
    print('   → 配音先行漂移/先出视频后配音漏跑 fit 的征兆：回 n2d-script/validate_timings.py 复查或重定时')
else:
    print('✅ 时长对账：成片≈配音≈字幕末行')
PY

if [ "${N2D_UPDATE_PROGRESS:-1}" != "0" ]; then
  python3 "$SKILL_DIR/../n2d/progress.py" set "$ROOT" "$EP" 成片 ✅ || true
fi
