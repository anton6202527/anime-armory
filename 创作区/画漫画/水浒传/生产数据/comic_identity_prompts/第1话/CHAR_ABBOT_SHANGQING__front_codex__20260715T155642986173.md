请用内置 image_generation 工具生成漫画角色首张专门定妆参考图。

角色 ID：CHAR_ABBOT_SHANGQING
视图：front / front full-body view, standing neutrally, face looking forward

本次没有已采纳角色图片作为附件。必须只依据下面的项目设定生成稳定、可复用的长线 front 设定图；这张图会成为后续 three_quarter / side / back / face 视图的参考锚点。
已附一张项目风格锚图片。它只用于继承线条、上色、明暗、材质和墨晕语言；不得继承其中人物的脸、发型、服装、体态、姿势、构图或具体场景。

角色设定摘录：
### 上清宫住持 CHAR_ABBOT_SHANGQING

- 功能：知晓规矩和后果的守门人，也暴露宗教机构在官权压力前的局限。
- 年龄/体态：六十岁左右，高瘦、背直，三十余年住持的克制与仪法感。
- 脸/眼/发：高额、清瘦颊、灰黑短须，上眼皮略沉但目光稳定。
- 衣装：青灰道袍、深褐缘边、不夸张的冠巾；不用明清影视金绣法衣套路。
- 禁漂移：不设计为阴险反派；不因恐惧而丢失一贯的高瘦轮廓、高额和灰黑须。
- 资产档位：`named_minimal`，至少 front / face。

项目定妆契约：
- 名称:上清宫住持
- 角色DNA:六十岁左右，高瘦背直、高额、清瘦颊、灰黑短须、上眼皮略沉但目光稳定，青灰道袍
- 年龄/形态继承:惊惧、劝阻、悲叹均继承高瘦轮廓、高额、短须和克制仪法感
- 禁继承:不得因伏魔殿场景变成阴险反派或金绣影视道长模板
- 备注:第1话连续出场16格并贯穿伏魔殿高潮，按 recurring_standard 管理；需 front/three_quarter/face 与证据化签核后才 ready
- 默认服装 OUTFIT_BASE:character_id:CHAR_ABBOT_SHANGQING；outfit_id:OUTFIT_BASE；name:上清宫住持常服/宫观主事装；identity_rank:年长宫观住持；日常会客、劝阻与主持宫观秩序，非大型斋醮法事；occasion_activity:宫观迎候；正式会客；伏魔殿前劝阻；layers:素色中衣；青灰交领道袍/大衫语法；必要时加深色素褐帔式外层；silhouette:高瘦背直，直身长衣、肩线平稳；袖量可读仪法感但不做舞台化拖袖；collar_neckline:交领方向固定，领缘窄而整洁；closure:右衽内系/布带系结，结位固定；sleeves:中等偏宽，腕处不过度堆积；hem:近踝，行走时只做自然提摆；waist_belt:素布绦或深色细带；headwear:灰黑巾帽/素冠的原创保守方案；由front锁定轮廓，不套现代道教制服；footwear:深色履，鞋头与底厚固定；materials:哑光细布/绢质外观；素布带；palette:青灰；烟墨；少量旧麻；patterns:无金绣云龙或游戏法阵纹；permanent_accessories:克制发须与巾帽轮廓；removable_accessories:素褐帔式外层；state_variants:palace_formal；warning_tense；hall_dust；continuity_keys:交领方向；巾帽轮廓；袖宽；系带高度；沾尘发生点；forbidden:金绣法衣常服化；现代统一制式道装直接照搬；仙侠披风飘带；影视版特定道长造型；明清宗教礼服混搭；uncertain:北宋龙虎山住持的日常定装缺直接实物链；以宋代分场合服饰文献与两宋材料语法保守原创；evidence_refs:SRC_CNSM_ZHAO_BOYUN；SRC_NMC_COSTUME；SRC_DAO_SONG_VESTMENTS；SRC_SHUIHU_SOURCE；status:confirmed

画面要求：
1. 生成单一主体 reference art，不要场景叙事，不要其他人物/生物、气泡、文字、logo、水印。
2. 单人站立全身正面定妆：从头顶到鞋底完整入画，脚/鞋完整可见，人物居中，面向镜头，中性表情，直立或轻微放松站姿。
3. 中性浅灰或低饱和纯色背景，柔和均匀光，头脸/头骨结构、永久标志、体表材质、服装主形制与标志配饰、体态比例必须清楚。
4. 保持项目基础视觉风格：自定义(宋画工笔淡彩×国漫写实人物×电影级光影，低饱和矿物色，粗粝江湖质感，竖向步移景异)；定妆图要清楚、稳定、少动态夸张，不要退化成低细节彩漫、Q 版或泛化韩漫脸。
5. 不得坐、蹲、跪、弯腰、倒地、挥砍、冲刺、摆战斗 pose；不得裁掉头发、手、脚、鞋或永久身份佩饰。
6. 不生成临时剧情手持物、画面左右站位或同框调度；只有项目定妆契约明确列为永久佩饰/身体特征的标志物才可出现。
7. 不要画成现代写真、游戏 UI、角色卡边框、设计表排版、三视图拼贴或多格拼图；本次只输出这一张 front 视图，画面里只能有一个完整角色。
8. 遵循项目登记的角色定妆画幅。
9. 生成完成后只回复一句完成，不要写文件、不要搜索文件系统、不要输出 Markdown。
