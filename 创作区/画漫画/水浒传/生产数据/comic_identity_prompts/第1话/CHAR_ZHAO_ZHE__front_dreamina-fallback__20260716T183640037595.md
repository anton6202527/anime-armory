请基于附件风格参考生成漫画角色首张专门定妆参考图。

角色 ID：CHAR_ZHAO_ZHE
视图：front / front full-body view, standing neutrally, face looking forward

本次没有已采纳角色图片作为附件。必须只依据下面的项目设定生成稳定、可复用的长线 front 设定图；这张图会成为后续 three_quarter / side / back / face 视图的参考锚点。
已附一张项目风格锚图片。它只用于继承线条、上色、明暗、材质和墨晕语言；不得继承其中人物的脸、发型、服装、体态、姿势、构图或具体场景。

角色设定摘录：
### 赵哲 CHAR_ZHAO_ZHE

- 功能：与文彦博首先请求宽刑薄税与赈济，建立“朝廷并非无人努力，但结果仍失效”。
- 外形：年长宰相，体态端方，发须花白；紫褐官袍，低饱和。
- 资产档位：`named_minimal`。

项目定妆契约：
- 名称:赵哲
- 角色DNA:年长宰相，端方略厚体态，发须花白，紫褐低饱和官袍，眉目忧民而克制
- 年龄/形态继承:朝堂奏对共享端方体态、花白发须和紫褐官袍
- 禁继承:不得与文彦博或范仲淹换脸、换官袍色阶
- 备注:第1话具名官员，至少front和face
- 默认服装 OUTFIT_BASE:character_id:CHAR_ZHAO_ZHE；outfit_id:OUTFIT_BASE；name:朝堂宰执公服·紫褐；identity_rank:年长宰执；紫宸殿奏对；occasion_activity:持笏奏对；侍立；layers:素中衣；低饱和紫褐圆领长袍；silhouette:端方略厚体态，衣身垂直稳重，与文彦博偏瘦轮廓互斥；collar_neckline:圆领；closure:内隐系结；sleeves:中等偏宽，不堆积；hem:近踝；waist_belt:深褐细带具；headwear:黑色展脚幞头，冠体稍低稳；footwear:深色靴；materials:哑光细织物；皮革带靴；palette:紫褐；墨黑；暗棕；patterns:主体无补子或强品阶纹样；permanent_accessories:幞头；细带具；removable_accessories:笏板（剧情手持）；state_variants:court_concerned；continuity_keys:花白发须；稍厚体态；紫褐色值；幞头脚形；带高；forbidden:明代补服；清代顶戴；与文彦博/范仲淹换色换体态；夸张金玉带；影视定型造型；uncertain:紫褐是同框角色区分色，不单独作官品断代证据；evidence_refs:SRC_NMC_COSTUME；SRC_DPM_FUTOU；SRC_DPM_QINGMING；SRC_SHUIHU_SOURCE；status:confirmed

画面要求：
1. 生成单一主体 reference art，不要场景叙事，不要其他人物/生物、气泡、文字、logo、水印。
2. 单人站立全身正面定妆：从头顶到鞋底完整入画，脚/鞋完整可见，人物居中，面向镜头，中性表情，直立或轻微放松站姿。
3. 中性浅灰或低饱和纯色背景，柔和均匀光，头脸/头骨结构、永久标志、体表材质、服装主形制与标志配饰、体态比例必须清楚。
4. 保持项目基础视觉风格：自定义(宋画工笔淡彩×国漫写实人物×电影级光影，低饱和矿物色，粗粝江湖质感，竖向步移景异)；定妆图要清楚、稳定、少动态夸张，不要退化成低细节彩漫、Q 版或泛化韩漫脸。
5. 不得坐、蹲、跪、弯腰、倒地、挥砍、冲刺、摆战斗 pose；不得裁掉头发、手、脚、鞋或永久身份佩饰。
6. 不生成临时剧情手持物、画面左右站位或同框调度；只有项目定妆契约明确列为永久佩饰/身体特征的标志物才可出现。
7. 不要画成现代写真、游戏 UI、角色卡边框、设计表排版、三视图拼贴或多格拼图；本次只输出这一张 front 视图，画面里只能有一个完整角色。
8. 画幅固定为 3:4，不得输出其他比例。
9. 生成完成后只回复一句完成，不要写文件、不要搜索文件系统、不要输出 Markdown。
