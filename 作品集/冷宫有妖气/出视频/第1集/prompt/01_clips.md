# 第1集 Clip prompts（即梦 image2video / frames2video / multiframe2video）

> 派生自 `脚本/第1集/故事板.md`，首帧来自 `出图/第1集/`（19/19 ✅）。
> 全部使用 dreamina CLI；MP4 落档 `出视频/第1集/ClipK_<描述>.mp4`。
> 通用：竖版 9:16（自动推断）、默认 seedance2.0fast、不另设负面词（即梦无独立负面框）。

---

## Clip 1（时长 8s · 镜头 1+2 · frames2video）

**模式**：图生视频 — 首尾帧
**首帧**：`出图/第1集/镜头01_沈念惊醒.png`
**尾帧**：`出图/第1集/镜头02_沈念环顾.png`
**场景**：冷宫寝殿（夜/内）

### 视频 prompt（中文）
```
人物运动：[0-3s] 沈念双眼猛然睁开瞳孔微缩睫毛轻颤；[3-8s] 撑身坐起、手指抓紧粗麻被、缓缓转头环顾四周。
镜头运动：[0-3s] 固定特写微推；[3-8s] 缓慢后拉至中近景。
动态细节：烛火忽明忽暗左右摇曳、烛光在墙面光影缓慢滑动、发丝随头部转动微微飘动、蛛网木梁背景虚焦。
国风写实漫剧、电影级光影、暗黑宫廷氛围。
```

### 视频 prompt（英文备用）
```
character motion: [0-3s] eyes snap open with pupil contraction and lash quiver; [3-8s] pushes upright, fingers grip coarse hemp quilt, slowly turns head scanning surroundings.
camera motion: [0-3s] locked extreme close-up with subtle push-in; [3-8s] slow dolly out to medium close-up.
dynamic detail: candle flame flickering side to side, light sliding across walls, hair strands swaying with head turn, blurred cobweb beams in background.
cinematic Chinese ancient-fantasy webcomic, dark palace, vertical 9:16.
```

### 命令
```bash
dreamina frames2video \
  --first "artifacts/冷宫有妖气/出图/第1集/镜头01_沈念惊醒.png" \
  --last  "artifacts/冷宫有妖气/出图/第1集/镜头02_沈念环顾.png" \
  --prompt "（粘贴上面中文 prompt）" \
  --duration 8 \
  --poll 90
```

### 检查清单
1. ✅ 首尾两帧人脸一致（同一定妆图衍生）
2. ✅ 0-3s 静→3s 起身节奏自然不突兀
3. ✅ 没出现额外角色（背景空）
4. ✅ 镜头不抖、人脸不变形

### 降级
若起身动作机械 → 减到 6s，重写"撑身坐起"为"上身先抬起再坐稳"分两段。

---

## Clip 2（时长 6s · 镜头 3 · image2video）

**模式**：图生视频 — 单帧
**首帧**：`出图/第1集/镜头03_铜镜自照.png`
**场景**：冷宫寝殿·铜镜角（夜/内）

### 视频 prompt（中文）
```
人物运动：沈念跌撞两步扑到铜镜前、双手扶镜框稳住身形、抬右手缓慢抚摸自己的脸颊与下唇、指尖停在唇边，呼吸急促胸口起伏。
镜头运动：从近景缓慢推进至面部特写、轻微跟拍贴合扶镜动作。
动态细节：烛光在斑驳铜镜面缓慢流动、镜中倒影清晰、发丝随移动飘动、铜镜边缘锈迹反光。
国风写实漫剧、电影级光影、暗黑宫廷氛围。
```

### 视频 prompt（英文备用）
```
character motion: Shen Nian stumbles two steps to bronze mirror, both hands grip frame, raises right hand slowly to touch own cheek and lower lip, fingertip rests on lip, breathing heavy with rising chest.
camera motion: close-up slowly pushing into facial close-up, slight tracking with the hand motion.
dynamic detail: candlelight flowing on tarnished bronze surface, clear reflection, hair strands moving, rust glints on mirror edge.
```

