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
KEEP_CLIP_AUDIO="${KEEP_CLIP_AUDIO:-0}"  # 默认丢弃 AI clip 原生音频；设 1 才低音量混入环境音底
J_CUT_SEC="${J_CUT_SEC:-0.25}"           # 默认轻量 J-cut：基于 line_*.wav 提前入声；设 0 关闭。正面口型特写慎用
# clips 是「出视频」的唯一产物，仍读 出视频/；配音/成片/中间件都在「合成」文件夹下。
VID="$ROOT/出视频/$EP/视频"
# 默认用 n2d-voice 产的整轨；`制作模式=先出视频后配音` 时先跑 fit_voice_to_clips.py
# 把后期补录的真音拟合到已成片镜头长，再用 VOICEFILE 指向 voice_<lang>_fitted.wav。
VOICE="${VOICEFILE:-$ROOT/合成/$EP/配音/voice_${VLANG}.wav}"
ZH_SRT="$ROOT/脚本/$EP/字幕_中文.srt"; EN_SRT="$ROOT/脚本/$EP/字幕_英文.srt"
W="$ROOT/合成/$EP/_work"; rm -rf "$W"; mkdir -p "$W"
OUT="$ROOT/合成/$EP/成片_${EP}_${MODE}.mp4"

[ -d "$VID" ] || { echo "缺 $VID（先 /n2d-video）"; exit 1; }
CLIPS=("$VID"/*.mp4)
[ -e "${CLIPS[0]}" ] || { echo "$VID 无 clip"; exit 1; }

# 占位配音守门：除非显式用 VOICEFILE 指了别的轨（如拟合轨），否则不许把占位音色烧进成片。
# `制作模式=先出视频后配音` 时：先 /n2d-voice 补真音 → fit_voice_to_clips.py → VOICEFILE=拟合轨。
MAN_J="$ROOT/合成/$EP/配音/时长清单.json"
if [ -z "${VOICEFILE:-}" ] && [ -f "$MAN_J" ] && [ "${ALLOW_PLACEHOLDER_COMPOSE:-0}" != "1" ]; then
  if python3 -c "import json,sys;d=json.load(open(sys.argv[1]));sys.exit(0 if isinstance(d,list) and any(isinstance(x,dict) and x.get('占位') for x in d) else 1)" "$MAN_J"; then
    echo "⛔ 本集配音仍是占位音色，拒绝合成（占位轨与镜头时长不是真实时长，成片音画会错）。"
    echo "   · 配音先行：先 /n2d-voice 换真实配音（CosyVoice/克隆/MiniMax）重跑。"
    echo "   · 先出视频后配音模式：/n2d-voice 补真音后，跑 fit_voice_to_clips.py 出拟合轨，再 VOICEFILE=…/voice_${VLANG}_fitted.wav 合成。"
    echo "   · 仅要占位 rough preview：ALLOW_PLACEHOLDER_COMPOSE=1 重跑（产物不可用于交付）。"
    exit 1
  fi
fi

echo "=== [1/6] 统一规格 1080x1920/30fps ==="
: > "$W/list.txt"; i=0
for c in "${CLIPS[@]}"; do
  ffmpeg -y -loglevel error -i "$c" \
    -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,fps=30,format=yuv420p" \
    -c:v libx264 -preset "$VIDEO_PRESET" -crf "$VIDEO_CRF" -an "$W/n$i.mp4"
  echo "file 'n$i.mp4'" >> "$W/list.txt"; i=$((i+1))
done

echo "=== [2/6] 拼接 ==="
ffmpeg -y -loglevel error -f concat -safe 0 -i "$W/list.txt" -c copy "$W/concat.mp4"
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

if [ "$KEEP_CLIP_AUDIO" = "1" ]; then
  echo "clip 原生音频：显式保留为低音量环境底"
  : > "$W/alist.txt"; i=0
  for c in "${CLIPS[@]}"; do
    if ffprobe -v error -select_streams a:0 -show_entries stream=index -of csv=p=0 "$c" | grep -q .; then
      ffmpeg -y -loglevel error -i "$c" -vn -t "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$c")" \
        -af "volume=0.35,aresample=44100" -ar 44100 -ac 2 "$W/a$i.wav"
    else
      d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$c")
      ffmpeg -y -loglevel error -f lavfi -i "anullsrc=r=44100:cl=stereo" -t "$d" "$W/a$i.wav"
    fi
    echo "file 'a$i.wav'" >> "$W/alist.txt"; i=$((i+1))
  done
  ffmpeg -y -loglevel error -f concat -safe 0 -i "$W/alist.txt" -c copy "$W/clip_audio.wav"
else
  echo "clip 原生音频：默认丢弃（避免原生台词与配音双人声）"
  ffmpeg -y -loglevel error -f lavfi -i "anullsrc=r=44100:cl=stereo" -t "$DUR" "$W/clip_audio.wav"
fi

echo "=== [4/6] 字幕 PNG ==="
cp "$ZH_SRT" "$W/zh.srt"; cp "$EN_SRT" "$W/en.srt"
# 复制时长清单供字幕样式分级（旁白/系统→灰小字，爽点→暖金大字）；缺则字幕全 normal
MANIFEST="$ROOT/合成/$EP/配音/时长清单.json"; [ -f "$MANIFEST" ] && cp "$MANIFEST" "$W/manifest.json" || true
PNG_INPUT_BASE=3 python3 "$SKILL_DIR/render_subs.py" "$W" "$MODE"
PNG_INPUTS=(); while IFS= read -r p; do PNG_INPUTS+=(-i "$p"); done < "$W/inputs.txt"
NPNG=$(grep -c . "$W/inputs.txt"); VIDX=$((3+NPNG))
VFILTER=$(cat "$W/vfilter.txt")

echo "=== [5/6] 混音 + 烧字幕 ==="
if [ -f "$VOICE" ]; then
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" -i "$W/clip_audio.wav" "${PNG_INPUTS[@]}" -i "$VOICE" \
    -filter_complex "
      [${VIDX}:a]asplit=2[voxA][voxB];
      [voxA]volume=1.0[vox];
      [1:a]volume=0.9[bgm0];
      [bgm0][voxB]sidechaincompress=threshold=${DUCK_THRESHOLD}:ratio=${DUCK_RATIO}:attack=${DUCK_ATTACK}:release=${DUCK_RELEASE}[bgmduck];
      [2:a]volume=1.0[sfx];
      [sfx][bgmduck][vox]amix=inputs=3:normalize=0:duration=first:dropout_transition=0,dynaudnorm[a];
      ${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
else
  echo "（无配音轨，纯 BGM+音效底+字幕）"
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" -i "$W/clip_audio.wav" "${PNG_INPUTS[@]}" \
    -filter_complex "[2:a]volume=1.0[sfx];[1:a]volume=0.85[bgm];[sfx][bgm]amix=inputs=2:duration=first:dropout_transition=0,dynaudnorm[a];${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
fi

echo "=== [6/6] 完成: $OUT ==="
ls -la "$OUT"
