#!/usr/bin/env bash
# 第2集 出图 · 第1轮：2 张共享定妆（偏殿修炼室 LOC_02 + 万妖血脉系统光幕）
# 在你自己的 Terminal 跑：  bash 出图/_round1_共享定妆.sh
# （必须用交互式终端，dreamina 生成要从 macOS 钥匙串取登录密钥）
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1   # 切到作品根 冷宫有妖气/

echo "出图前积分：$(dreamina user_credit 2>/dev/null | grep total_credit)"

# 通用：提交 text2image → 取 submit_id → 下载 4 张候选到目录
gen_t2i() {  # $1=输出目录  $2=prompt
  local dir="$1" prompt="$2" out sid
  mkdir -p "$dir"
  echo "==== 生成 → $dir ===="
  out=$(dreamina text2image --prompt="$prompt" --ratio=9:16 --resolution_type=2k --model_version=3.0 --poll 200 2>&1)
  echo "$out" | tee "$dir/_submit.log"
  sid=$(printf '%s' "$out" | python3 -c 'import sys,re;d=sys.stdin.read();m=re.search(r"submit_id\"?\s*[:=]\s*\"?([0-9a-fA-F]{6,})",d);print(m.group(1) if m else "")')
  if [ -z "$sid" ]; then echo "!! 未取到 submit_id —— 把上面 $dir/_submit.log 内容发我"; return 1; fi
  echo ">> submit_id=$sid 下载中…"
  dreamina query_result --submit_id="$sid" --download_dir="$dir" 2>&1 | tail -5
  echo ">> $dir 现有文件："; ls -1 "$dir"
}

# ① 偏殿修炼室 LOC_02（无参考图·纯文生）
gen_t2i "出图/common/_候选/偏殿修炼室" \
'古代冷宫一间收拾出来的简素旧偏殿作修炼室，空旷无任何人物，地面正中放一张圆形粗麻蒲团，木质窗棂结构透入清晨的斜射阳光形成数道明显光柱、光柱中浮尘缓缓飞舞，墙角堆着几件褪色旧物（旧木匣、旧布卷），地面铺旧木板有划痕，墙面斑驳但比寝殿略整洁、清贫静谧，环境构图远景偏中景，国风写实漫剧，电影级光影，冷青灰调加晨光暖点缀，高细节，竖版9:16。画面避免：人物、人脸、宫女、太监、暗夜、烛光、明亮辉煌、华丽家具、彩色、低幼Q版、卡通、画风漂移、多余文字水印、现代物件'

# ② 万妖血脉系统光幕（无参考图·纯文生）
gen_t2i "出图/common/_候选/系统光幕" \
'半透明青绿色光幕悬浮于画面近景，光幕上是古朴篆字竖排文字排布、边缘暗金描边与细微妖纹流光，文字内容如「检测到宿主濒死，万妖血脉强制激活」「击杀小妖，经验+10」等系统提示，科技与国风混合的"妖术面板"质感（既不像现代游戏UI、也不像纯古风牌匾），光幕半透能看到背后虚化的人物轮廓与破败冷宫寝殿烛光氛围，国风写实漫剧，电影级光影，暗黑宫廷，冷色调加暗金妖气，高细节，竖版9:16。画面避免：现代游戏UI、像素风、3D全息感、霓虹绿、荧光、纯古风牌匾、塑料感、低幼Q版、卡通、画风漂移、英文文字、欧美脸'

echo
echo "出图后积分：$(dreamina user_credit 2>/dev/null | grep total_credit)"
echo "==== 第1轮完成。把两个 _候选 目录跑出来后告诉我，我来读图挑选+落档 ===="