### 命令
```bash
dreamina image2video \
  --image "artifacts/冷宫有妖气/出图/第1集/镜头03_铜镜自照.png" \
  --prompt "（粘贴上面中文 prompt）" \
  --duration 6 \
  --poll 90
```

### 检查清单
1. ✅ 镜中倒影没出现"双脸"鬼影
2. ✅ 手指停唇边动作明确（不是抓脸）
3. ✅ 镜头不切到第三视角
4. ✅ 表情震惊而非微笑

### 降级
镜中倒影易翻车 → 改 5s、prompt 强化"镜中反射轮廓清晰、无重影、单一倒影"。

---

## Clip 3（时长 6s · 镜头 4 · image2video）

**模式**：图生视频 — 单帧蒙太奇
**首帧**：`出图/第1集/镜头04_身世闪回.png`（蒙太奇拼接图）
**场景**：记忆闪回（冷色颗粒）

### 视频 prompt（中文）
```
人物运动：身世闪回蒙太奇快速硬切——画面1入宫受封红盖头掀起、画面2搜出巫蛊人偶被官差喝令、画面3皇帝拂袖背影、画面4冷宫朱门重重合拢，每段1.5秒推进。
镜头运动：每段轻微缩放+硬切转场。
动态细节：颗粒噪点贯穿全片、冷雾在画面边缘流动、画面边缘暗角加深、整体青冷色调略带颗粒胶片质感。
国风写实漫剧、电影级光影、回忆滤镜。
```

### 视频 prompt（英文备用）
```
character motion: backstory flashback montage with rapid hard cuts — frame1 red veil lifted at coronation, frame2 voodoo doll discovered with guards shouting, frame3 emperor turning away in fury, frame4 cold palace vermilion doors slamming shut, each segment 1.5s.
camera motion: subtle zoom per segment with hard-cut transitions.
dynamic detail: film grain throughout, cold mist drifting along edges, vignette deepening, cool blue color grade with film texture.
```

### 命令
```bash
dreamina image2video \
  --image "artifacts/冷宫有妖气/出图/第1集/镜头04_身世闪回.png" \
  --prompt "（粘贴上面中文 prompt）" \
  --duration 6 \
  --poll 90
```

### 检查清单
1. ✅ 4 段画面有节奏感（不是一镜到底慢移）
2. ✅ 颗粒/冷雾贯穿（强化"回忆"感）
3. ✅ 没出现现代元素

### 降级
单帧蒙太奇 AI 理解差 → 降级方案：把蒙太奇拆 4 张静态图，改用 `multiframe2video --images img1,img2,img3,img4 --transition-prompt "硬切+缩放"×3 --transition-duration 1.5,1.5,1.5`。

---

## Clip 4（时长 8s · 镜头 5+6 · frames2video）

**模式**：图生视频 — 首尾帧
**首帧**：`出图/第1集/镜头05_小禾撞入.png`
**尾帧**：`出图/第1集/镜头06_柳娘子带队.png`
**场景**：冷宫寝殿（夜/内）

### 视频 prompt（中文）
```
人物运动：[0-4s] 小禾跌撞冲入扑抓沈念手臂、浑身发抖、泪滑落；[4-8s] 门帘掀开柳娘子假笑步入、身后两太监端托盘（白绫匕首毒酒）脚步沉稳逼近。
镜头运动：[0-4s] 中景固定；[4-8s] 门帘处缓慢横移入画。
动态细节：门帘掀开布料晃动、烛影晃动、小禾发丝凌乱、托盘上器物轻微反光、柳娘子衣袂摆动。
国风写实漫剧、电影级光影、暗黑宫廷氛围。
```

### 视频 prompt（英文备用）
```
character motion: [0-4s] Xiao He stumbles in clutching Shen Nian's arm, trembling, tears falling; [4-8s] door curtain lifts, Madam Liu enters with fake smile, two eunuchs behind carrying tray (white silk, dagger, poison wine), steady advancing steps.
camera motion: [0-4s] medium shot locked; [4-8s] slow lateral pan from curtain into frame.
dynamic detail: curtain fabric swaying, candle shadows wavering, Xiao He's hair disheveled, tray items glinting, Madam Liu's robe drifting.
```

