#!/usr/bin/env bash
# 合成成片：视频/clips + (可选)配音轨 + BGM + 烧字幕 → 成片_第N集_{mode}.mp4
# 用法: bash compose.sh <作品根> <第N集> [bilingual|zh|en]
# 可选: BGMFILE=/path/to/music.mp3   传真实BGM(否则程序化占位)
set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
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
if [ "$KEEP_CLIP_AUDIO" = "1" ] && [ "$VIDEO_NATIVE_AUDIO_POLICY" = "丢弃" ]; then
  echo "⚠️ 旧环境变量 KEEP_CLIP_AUDIO=1 覆盖了权威设置「视频原生音轨=丢弃」→ 改用「低音量混入环境声」。若非本意请 unset KEEP_CLIP_AUDIO 或在 _设置.md 显式写「视频原生音轨」。"
  VIDEO_NATIVE_AUDIO_POLICY="低音量混入环境声"
fi

# 制作模式=原生音画：说话镜的台词由视频后端原生生成、就在 clip 自带音轨里——绝不能丢弃，否则台词没了。
PROD_MODE=$(eval $_GET_SETTING "\"$ROOT\" \"制作模式\" \"配音先行\"")
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
# 默认用 n2d-voice 产的整轨；`制作模式=先出视频后配音` 时先跑 fit_voice_to_clips.py
# 把后期补录的真音拟合到已成片镜头长，再用 VOICEFILE 指向 voice_<lang>_fitted.wav。
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
python3 - "$ROOT" "$EP" "$VID" "$SOURCE_LIST" <<'PY'
import glob, json, os, sys
root, ep, vid, out_path = sys.argv[1:5]
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
            parts = sorted(glob.glob(os.path.join(vid, f"*{cid}*part*.mp4")))
            if parts:
                for p in parts:
                    # 拆段后的子文件时长由生成时控制，此处设为 None 让 ffmpeg 取全长，
                    # 速度模式设为 trim（生成时已对齐时长，不需要整体 warp，否则会把子段拉长到总时长）
                    ordered.append((p, "None", "trim"))
                continue
            
            # 无拆段时，尝试精确匹配或模糊匹配
            if not path or not os.path.exists(path):
                cands = sorted(glob.glob(os.path.join(vid, f"*{cid}*.mp4")))
                if cands: path = cands[0]
        
        if path and os.path.exists(path):
            ordered.append((path, clip.get("duration", "None"), clip.get("speed_mode", "warp")))
else:
    for p in sorted(glob.glob(os.path.join(vid, "*.mp4"))):
        ordered.append((p, "None", "trim"))

with open(out_path, "w", encoding="utf-8") as f:
    for p, d, s in ordered:
        f.write(f"{p}\t{d}\t{s}\n")
PY

if [ ! -s "$SOURCE_LIST" ]; then
  echo "⛔ $VID 找不到对应 clip"
  exit 1
fi

CACHE="$ROOT/合成/$EP/_clipcache"; mkdir -p "$CACHE"
: > "$W/list.txt"
CLIPS=() # 重置 CLIPS 以确保后续读取原生音频的顺序也是排好的
while IFS=$'\t' read -r c dur speed_mode; do
  [ -f "$c" ] || continue
  CLIPS+=("$c")
  key=$(python3 -c "import os,hashlib,sys;p=sys.argv[1];print(hashlib.md5(f'{os.path.basename(p)}:{os.path.getmtime(p)}:{sys.argv[2]}:{sys.argv[3]}:{sys.argv[4]}'.encode()).hexdigest()[:16])" "$c" "${PXW}x${PXH}:${VIDEO_CRF}:${VIDEO_PRESET}" "$dur" "$speed_mode")
  nf="$CACHE/n_${key}.mp4"
  
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
            echo "  ✨ 光流拉伸(Time-Warp): $(basename "$c") ($SRC_DUR s -> ${dur}s, ${FACTOR}x)"
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

    # 只在 compose 的规格化缓存中 -an；出视频目录里的 AI 原片保持不变。
    ffmpeg -y -loglevel error -i "$c" \
      -vf "${SETPTS_OPT}scale=${PXW}:${PXH}:force_original_aspect_ratio=decrease,pad=${PXW}:${PXH}:(ow-iw)/2:(oh-ih)/2:black,fps=30,format=yuv420p" \
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
    echo "⚠️ clip 原生音频策略=保留原片音轨，且检测到配音轨 $VOICE；若原片含人声会双人声。正式成片建议改为 低音量混入环境声 或 丢弃。"
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

