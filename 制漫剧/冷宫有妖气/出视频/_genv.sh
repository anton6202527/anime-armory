#!/usr/bin/env bash
# 视频生成 helper（带自动重试瞬时失败）
# 用法:
#   _genv.sh i2v   <候选目录> <prompt> <image> [model] [res] [dur]
#   _genv.sh f2v   <候选目录> <prompt> <first> <last> [model] [res] [dur]
#   _genv.sh mf2v  <候选目录> <images_csv> <tp1::dur1> [tp2::dur2] ...   (multiframe)
cd "$(dirname "$0")/.."   # 切到作品根
mode="$1"; outdir="$2"; mkdir -p "出视频/$outdir"
od="出视频/$outdir"

submit(){
  for attempt in 1 2 3; do
    resp=$("$@" 2>&1)
    sid=$(printf '%s' "$resp" | python3 -c 'import sys,re;t=sys.stdin.read();m=re.search(r"\"submit_id\"\s*:\s*\"([^\"]+)\"",t);print(m.group(1) if m else "")')
    cred=$(printf '%s' "$resp" | python3 -c 'import sys,re;t=sys.stdin.read();m=re.search(r"\"credit_count\"\s*:\s*(\d+)",t);print(m.group(1) if m else "?")')
    if [ -n "$sid" ]; then
      # 视频渲染比 poll 慢，轮询 query_result 直到 mp4 落地（最多 ~12 次 × 20s）
      for q in $(seq 1 12); do
        dreamina query_result --submit_id="$sid" --download_dir="$od" >/dev/null 2>&1
        f=$(ls -t "$od"/*.mp4 2>/dev/null | head -1)
        [ -n "$f" ] && { echo "OK sid=$sid credit=$cred file=$f"; return 0; }
        sleep 20
      done
      echo "OK sid=$sid credit=$cred file=PENDING(query_result --submit_id=$sid 稍后重取)"; return 0
    fi
    echo "第${attempt}次提交失败,重试..." >&2; sleep 6
  done
  echo "三次均失败: $(printf '%s' "$resp" | tail -3)"; return 1
}

case "$mode" in
  i2v)  prompt="$3"; img="$4"; model="${5:-}"; res="${6:-}"; dur="${7:-}"
        args=(dreamina image2video --image "$img" --prompt "$prompt" --poll 240)
        [ -n "$dur" ] && args+=(--duration "$dur")
        [ -n "$model" ] && args+=(--model_version "$model")
        [ -n "$res" ] && args+=(--video_resolution "$res")
        submit "${args[@]}" ;;
  f2v)  prompt="$3"; first="$4"; last="$5"; model="${6:-}"; res="${7:-}"; dur="${8:-}"
        args=(dreamina frames2video --first "$first" --last "$last" --prompt "$prompt" --poll 240)
        [ -n "$dur" ] && args+=(--duration "$dur")
        [ -n "$model" ] && args+=(--model_version "$model")
        [ -n "$res" ] && args+=(--video_resolution "$res")
        submit "${args[@]}" ;;
  mf2v) images="$3"; shift 3
        args=(dreamina multiframe2video --images "$images" --poll 240)
        for seg in "$@"; do
          tp="${seg%%::*}"; td="${seg##*::}"
          args+=(--transition-prompt "$tp" --transition-duration "$td")
        done
        submit "${args[@]}" ;;
  *) echo "unknown mode $mode"; exit 1 ;;
esac
