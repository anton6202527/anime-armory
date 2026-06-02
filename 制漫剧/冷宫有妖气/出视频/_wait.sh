#!/usr/bin/env bash
cd /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气
names=(Clip3 Clip4 Clip6 Clip7 Clip8)
sids=(1fe4246f-5b42-4eb9-a9c7-fb829fb40424 c4ce095a-3769-422c-8567-b2f57f619c9d d2335550-1ec9-497c-bd72-54390a680300 05b2f06e-5829-44f3-a723-dd0c0c9a1785 614a5674-f514-434c-bcb9-5b41cd545694)
n=${#names[@]}
for round in $(seq 1 50); do
  ready=0
  for i in $(seq 0 $((n-1))); do
    nm=${names[$i]}; sid=${sids[$i]}
    if ls 出视频/候选/$nm/*.mp4 >/dev/null 2>&1; then ready=$((ready+1)); continue; fi
    dreamina query_result --submit_id="$sid" --download_dir="出视频/候选/$nm" >/dev/null 2>&1
    ls 出视频/候选/$nm/*.mp4 >/dev/null 2>&1 && ready=$((ready+1))
  done
  echo "round $round: $ready/$n ready"
  [ "$ready" -ge "$n" ] && break
  sleep 25
done
for i in $(seq 0 $((n-1))); do nm=${names[$i]}; f=$(ls -t 出视频/候选/$nm/*.mp4 2>/dev/null|head -1); echo "$nm: ${f:-缺失}"; done