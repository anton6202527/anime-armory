# MV 舞蹈编排与动作卡点指南 (Dance Choreography)

MV 的灵魂在于“音画同步”。对于包含舞蹈（Dance）、表演（Performance）或高强度动作的 MV，必须遵循本指南来确保 AI 生成的动作具有力量感、节奏感且不崩坏。

## 1. 舞蹈编排核心原则

- **动作峰值 (Action Peak)**：舞蹈的“击中点（Hit）”必须严丝合缝地对齐 `beatgrid` 中的 `downbeat` 或强鼓点（Snare/Kick）。
- **五帧编排法**：
    1. **起势 (Anticipation)**：动作开始前的准备姿态。
    2. **蓄力 (Load)**：能量积蓄，通常伴随身体微缩。
    3. **击中 (Hit/Peak)**：能量爆发的最顶点，动作幅度最大或停顿感最强。
    4. **延伸 (Extension)**：动作惯性的余波，发丝、衣摆继续摆动。
    5. **收势 (Recovery)**：回到稳态，为下一拍准备。
- **锁姿态动背景 (Pose Lock)**：对于复杂舞步，首帧必须锁死核心姿态，视频仅负责完成位移。

## 2. 舞蹈子类 (Action Family)

| 类别 | 节奏取向 | 视觉特征 | Prompt 建议 |
|---|---|---|---|
| `dance_sharp` | 爵士 / 机械 / Popping | 动作短促、力量感极强、位移小 | sharp movements, robotic isolation, hard hits, sudden stops |
| `dance_fluid` | 现代 / 国风 / 芭蕾 | 动作连贯、大开大合、丝滑 | graceful flow, long lines, seamless transitions, continuous motion |
| `dance_street` | 街舞 / Hiphop | 律动感强、重心低、肢体夸张 | rhythmic bounce, swag, low center of gravity, power moves |
| `performance_vocal` | 演唱 / 舞台 | 麦克风互动、手势、面部表情 | expressive face, microphone play, stage presence, subtle swaying |

## 3. 力量等级 (Energy Level)

在 Prompt 中显式定义力量等级，驱动 AI 的运动幅度：

- **Level 1-3 (Low)**: 呼吸感、轻微摆动、抬头、垂眸。
- **Level 4-6 (Medium)**: 步行、转头、抬手、轻微律动。
- **Level 7-8 (High)**: 转身、小跳、挥臂、快速位移。
- **Level 9-10 (Extreme)**: 爆发舞步、空翻、瞬间定格（Power Move）、光效炸裂。

## 4. 空间与轴线锁 (Space & Axis Lock)

防止 AI 在生成舞蹈时人物位置和朝向乱跳：

- **Eyeline Lock**: 明确视线方向（看向镜头、看向侧面、看向指尖）。
- **Movement Vector**: 明确运动轴线（画左至画右、深处向镜头推进）。
- **Grounding**: 强调双脚与地面的接触感，防止“漂浮”现象。

## 5. 动态细节 (Secondary Motion)

增强动作说服力的物理惯性描述：
- `Physics-based hair and clothing movement following the momentum of the dance.`
- `Particles/Dust kicking up from the floor on the beat hit.`
- `Motion blur on limbs during the peak of the action.`

## 6. 卡点 Prompt 示例

```text
[Chorus Clip]
动作：dance_sharp (爵士舞动作)
力量等级：Level 9
动作链：右臂向斜上方瞬间击出(Hit)并定格。
动作峰值：在 0.8s (对齐 48.5s downbeat) 处到达动作顶点。
镜头：快推(Fast Zoom-in)至半身特写。
细节：发丝和项链随击打动作产生强烈的惯性抖动。
```
