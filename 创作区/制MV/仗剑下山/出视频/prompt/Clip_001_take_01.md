# Clip_001 take_01 视频生成任务

- 生视频模型：manual
- 生视频渠道：manual
- 分辨率：720p
- 帧率：24fps
- 质量档：标准档
- 本镜质量档意图(quality_tier)：n/a  # high→后端 pro/高质量档，fast→量产省档，n/a→该后端无档（不改后端，仅意图）
- 运动参考(motion_reference)：不适用（非舞蹈/环绕镜或后端不支持视频参考）
- 模型能力：reference_images=False start_end_frames=False native_audio=False
- 渠道类型：manual；官方API=False
- 首帧：`出图/共享/图片/定妆_少年_常态.png`
- 尾帧：不使用
- 时长：3.413s
- 转场：卡点硬切
- 动作家族：vfx_burst/sword_pose
- 动作峰值：3.2s
- 转场母题：卡点硬切
- 景别：中近景
- 运镜：极缓推，保持定妆稳定
- 光影：青白冷晨光，脸部柔和可读
- 参考输入：出图/共享/图片/定妆_少年_常态.png, LOC_MOUNTAIN_GATE, PROP_QINGFENG_SWORD

## inherited_contract
- lead_id：CHAR_LEAD_YOUNG
- lead_identity_anchor：白衣束发玄发带·眉目清俊倔强眼·背青锋墨鞘长剑·玄色腰穗
- reference_group：REF_LEAD_YOUNG
- forbidden_drift：换脸, 换发型, 换主服装, 丢失青锋长剑, 新增无关人物, 现代物件, 文字/logo/水印, 生成原生人声

## continuity
- start_state：定妆亮相首帧：继承定妆锚点，主体稳定入画
- action：白衣少年立于山雾前，衣袂轻动，手扶青锋长剑，眼神从平静转为坚定
- end_state：定妆亮相尾帧：动作重心完成，留出卡点硬切接点
- constraints：同一主角脸、服装、青锋长剑、青白墨主色、段落场景 setup 必须连续
- negative：不要换脸、不要换衣、不要新增人物、不要改变场景、不要生成文字/logo/水印、不要生成原生人声

## Prompt
人物运动：白衣少年立于山雾前，衣袂轻动，手扶青锋长剑，眼神从平静转为坚定；动作家族：vfx_burst/sword_pose；镜头运动：极缓推，保持定妆稳定；光影继承：青白冷晨光，脸部柔和可读；动态细节：发丝、衣摆、光斑或环境粒子随节拍变化；卡点约束：动作峰值对齐 3.2s；转场母题：卡点硬切；继承约束：不得重定脸、服装、长剑、场景 setup、光色基调；声音约束：无对白、无旁白、不要生成原生人声。
