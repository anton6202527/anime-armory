#!/usr/bin/env bash
# 拍广告 剪辑包装：拼 clips + 混 VO/音乐床 + 字幕 + 片尾包装 → 成片_主片.mp4
# 自包含（本机 ffmpeg 无 libass，字幕走 render_subs.py 的 PNG overlay）。
# 用法：bash compose.sh <作品根> [输出比例 16:9] [字幕语言 zh|en|bilingual|none] [交付规格 平台默认|广电TVC]
set -euo pipefail

ROOT="${1:?用法: compose.sh <作品根> [比例] [字幕语言] [交付规格]}"
ASPECT="${2:-16:9}"
SUBLANG="${3:-none}"      # zh|en|bilingual|none（none=不烧字幕）
DELIVERY="${4:-平台默认}"  # 平台默认 -16 LUFS / 广电TVC -23 LUFS
WORK="$ROOT/合成/_work"
OUT="$ROOT/合成/成片_主片.mp4"
CLIP_DIR="$ROOT/出视频/分镜/视频"
VO="$ROOT/配音/vo.wav"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$WORK" "$ROOT/合成"

command -v ffmpeg >/dev/null || { echo "[err] 需要 ffmpeg"; exit 2; }

# ASPECT → 输出分辨率（长边 1920），end card / 字幕 / 归一画幅都用它。
SIZE="$(python3 "$HERE/reframe.py" --src 1920x1080 --target "$ASPECT" --mode pad 2>/dev/null \
  | sed -n 's/.*输出 \([0-9]*x[0-9]*\).*/\1/p' | head -1)"
OW="${SIZE%x*}"; OH="${SIZE#*x}"
[ -n "$OW" ] && [ -n "$OH" ] || { echo "[err] 无法从比例 $ASPECT 推出分辨率"; exit 2; }
echo "[i] 输出画幅 ${OW}x${OH}（比例 ${ASPECT}）  字幕=${SUBLANG}  交付规格=${DELIVERY}"

# 1) 拼接 clips。异构 clip 用 filter-concat 归一（scale/pad/fps/setsar），不用 -c copy
#    （-c copy 拼异构 clip 会静默产出损坏；这里始终重编码归一，stderr 不吞）。
shopt -s nullglob
clips=( "$CLIP_DIR"/*.mp4 )
[ ${#clips[@]} -gt 0 ] || { echo "[err] $CLIP_DIR 没有 clip"; exit 2; }

NORM="scale=${OW}:${OH}:force_original_aspect_ratio=decrease,pad=${OW}:${OH}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30"
VIDEO="$WORK/_video.mp4"
in_args=(); fc=""; n=${#clips[@]}
for i in "${!clips[@]}"; do in_args+=( -i "${clips[$i]}" ); fc+="[$i:v]${NORM}[v$i];"; done
maps=""; for i in "${!clips[@]}"; do maps+="[v$i]"; done
fc+="${maps}concat=n=${n}:v=1:a=0[outv]"
ffmpeg -y "${in_args[@]}" -filter_complex "$fc" -map "[outv]" -c:v libx264 -pix_fmt yuv420p "$VIDEO"

# 2) 片尾 end card（若已生成 endcard.png，按当前画幅归一后追加 2.5s）
ENDCARD="$WORK/endcard.png"
if [ -f "$ENDCARD" ]; then
  ffmpeg -y -loop 1 -t 2.5 -i "$ENDCARD" -vf "${NORM}" \
    -c:v libx264 -pix_fmt yuv420p "$WORK/_endcard.mp4"
  ffmpeg -y -i "$VIDEO" -i "$WORK/_endcard.mp4" \
    -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[v]" -map "[v]" \
    -c:v libx264 -pix_fmt yuv420p "$WORK/_video_full.mp4"
  VIDEO="$WORK/_video_full.mp4"
fi

# 3) 字幕烧录（可选）。先用 render_subs.py 出 PNG + vfilter.txt，再 overlay 进底片。
#    render_subs 的 overlay 链按 png_input_base=1（0=底片视频）拼好，compose 直接消费 vfilter.txt。
SUBBED=""
if [ "$SUBLANG" != "none" ]; then
  case "$SUBLANG" in
    en) SRT="$ROOT/脚本/字幕_en.srt" ;;
    bilingual) SRT="$ROOT/脚本/字幕_zh.srt" ;;  # 双语 SRT 已在脚本阶段合一（每条多行）
    *) SRT="$ROOT/脚本/字幕_zh.srt" ;;
  esac
  if [ -f "$SRT" ]; then
    SUBDIR="$WORK/subs"
    python3 "$HERE/render_subs.py" "$SRT" --out-dir "$SUBDIR" --size "${OW}x${OH}" --png-input-base 1
    if [ -s "$SUBDIR/vfilter.txt" ] && [ -s "$SUBDIR/inputs.txt" ]; then
      VF="$(cat "$SUBDIR/vfilter.txt")"
      png_args=(); while IFS= read -r p; do [ -n "$p" ] && png_args+=( -i "$p" ); done < "$SUBDIR/inputs.txt"
      SUBBED="$WORK/_video_sub.mp4"
      ffmpeg -y -i "$VIDEO" "${png_args[@]}" \
        -filter_complex "$VF" -map "[v]" -c:v libx264 -pix_fmt yuv420p "$SUBBED"
      VIDEO="$SUBBED"
      echo "[i] 已烧字幕（${SUBLANG}）"
    else
      echo "[warn] 字幕 PNG/overlay 链为空，跳过烧字幕"
    fi
  else
    echo "[warn] 缺字幕 SRT：${SRT}，跳过烧字幕"
  fi
fi

# 4) 混音：VO（主）+ 音乐床（duck）。音乐床可选：$ROOT/配音/music.wav
MUSIC="$ROOT/配音/music.wav"
if [ -f "$VO" ] && [ -f "$MUSIC" ]; then
  ffmpeg -y -i "$VIDEO" -i "$VO" -i "$MUSIC" \
    -filter_complex "[2:a]volume=0.25[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -shortest "$OUT"
elif [ -f "$VO" ]; then
  ffmpeg -y -i "$VIDEO" -i "$VO" -map 0:v -map 1:a -c:v copy -c:a aac -shortest "$OUT"
else
  cp "$VIDEO" "$OUT"
fi
echo "[ok] 成片：$OUT"

# 5) 交付规格响度归一（按 DELIVERY 的 LUFS）。只有当成片有音轨时才跑。
LUFS="-16"; TP="-1"
[ "$DELIVERY" = "广电TVC" ] && { LUFS="-23"; TP="-2"; }
HAS_AUDIO=0
if command -v ffprobe >/dev/null; then
  ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$OUT" | grep -q . && HAS_AUDIO=1
else
  ffmpeg -i "$OUT" -hide_banner 2>&1 | grep -q "Audio:" && HAS_AUDIO=1
fi
if [ "$HAS_AUDIO" = "1" ]; then
  LOUD="$ROOT/合成/成片_主片_loud.mp4"
  ffmpeg -y -i "$OUT" -af "loudnorm=I=${LUFS}:TP=${TP}:LRA=11" -c:v copy -c:a aac "$LOUD"
  echo "[ok] 响度归一（${LUFS} LUFS / TP ${TP}）：$LOUD"
else
  echo "[i] 成片无音轨（无 VO），跳过响度归一"
fi

echo "下一步：多比例 reframe.py --render → 多时长 cutdown.py --render → deliver.py --mark-existing 回写交付矩阵"