### 命令
```bash
dreamina frames2video \
  --first "artifacts/冷宫有妖气/出图/第1集/镜头05_小禾撞入.png" \
  --last  "artifacts/冷宫有妖气/出图/第1集/镜头06_柳娘子带队.png" \
  --prompt "（粘贴上面中文 prompt）" \
  --duration 8 \
  --poll 90
```

### 检查清单
1. ✅ 小禾→柳娘子镜头切换流畅（不是硬切）
2. ✅ 太监 2 人始终在画面（不会消失）
3. ✅ 托盘三件套清晰可辨
4. ✅ 柳娘子表情温和假笑（不是凶相）

### 降级
4 人物切换易混乱 → 拆 Clip4a (5, 4s, image2video) + Clip4b (6, 4s, image2video)。

---

## Clip 5（时长 7s · 镜头 7+8A+8B · multiframe2video）

**模式**：图生视频 — 多帧交叉剪辑
**帧序列**：
- 帧1：`出图/第1集/镜头07_柳娘子俯视.png`（0-3s）
- 帧2：`出图/第1集/镜头08A_压制小禾.png`（3-5s）
- 帧3：`出图/第1集/镜头08B_鸩酒近唇.png`（5-7s）

**场景**：冷宫寝殿（夜/内）

### 视频 prompt（中文 · 2 段 transition）

**Transition 1 prompt（07→08A，3s）**：
```
柳娘子俯视假笑微微侧首眼神阴冷、镜头从低角度仰拍切到中景太监粗手捂住小禾嘴拖向门外、小禾挣扎踢腿掉鞋、烛影晃动。
```

**Transition 2 prompt（08A→08B，4s）**：
```
镜头切回柳娘子近景，柳娘子双手端起青瓷鸩酒壶将壶嘴缓缓递近沈念唇边、琥珀色鸩酒在壶嘴轻晃泛起苦杏仁气、沈念凤眼半垂咬紧牙关眼神疾转、烛光勾勒壶口与两人侧脸。
```

### 命令
```bash
dreamina multiframe2video \
  --images "artifacts/冷宫有妖气/出图/第1集/镜头07_柳娘子俯视.png,artifacts/冷宫有妖气/出图/第1集/镜头08A_压制小禾.png,artifacts/冷宫有妖气/出图/第1集/镜头08B_鸩酒近唇.png" \
  --transition-prompt "柳娘子俯视假笑微微侧首眼神阴冷、镜头从低角度仰拍切到中景太监粗手捂住小禾嘴拖向门外、小禾挣扎踢腿掉鞋、烛影晃动。" \
  --transition-prompt "镜头切回柳娘子近景，柳娘子双手端起青瓷鸩酒壶将壶嘴缓缓递近沈念唇边、琥珀色鸩酒在壶嘴轻晃泛起苦杏仁气、沈念凤眼半垂咬紧牙关眼神疾转、烛光勾勒壶口与两人侧脸。" \
  --transition-duration 3 \
  --transition-duration 4 \
  --poll 120
```

### 检查清单
1. ✅ 3 帧角色脸一致（07/08A/08B 同一定妆）
2. ✅ 第2段没把鸩酒画成水/茶
3. ✅ 沈念表情冷峻镇定（不哀求/不挣扎）
4. ✅ 太监粗暴但不血腥

### 降级
3 帧交叉剪辑复杂度高 → 拆 Clip5a (07→08A, 3s, frames2video) + Clip5b (08B, 4s, image2video)。

---

## Clip 6（时长 7s · 镜头 9+10 · frames2video）

**模式**：图生视频 — 首尾帧（觉醒爆发）
**首帧**：`出图/第1集/镜头09_觉醒情绪顶点.png`
**尾帧**：`出图/第1集/镜头10_图腾蔓延.png`
**场景**：冷宫寝殿（夜/内）

