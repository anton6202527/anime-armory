#!/usr/bin/env bash
# 第1集成片合成：8 clip 拼接 + BGM + TTS配音(ducking) + 字幕(烧录)
# 用法: bash _compose.sh [bilingual|zh|en]   字幕模式；配音随之 zh/zh/en
# 可选: BGMFILE=/path/to/music.mp3 bash _compose.sh zh   传真实BGM(否则程序化占位)
set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
B=/Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气
cd "$B"
MODE="${1:-bilingual}"
case "$MODE" in zh|bilingual) VLANG=zh;; en) VLANG=en;; *) echo "bad mode"; exit 1;; esac
BGMFILE="${BGMFILE:-}"
W="出视频/第1集/_work"
rm -rf "$W"; mkdir -p "$W"

CLIPS=(
  "出视频/第1集/Clip1_惊醒环顾.mp4" "出视频/第1集/Clip2_铜镜自照.mp4"
  "出视频/第1集/Clip3_身世闪回.mp4" "出视频/第1集/Clip4_小禾撞入柳娘带队.mp4"
  "出视频/第1集/Clip5_鸩酒交叉剪辑.mp4" "出视频/第1集/Clip6_觉醒图腾蔓延.mp4"
  "出视频/第1集/Clip7_反杀化黑烟.mp4" "出视频/第1集/Clip8_收尾握拳钩子.mp4"
)

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
  echo "用真实BGM: $BGMFILE"
  fo=$(python3 -c "print(max(0,$DUR-3))")
  ffmpeg -y -loglevel error -stream_loop -1 -i "$BGMFILE" -t "$DUR" \
    -af "afade=t=in:d=2,afade=t=out:st=${fo}:d=3,aresample=44100" -ac 2 "$W/bgm.wav"
else
  echo "无 BGMFILE → 程序化占位氛围乐（暗黑国风·渐强）"
  ffmpeg -y -loglevel error \
    -f lavfi -i "sine=frequency=55:duration=$DUR" -f lavfi -i "sine=frequency=110:duration=$DUR" -f lavfi -i "sine=frequency=164.81:duration=$DUR" \
    -filter_complex "[0:a][1:a][2:a]amix=inputs=3:normalize=0,tremolo=f=5:d=0.25,lowpass=f=380,aecho=0.8:0.7:60:0.3,volume='0.35+0.5*t/${DUR%.*}':eval=frame,alimiter=limit=0.9" \
    -ar 44100 -ac 2 "$W/bgm.wav"
fi

echo "=== [4/6] TTS 配音($VLANG) + 字幕 PNG ==="
cp "脚本/第1集/字幕_中文.srt" "$W/zh.srt"
cp "脚本/第1集/字幕_英文.srt" "$W/en.srt"
python3 出视频/_render_voice.py "$W" "$VLANG" "$DUR"
python3 出视频/_render_subs.py "$W" "$MODE"

echo "=== [5/6] 组装输入 ==="
PNG_INPUTS=(); while IFS= read -r p; do PNG_INPUTS+=(-i "$p"); done < "$W/inputs.txt"
NPNG=$(grep -c . "$W/inputs.txt"); VIDX=$((2+NPNG))
VFILTER=$(cat "$W/vfilter.txt")

echo "=== [6/6] 混音(配音+ducking BGM+音效底) + 烧字幕 → 成片 ==="
OUT="出视频/第1集/demo_第1集_${MODE}.mp4"
ffmpeg -y -loglevel error -i "$W/concat.mp4" -i "$W/bgm.wav" "${PNG_INPUTS[@]}" -i "$W/voice_${VLANG}.wav" \
  -filter_complex "
    [0:a]volume=0.45[sfx];
    [${VIDX}:a]asplit=2[voxA][voxB];
    [voxA]volume=1.0[vox];
    [1:a]volume=0.9[bgm0];
    [bgm0][voxB]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=400[bgmduck];
    [sfx][bgmduck][vox]amix=inputs=3:normalize=0:duration=first:dropout_transition=0,dynaudnorm[a];
    ${VFILTER}" \
  -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"

echo "=== 完成: $OUT ==="
ls -la "$OUT"
ffprobe -v error -show_entries format=duration -show_entries stream=codec_type -of default=noprint_wrappers=1 "$OUT" 2>/dev/null | head