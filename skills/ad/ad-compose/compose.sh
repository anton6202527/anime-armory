#!/usr/bin/env bash
# 拍广告 剪辑包装：拼 clips + 混 VO/音乐床 + 字幕 + 片尾包装 → 成片_主片.mp4
# 自包含（本机 ffmpeg 无 libass，字幕走 render_subs.py 的 PNG overlay）。
# 用法：bash compose.sh <作品根> [输出比例] [字幕语言 zh|en|bilingual|none] [交付规格 平台默认|广电TVC]
set -euo pipefail

ROOT="${1:?用法: compose.sh <作品根> [比例] [字幕语言] [交付规格]}"
ASPECT_ARG="${2:-}"
SUBLANG="${3:-none}"      # zh|en|bilingual|none（none=不烧字幕）
DELIVERY="${4:-平台默认}"
WORK="$ROOT/合成/_work"
OUT="$ROOT/合成/成片_主片.mp4"
CLIP_DIR="$ROOT/出视频/分镜/视频"
VO="$ROOT/配音/vo.wav"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$WORK" "$ROOT/合成"

# 正式合成入口强制跑 compose gate，不能靠操作者记住文档步骤。
python3 "$HERE/../ad-craft/scripts/gate.py" "$ROOT" --stage compose
python3 "$HERE/../ad-craft/scripts/stage_acceptance.py" "$ROOT" --stage video
python3 "$HERE/compose_preflight.py" "$ROOT" --color-report "$ROOT/合成/color_preflight.json"

command -v ffmpeg >/dev/null || { echo "[err] 需要 ffmpeg"; exit 2; }
COLOR_ARGS=( -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv )

# 单一规格源：设置选择 + placement/客户交付要求统一编译到 render_profile.json。
# 这里不再假定长边 1920 / 30fps；若要求原生分辨率而生成源不足，compiler 会直接退出。
profile_args=( "$ROOT" --json "$ROOT/生产数据/render_profile.json" --shell )
if [ -n "$ASPECT_ARG" ]; then profile_args+=( --aspect "$ASPECT_ARG" ); fi
PROFILE_LINE="$(python3 "$HERE/../ad-craft/scripts/render_profile.py" "${profile_args[@]}")"
IFS=$'\t' read -r OW OH FPS ASPECT SOURCE_W SOURCE_H UPSCALE_POLICY QUALITY_CLAIM <<< "$PROFILE_LINE"
[ -n "$OW" ] && [ -n "$OH" ] && [ -n "$FPS" ] && [ -n "$ASPECT" ] \
  || { echo "[err] render_profile 未返回有效 master_render"; exit 2; }
echo "[i] 母版 ${OW}x${OH}@${FPS}fps（比例 ${ASPECT}）  生成源=${SOURCE_W}x${SOURCE_H}  ${QUALITY_CLAIM}/${UPSCALE_POLICY}  字幕=${SUBLANG}  交付规格=${DELIVERY}"

# 1) 拼接 clips。异构 clip 用 filter-concat 归一（scale/pad/fps/setsar），不用 -c copy
#    （-c copy 拼异构 clip 会静默产出损坏；这里始终重编码归一，stderr 不吞）。
shopt -s nullglob
clips=( "$CLIP_DIR"/*.mp4 )
[ ${#clips[@]} -gt 0 ] || { echo "[err] $CLIP_DIR 没有 clip"; exit 2; }

NORM="scale=${OW}:${OH}:force_original_aspect_ratio=decrease,pad=${OW}:${OH}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=${FPS}"
VIDEO="$WORK/_video.mp4"
in_args=(); fc=""; n=${#clips[@]}
for i in "${!clips[@]}"; do in_args+=( -i "${clips[$i]}" ); fc+="[$i:v]${NORM}[v$i];"; done
maps=""; for i in "${!clips[@]}"; do maps+="[v$i]"; done
fc+="${maps}concat=n=${n}:v=1:a=0[outv]"
ffmpeg -y "${in_args[@]}" -filter_complex "$fc" -map "[outv]" -c:v libx264 -pix_fmt yuv420p "${COLOR_ARGS[@]}" "$VIDEO"

# 2) 片尾 end card（若已生成 endcard.png，按当前画幅归一后追加 2.5s）
ENDCARD="$WORK/endcard.png"
if [ -f "$ENDCARD" ] && python3 "$HERE/compose_preflight.py" "$ROOT" --should-append-endcard; then
  ffmpeg -y -loop 1 -t 2.5 -i "$ENDCARD" -vf "${NORM}" \
    -c:v libx264 -pix_fmt yuv420p "${COLOR_ARGS[@]}" "$WORK/_endcard.mp4"
  ffmpeg -y -i "$VIDEO" -i "$WORK/_endcard.mp4" \
    -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[v]" -map "[v]" \
    -c:v libx264 -pix_fmt yuv420p "${COLOR_ARGS[@]}" "$WORK/_video_full.mp4"
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
        -filter_complex "$VF" -map "[v]" -c:v libx264 -pix_fmt yuv420p "${COLOR_ARGS[@]}" "$SUBBED"
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
  ffmpeg -y -i "$VIDEO" -i "$VO" -stream_loop -1 -i "$MUSIC" \
    -filter_complex "[2:a]volume=0.25[m];[1:a]apad[vo];[vo][m]amix=inputs=2:duration=longest:dropout_transition=2,apad[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -ar 48000 -shortest "$OUT"
elif [ -f "$VO" ]; then
  ffmpeg -y -i "$VIDEO" -i "$VO" -filter_complex "[1:a]apad[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -ar 48000 -shortest "$OUT"
else
  cp "$VIDEO" "$OUT"
fi
echo "[ok] 成片：$OUT"

# 5) 交付规格响度归一（按 DELIVERY 的 LUFS）。只有当成片有音轨时才跑。
PROFILE="$(python3 "$HERE/delivery_profile.py" "$DELIVERY" --project-root "$ROOT")"
LUFS="${PROFILE%%$'\t'*}"; TP="${PROFILE#*$'\t'}"
HAS_AUDIO=0
if command -v ffprobe >/dev/null; then
  ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$OUT" | grep -q . && HAS_AUDIO=1
else
  ffmpeg -i "$OUT" -hide_banner 2>&1 | grep -q "Audio:" && HAS_AUDIO=1
fi
if [ "$HAS_AUDIO" = "1" ]; then
  LOUD="$ROOT/合成/_work/成片_主片_loud.tmp.mp4"
  ffmpeg -y -i "$OUT" -af "loudnorm=I=${LUFS}:TP=${TP}:LRA=11" -c:v copy -c:a aac -ar 48000 "$LOUD"
  mv "$LOUD" "$OUT"
  echo "[ok] 响度归一（${LUFS} LUFS / TP ${TP}）：$OUT（正式交付路径已替换）"
else
  echo "[i] 成片无音轨（无 VO），跳过响度归一"
fi

echo "下一步：placement_adaptation.py 决策逐版位模式 → 仅获准 mechanical_reframe 执行 reframe.py --render → 多时长 cutdown.py --render → deliver.py --mark-existing 回写交付矩阵"
