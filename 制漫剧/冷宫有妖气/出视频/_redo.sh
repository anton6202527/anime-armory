#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气
rm -rf 出视频/候选/Clip3 出视频/候选/Clip4 出视频/候选/Clip6

submit_sid(){ # echo sid; args after
  resp=$("$@" 2>&1)
  echo "$resp" | python3 -c 'import sys,re;t=sys.stdin.read();m=re.search(r"\"submit_id\"\s*:\s*\"([^\"]+)\"",t);print(m.group(1) if m else "")'
}

echo "提交 Clip3 (i2v fast 6s)..."
S3=$(submit_sid dreamina image2video --image "出图/第1集/镜头04_身世闪回.png" --prompt '身世闪回蒙太奇快速硬切：画面1入宫受封红盖头掀起、画面2搜出黑色巫蛊草人偶被官差喝令、画面3皇帝拂袖背影、画面4冷宫朱门重重合拢，每段约1.5秒，每段轻微缩放加硬切。颗粒噪点贯穿、冷雾沿画面边缘流动、暗角加深、青冷胶片质感。国风写实漫剧、回忆滤镜。' --model_version seedance2.0fast --video_resolution 720p --duration 6 --poll 200)
echo "S3=$S3"
echo "提交 Clip4 (f2v fast 8s)..."
S4=$(submit_sid dreamina frames2video --first "出图/第1集/镜头05_小禾撞入.png" --last "出图/第1集/镜头06_柳娘子带队.png" --prompt '[0-4s] 小禾跌撞冲入扑抓沈念手臂、浑身发抖、泪滑落；[4-8s] 门帘掀开柳娘子假笑步入、身后两太监端托盘脚步沉稳逼近。[0-4s] 中景固定；[4-8s] 门帘处缓慢横移入画。动态细节：门帘布料晃动、烛影晃动、小禾发丝凌乱、托盘器物反光、柳娘子衣袂摆动。国风写实漫剧、电影级光影、暗黑宫廷。' --model_version seedance2.0fast --video_resolution 720p --duration 8 --poll 200)
echo "S4=$S4"
echo "提交 Clip6 (f2v vip 1080p 7s · 重生)..."
S6=$(submit_sid dreamina frames2video --first "出图/第1集/镜头09_觉醒情绪顶点.png" --last "出图/第1集/镜头10_图腾蔓延.png" --prompt '[0-3s] 沈念胸口炸开暗金热流光芒向外迸射照亮惊缩瞳孔、表情从震惊转为觉醒；[3-7s] 暗金图腾纹路从心口蔓延至双臂指尖、瞳孔骤缩成金色竖瞳、发丝被妖气掀起、柳娘子假笑凝固后退半步。[0-3s] 特写急推；[3-7s] 近景环绕半圈轻微震动。暗金妖气如热浪扩散、纹路如刺青从皮肤下点亮、烛火被气流吹偏、光粒上升、发丝飘动。国风写实漫剧、电影级光影、暗黑宫廷加暗金妖气。' --model_version seedance2.0_vip --video_resolution 1080p --duration 7 --poll 200)
echo "S6=$S6"

# 统一长轮询下载（最多 ~30 分钟）
names=(Clip3 Clip4 Clip6); sids=($S3 $S4 $S6)
for round in $(seq 1 70); do
  ready=0
  for i in 0 1 2; do
    nm=${names[$i]}; sid=${sids[$i]}
    [ -z "$sid" ] && continue
    if ls 出视频/候选/$nm/*.mp4 >/dev/null 2>&1; then ready=$((ready+1)); continue; fi
    dreamina query_result --submit_id="$sid" --download_dir="出视频/候选/$nm" >/dev/null 2>&1
    ls 出视频/候选/$nm/*.mp4 >/dev/null 2>&1 && ready=$((ready+1))
  done
  echo "round $round: $ready/3 ready"
  [ "$ready" -ge 3 ] && break
  sleep 25
done
echo "=== 完成 ==="
for i in 0 1 2; do nm=${names[$i]}; echo "$nm: sid=${sids[$i]} file=$(ls 出视频/候选/$nm/*.mp4 2>/dev/null|head -1 || echo 未出)"; done