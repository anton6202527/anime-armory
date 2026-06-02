#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd /Users/lalala/learn/anime-armory/制漫剧/冷宫有妖气
# Clip5 多帧交叉剪辑 07→08A→08B (mf2v 不支持 model/res 覆盖，固定路径)
echo "==== Clip5 鸩酒交叉剪辑 (mf2v 3s+4s) ===="
出视频/_genv.sh mf2v 候选/Clip5 \
  "出图/第1集/镜头07_柳娘子俯视.png,出图/第1集/镜头08A_压制小禾.png,出图/第1集/镜头08B_鸩酒近唇.png" \
  "柳娘子俯视假笑微微侧首眼神阴冷、镜头从低角度仰拍切到中景太监粗手捂住小禾嘴拖向门外、小禾挣扎踢腿、烛影晃动。::3" \
  "镜头切回柳娘子近景，柳娘子双手端起青瓷鸩酒器将器口缓缓递近沈念唇边、琥珀色鸩酒轻晃、沈念凤眼半垂咬紧牙关眼神疾转冷峻镇定不哀求、烛光勾勒器口与两人侧脸。::4"
echo "==== Clip5 完毕 ===="