echo "=== [4/6] 字幕 PNG ==="
# 字幕可选：默认仅中文（finalize_storyboard 仅在有英文译文时才产 字幕_英文.srt），EN 缺失不算错。
# 注意 set -e：缺文件时 cp 会整体中断合成，故每个 cp 先判存在。render_subs.parse_srt 对缺轨已容错。
[ -f "$ZH_SRT" ] && cp "$ZH_SRT" "$W/zh.srt" || echo "（无中文字幕 $ZH_SRT，跳过）"
[ -f "$EN_SRT" ] && cp "$EN_SRT" "$W/en.srt" || true
# 复制时长清单供字幕样式分级（旁白/系统→灰小字，爽点→暖金大字）；缺则字幕全 normal
MANIFEST="$ROOT/合成/$EP/配音/时长清单.json"; [ -f "$MANIFEST" ] && cp "$MANIFEST" "$W/manifest.json" || true
PNG_INPUT_BASE=3 SUB_W="$PXW" SUB_H="$PXH" python3 "$SKILL_DIR/render_subs.py" "$W" "$MODE"
PNG_INPUTS=(); while IFS= read -r p; do PNG_INPUTS+=(-i "$p"); done < "$W/inputs.txt"
NPNG=$(grep -c . "$W/inputs.txt"); VIDX=$((3+NPNG))
VFILTER=$(cat "$W/vfilter.txt")

echo "=== [5/6] 混音 + 烧字幕 ==="
if [ -f "$VOICE" ]; then
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" -i "$W/clip_audio.wav" "${PNG_INPUTS[@]}" -i "$VOICE" \
    -filter_complex "
      [${VIDX}:a]asplit=2[voxA][voxB];
      [voxA]volume=1.0[vox];
      [1:a]${BGM_VOL_VOICE}[bgm0];
      [bgm0][voxB]sidechaincompress=threshold=${DUCK_THRESHOLD}:ratio=${DUCK_RATIO}:attack=${DUCK_ATTACK}:release=${DUCK_RELEASE}[bgmduck];
      [2:a]volume=1.0[sfx];
      [sfx][bgmduck][vox]amix=inputs=3:normalize=0:duration=first:dropout_transition=0,dynaudnorm[a];
      ${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
elif [ "$NATIVE_AV_MODE" = "1" ] && [ "$NATIVE_AUDIO_MODE" != "discard" ]; then
  echo "（原生音画模式：使用 clip 原生音频作为侧链 ducking 源）"
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" -i "$W/clip_audio.wav" "${PNG_INPUTS[@]}" \
    -filter_complex "
      [2:a]asplit=2[sfx][sfxB];
      [1:a]${BGM_VOL_VOICE}[bgm0];
      [bgm0][sfxB]sidechaincompress=threshold=${DUCK_THRESHOLD}:ratio=${DUCK_RATIO}:attack=${DUCK_ATTACK}:release=${DUCK_RELEASE}[bgmduck];
      [sfx][bgmduck]amix=inputs=2:normalize=0:duration=first:dropout_transition=0,dynaudnorm[a];
      ${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
else
  echo "（无配音轨，纯 BGM+音效底+字幕）"
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" -i "$W/clip_audio.wav" "${PNG_INPUTS[@]}" \
    -filter_complex "[2:a]volume=1.0[sfx];[1:a]${BGM_VOL_NOVOICE}[bgm];[sfx][bgm]amix=inputs=2:duration=first:dropout_transition=0,dynaudnorm[a];${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
fi


echo "=== [6/6] 完成: $OUT ==="
ls -la "$OUT"

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