### 视频 prompt（中文）
```
人物运动：[0-3s] 沈念胸口炸开暗金热流光芒向外迸射照亮惊缩瞳孔、表情从震惊转为觉醒；[3-7s] 暗金图腾纹路从心口蔓延至双臂指尖、瞳孔骤缩成金色竖瞳、发丝被妖气掀起、柳娘子假笑凝固后退半步。
镜头运动：[0-3s] 特写急推；[3-7s] 近景环绕半圈带轻微震动。
动态细节：暗金妖气如热浪扩散、纹路如刺青从皮肤下点亮、烛火被气流吹偏、空气中细小光粒上升、发丝飘动。
国风写实漫剧、电影级光影、暗黑宫廷加暗金妖气、强动态。
```

### 视频 prompt（英文备用）
```
character motion: [0-3s] golden energy explodes from chest illuminating shocked contracted pupils, expression shifts from shock to awakening; [3-7s] dark-gold totem patterns spread from heart to fingertips, pupils contract to gold vertical slits, hair lifted by demonic aura, Madam Liu's smile freezes as she steps back.
camera motion: [0-3s] close-up rapid push; [3-7s] half orbit on medium close-up with slight shake.
dynamic detail: dark-gold aura like heat wave, patterns igniting beneath skin like tattoo, candles bent by gust, fine light particles rising, hair strands floating.
```

### 命令
```bash
dreamina frames2video \
  --first "artifacts/冷宫有妖气/出图/第1集/镜头09_觉醒情绪顶点.png" \
  --last  "artifacts/冷宫有妖气/出图/第1集/镜头10_图腾蔓延.png" \
  --prompt "（粘贴上面中文 prompt）" \
  --duration 7 \
  --poll 120
```

### 检查清单
1. ✅ 暗金纹路是"皮肤下亮起"不是"贴上去的金线"
2. ✅ 金色竖瞳清晰（不是普通金色圆瞳）
3. ✅ 柳娘子表情有变化（凝固后退）
4. ✅ 妖气方向一致（从胸口向外辐射）

### 降级
若纹路混乱 → 改 5s 只演爆发瞬间；纹路蔓延单独 Clip6b。

---

## Clip 7（时长 6s · 镜头 11 · image2video · 全集最炸爽点）

**模式**：图生视频 — 单帧（**建议跑 2-3 条挑稳的**）
**首帧**：`出图/第1集/镜头11_反杀化黑烟.png`
**场景**：冷宫寝殿（夜/内）

### 视频 prompt（中文）
```
人物运动：沈念一拳挥出带强烈残影、拳头贯穿柳娘子胸口位置、柳娘子身体从胸口向外炸开化为滚滚黑烟与黑色细碎灰烬如纸片漫天飞散、深蓝宫装空荡撕裂崩解从内向外瓦解最终堆落地面、地面残留一摊污血。
镜头运动：动态特写带轻微甩镜跟拳、慢动作 0.5x 强调贯穿瞬间然后恢复正常速度。
动态细节：黑烟翻滚扩散、黑灰漫天飘散像撕碎的纸、暗金妖气环绕拳头与黑烟对撞、衣袂崩解从布到碎片到灰烬的渐变。
国风写实漫剧、电影级爆裂动态光影、暗黑宫廷加暗金妖气、强冷色调高对比。
负面（写进 prompt）：禁血腥红血、禁内脏、禁断肢、柳娘子身体不能完整。
```

### 视频 prompt（英文备用）
```
character motion: Shen Nian punches with strong motion blur, fist piercing through Madam Liu's chest, body bursting from chest into rolling black smoke and fine black ash scattering like torn paper, dark-blue robe torn and collapsing from inside out finally heaping on floor, foul blood pool remains.
camera motion: dynamic close-up with slight whip pan following fist, 0.5x slow motion on impact then back to normal speed.
dynamic detail: rolling black smoke, ash drifting like shredded paper, dark-gold aura clashing with smoke, robe disintegration cloth→shred→ash gradient.
no bloody red, no organs, no severed limbs, Madam Liu's body must not stay intact.
```

### 命令
```bash
dreamina image2video \
  --image "artifacts/冷宫有妖气/出图/第1集/镜头11_反杀化黑烟.png" \
  --prompt "（粘贴上面中文 prompt）" \
  --duration 6 \
  --model_version seedance2.0_vip \
  --video_resolution 1080p \
  --poll 120
# 建议跑 2-3 次取最稳的那条
```

