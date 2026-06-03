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
VID="$ROOT/出视频/$EP/视频"
VOICE="$ROOT/出视频/$EP/配音/voice_${VLANG}.wav"
ZH_SRT="$ROOT/脚本/$EP/字幕_中文.srt"; EN_SRT="$ROOT/脚本/$EP/字幕_英文.srt"
W="$ROOT/出视频/$EP/_work"; rm -rf "$W"; mkdir -p "$W"
OUT="$ROOT/出视频/$EP/成片_${EP}_${MODE}.mp4"

[ -d "$VID" ] || { echo "缺 $VID（先 /n2d-video）"; exit 1; }
CLIPS=("$VID"/*.mp4)
[ -e "${CLIPS[0]}" ] || { echo "$VID 无 clip"; exit 1; }

echo "=== [1/6] 统一规格 1080x1920/30fps ==="
: > "$W/list.txt"; i=0
for c in "${CLIPS[@]}"; do
  ffmpeg -y -loglevel error -i "$c" \
    -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,fps=30,format=yuv420p" \
    -c:v libx264 -preset medium -crf 18 -c:a aac -ar 44100 -ac 2 "$W/n$i.mp4"
  echo "file 'n$i.mp4'" >> "$W/list.txt"; i=$((i+1))
done

echo "=== [2/6] 拼接 ==="
ffmpeg -y -loglevel error -f concat -safe 0 -i "$W/list.txt" -c copy "$W/concat.mp4"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$W/concat.mp4")
echo "成片时长 ${DUR}s"

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

echo "=== [4/6] 字幕 PNG ==="
cp "$ZH_SRT" "$W/zh.srt"; cp "$EN_SRT" "$W/en.srt"
python3 "$SKILL_DIR/render_subs.py" "$W" "$MODE"
PNG_INPUTS=(); while IFS= read -r p; do PNG_INPUTS+=(-i "$p"); done < "$W/inputs.txt"
NPNG=$(grep -c . "$W/inputs.txt"); VIDX=$((2+NPNG))
VFILTER=$(cat "$W/vfilter.txt")

echo "=== [5/6] 混音 + 烧字幕 ==="
if [ -f "$VOICE" ]; then
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" "${PNG_INPUTS[@]}" -i "$VOICE" \
    -filter_complex "
      [0:a]volume=0.45[sfx];
      [${VIDX}:a]asplit=2[voxA][voxB];
      [voxA]volume=1.0[vox];
      [1:a]volume=0.9[bgm0];
      [bgm0][voxB]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=400[bgmduck];
      [sfx][bgmduck][vox]amix=inputs=3:normalize=0:duration=first:dropout_transition=0,dynaudnorm[a];
      ${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
else
  echo "（无配音轨，纯 BGM+音效底+字幕）"
  ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" "${PNG_INPUTS[@]}" \
    -filter_complex "[0:a]volume=0.5[sfx];[1:a]volume=0.85[bgm];[sfx][bgm]amix=inputs=2:duration=first:dropout_transition=0,dynaudnorm[a];${VFILTER}" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
fi

echo "=== [6/6] 完成: $OUT ==="
ls -la "$OUT"
