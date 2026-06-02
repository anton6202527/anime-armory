#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
B=/Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气
cd "$B" || { echo "CD FAILED"; exit 1; }
rm -rf 出视频/候选/Clip4 出视频/候选/Clip6 出视频/候选/Clip4b

sidof(){ python3 -c 'import sys,re;t=sys.stdin.read();m=re.search(r"\"submit_id\"\s*:\s*\"([^\"]+)\"",t);print(m.group(1) if m else "")'; }

echo "提交 Clip4 (multiframe 05->06, 8s)..."
R4=$(dreamina multiframe2video \
  --images "$B/出图/第1集/镜头05_小禾撞入.png,$B/出图/第1集/镜头06_柳娘子带队.png" \
  --prompt '小禾跌撞冲入扑抓沈念手臂浑身发抖泪滑落，随后门帘掀开柳娘子假笑步入身后两太监端托盘脚步沉稳逼近；门帘布料晃动、烛影晃动、小禾发丝凌乱、托盘器物反光。国风写实漫剧暗黑宫廷。' \
  --duration 8 --poll 200 2>&1)
S4=$(printf '%s' "$R4" | sidof); echo "S4=$S4"

echo "提交 Clip6 (i2v vip1080p, 镜头09 觉醒, 7s)..."
R6=$(dreamina image2video \
  --image "$B/出图/第1集/镜头09_觉醒情绪顶点.png" \
  --prompt '沈念胸口炸开的暗金热流光芒持续向外迸射照亮惊缩瞳孔，暗金图腾纹路如刺青从心口下方点亮并蔓延至双臂指尖、瞳孔骤缩成金色野兽竖瞳、月白宫装窄袖被妖气从内掀起轻微撕裂、发丝被妖气掀起上扬、体表暗金妖气如热浪向外扩散细小光粒上升、烛火被气流吹偏压暗。镜头特写急推后轻微环绕。国风写实漫剧、电影级动态光影、暗黑宫廷加暗金妖气、强动态。' \
  --model_version seedance2.0_vip --video_resolution 1080p --duration 7 --poll 200 2>&1)
S6=$(printf '%s' "$R6" | sidof); echo "S6=$S6"

names=(Clip4 Clip6); sids=("$S4" "$S6")
for round in $(seq 1 80); do
  ready=0
  for i in 0 1; do
    nm=${names[$i]}; sid=${sids[$i]}; [ -z "$sid" ] && continue
    if ls "$B"/出视频/候选/$nm/*.mp4 >/dev/null 2>&1; then ready=$((ready+1)); continue; fi
    dreamina query_result --submit_id="$sid" --download_dir="$B/出视频/候选/$nm" >/dev/null 2>&1
    ls "$B"/出视频/候选/$nm/*.mp4 >/dev/null 2>&1 && ready=$((ready+1))
  done
  echo "round $round: $ready/2 ready"
  [ "$ready" -ge 2 ] && break
  sleep 25
done
echo "=== 完成 ==="
for i in 0 1; do nm=${names[$i]}; echo "$nm: sid=${sids[$i]} file=$(ls "$B"/出视频/候选/$nm/*.mp4 2>/dev/null|head -1 || echo 未出)"; done