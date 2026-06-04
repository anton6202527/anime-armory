#!/bin/bash
# 冷宫有妖气 角色音色库：用本机中文 say 三把真嗓(Tingting/Meijia/Sinji) + ffmpeg 变调派生，
# 生成 7 个互相区分的参考音(纯合成,合规)，供 FishSpeech 零样本克隆成稳定角色嗓。
# 角色键见 render_voice.py role_key(): SHEN/NARR/LIU/XIAOHE/TAIJIAN/SYS/YAO
# 用法: bash build_voicebank.sh   产出 *.wav + _refs.env(可 source 后跑配音)
set -e
cd "$(dirname "$0")"
FF=/opt/homebrew/bin/ffmpeg
REF="夜色深沉，宫墙之内一片寂静。她缓缓抬起头，目光扫过四周，心里渐渐有了主意。"
echo "$REF" > _ref_text.txt

# key  say嗓     变调FX(空=原嗓)。FX 前已强制 aresample=44100，故 asetrate 基准恒为 44100；
# K<1=降调(更低沉/男/妖)，K>1=升调(尖细/太监)，atempo=1/K 还原时长。
gen () {
  local key="$1" voice="$2" fx="$3"
  say -v "$voice" -o "/tmp/vb_$key.aiff" "$REF"
  local af="aresample=44100"                                  # 先归一化(say aiff 为 22050Hz)
  [ -n "$fx" ] && af="$af,$fx"                                 # 再变调(基准已是 44100)
  af="$af,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100"
  $FF -y -loglevel error -i "/tmp/vb_$key.aiff" -af "$af" -ar 44100 -ac 1 "$key.wav"
  printf "  %-8s ← %-9s %s\n" "$key" "$voice" "${fx:-原嗓}"
}

echo "[voicebank] 生成中..."
gen SHEN    Tingting ""                                              # 沈念：清亮女声
gen LIU     Meijia   ""                                              # 柳娘子：成熟女声
gen XIAOHE  Sinji    ""                                              # 小禾：偏年轻女声
gen NARR    Meijia   "asetrate=44100*0.93,atempo=1.075"              # 旁白：沉稳(略降)
gen TAIJIAN Sinji    "asetrate=44100*1.12,atempo=0.893"              # 太监：尖细(升调)
gen YAO     Meijia   "asetrate=44100*0.80,atempo=1.25"               # 妖：低沉粗哑(重降)
gen SYS     Tingting "asetrate=44100*0.95,atempo=1.053"              # 系统：合成时再叠机械FX

# 写出可 source 的 env（绝对路径）
DIR="$(pwd)"
{
  echo "# source 我，再跑 render_voice.py 即按角色分音色"
  echo "export FISH_REF_TEXT=\"$REF\""
  for k in SHEN LIU XIAOHE NARR TAIJIAN YAO SYS; do
    echo "export FISH_REF_${k}=\"$DIR/$k.wav\""
    echo "export FISH_REF_${k}_TEXT=\"$REF\""
  done
} > _refs.env
echo "[voicebank] 完成 → $DIR/*.wav + _refs.env"