### 检查清单
1. ✅ 拳头贯穿瞬间清晰（不是擦边）
2. ✅ 柳娘子身体确实在崩解（不是完好站着）
3. ✅ 黑烟+黑灰，无血腥红血
4. ✅ 慢动作不卡顿
5. ✅ 沈念脸不变形（这是核心爽点脸要稳）

### 降级
- 单条出不来"崩解" → 拆 Clip7a（出拳穿透 2s, image2video）+ Clip7b（黑烟弥漫扩散 4s, image2video 用一张"黑烟爆开瞬间"图作首帧）
- 还不行 → 退到 5s 只演出拳与黑烟初炸，崩解留给下一 Clip 衔接

---

## Clip 8（时长 7s · 镜头 12 · image2video · 收尾钩子）

**模式**：图生视频 — 单帧
**首帧**：`出图/第1集/镜头12_收尾握拳.png`
**场景**：冷宫寝殿（夜/内）

### 视频 prompt（中文）
```
人物运动：[0-3s] 两太监瘫倒连滚带爬向门口逃出画面、小禾跪坐瞪眼僵立无血色、黑灰飘落；[3-7s] 沈念立于原地正面镜头垂眸看着自己抬起的右手、暗金图腾纹路如退潮般缓缓消退、金色竖瞳的金光渐隐回归正常凤眼但眼神冷冽锐利、缓缓握拳。
镜头运动：[0-3s] 中景固定；[3-7s] 近景缓慢推进至手部特写再回拉至面部。
动态细节：余烬在烛光中飘落、地面残留空衣污血灰烬未落定、烛火忽明忽暗、纹路消退时有微弱金光残留、握拳时关节轻响。
国风写实漫剧、电影级光影、暗黑宫廷加暗金余烬、肃杀冷冽。
```

### 视频 prompt（英文备用）
```
character motion: [0-3s] two eunuchs sprawled scrambling for door, Xiao He kneeling stunned wide-eyed pale, ash falling; [3-7s] Shen Nian stands front to camera, gazes at her raised right hand, dark-gold totem patterns receding like ebbing tide, gold vertical pupils fading to normal phoenix eyes with sharp cold gaze, slowly clenches fist.
camera motion: [0-3s] medium locked; [3-7s] slow push-in to hand close-up then pull back to face.
dynamic detail: embers drifting in candlelight, empty clothes and blood on floor, candle flickering, faint gold residue as patterns fade, subtle knuckle creak on fist clench.
```

### 命令
```bash
dreamina image2video \
  --image "artifacts/冷宫有妖气/出图/第1集/镜头12_收尾握拳.png" \
  --prompt "（粘贴上面中文 prompt）" \
  --duration 7 \
  --poll 120
```

### 检查清单
1. ✅ 沈念过渡态（图腾消退中、瞳孔金光渐隐）
2. ✅ 小禾跪坐震惊（不站立、不动作）
3. ✅ 太监有逃出动势（不是静止瘫地）
4. ✅ 地面空衣+灰烬清晰
5. ✅ 整体肃杀（不温馨/不明亮）

### 降级
若 7s 一镜难统筹"太监逃 + 沈念握拳"，拆 Clip8a（前 3s 固定中景，image2video）+ Clip8b（后 4s 沈念握拳特写，image2video 用一张"手部纹路消退"图作首帧）。

---

## 跑视频前 checklist

- [ ] `dreamina login` 已登录（OAuth 设备流）
- [ ] `dreamina user_credit` 余额够（视频比图贵 1-2 个数量级；8 Clip × 多跑 ≈ 至少几百积分）
- [ ] 工作目录 = `/Users/wesley/work/anime-armory`
- [ ] 落档目录 `出视频/第1集/` 已存在（写完 prompt 后 mkdir）

## 跑后归档规则

- 通过 → `mv /path/to/dreamina/download/*.mp4 "出视频/第1集/Clip<K>_<描述>.mp4"`
- 不通过 → `mv .../废稿.mp4 "common/废料/出视频/第1集/Clip<K>_废_<原因>.mp4"`
- 每条定稿 MP4 落档后 → 改 `00_总览.md` 状态 ✅ + `_进度.md` `视频` 列分子 +1
