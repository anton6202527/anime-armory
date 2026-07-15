请用内置 image_generation 工具生成漫画角色的专门换装参考图。

用例：historical-scene / identity-preserve
角色 ID：CHAR_HONG_XIN
服装 ID：OUTFIT_MOUNTAIN_PLAIN

已附该角色当前采纳的 front 正面定妆图。它是身份参考：脸型、眼型/眼距、发际线、发型、年龄、体态和整体画风不得改变。
本次只替换为指定服装；原 front 中的旧服装、临时手持物、动作、场景和站位不得混入新服装。

角色设定摘录：
### 洪信 CHAR_HONG_XIN

- 功能：神话序章的行动主体和负面引信；他并非纯粹恶人，却把权势、面子和自信当成判断真相的依据。
- 年龄/体态：四十五岁左右，中等偏高，官员体态略厚，非武将肌肉型；上山后狼狈、沾尘，但不能突然变成滑稽丑角。
- 脸/眼/发：长方圆脸，下颌软但不肥肿；眼裂偏窄、眼距正常，情绪从稳拿转为心虚；发际线稍高，戴宋代官员幞头时仍锁定额角与鬓发。
- 衣装：朝堂与出使为绛/深褐系圆领官袍、深色幞头与革带；上山更换素色窄袖布衣、麻履，背黄罗诏包，持银手炉。
- 永久识别：微高发际线、窄眼、右眉尾轻微下压、直而略厚的鼻梁、指节圆润的非劳作手。
- 禁漂移：不使用任何已知影视演员脸；不变为俗套奸臣尖脸、武将壮汉或喜剧化肥官。
- 资产档位：`recurring_standard`，第1–2话须 front / three_quarter / face 三项业界基础定妆视图。

角色身份契约：
- 名称:洪信
- 角色DNA:四十五岁左右，长方圆脸、窄眼、正常眼距、微高发际线、右眉尾轻压、直厚鼻梁、中等偏高略厚体态、非劳作型圆润指节；不得演员脸或奸臣尖脸模板
- 年龄/形态继承:官服出使与布衣上山共享脸型、眼型、眼距、发际线、体态；只切换服装和泥尘状态
- 禁继承:不继承影视演员肖像、剧照构图、临时手持物、摔倒姿势、虎蛇同框遮挡
- 备注:第1-2话高曝光；前/三分之四/脸三视图及model pack人工签核后才ready
- 默认服装 OUTFIT_COURT_ENVOY:character_id:CHAR_HONG_XIN；outfit_id:OUTFIT_COURT_ENVOY；name:朝廷使臣公服/旅途官装；identity_rank:殿前太尉、奉诏使臣；非武将临阵；occasion_activity:入朝受诏；长途出使；宫观正式会见；layers:内层中衣（不外露抢戏）；绛褐低饱和圆领长袍；长途可加素色防尘外披；silhouette:直身长袍、肩线克制、下摆便于步行；以官帽和带具读身份，不靠甲胄；collar_neckline:圆领，领缘窄而整洁；closure:右侧隐蔽系结/结构不外露；不得画成现代正中拉链或盘扣；sleeves:常服宽度适中、腕部不作仙侠飘袖；hem:近踝，行旅状态仅自然提摆；waist_belt:深色革带，饰件从简；headwear:深色幞头；翅形与长度保持同一版本；footwear:深色靴，旅途允许尘土但不改形；materials:哑光绢/细织物外观；皮革带靴；palette:绛褐；墨黑；烟褐；patterns:主体无大面积团花；细节不抢脸；permanent_accessories:官带（本套身份锚）；removable_accessories:旅途外披；state_variants:court_clean；travel_dust；mountain_arrival；continuity_keys:幞头翅形；圆领宽度；革带高度；靴色；尘土发生点；forbidden:武将甲胄；明清补服/顶戴；影视版特定整套造型；大金带与越级华饰；随机龙纹；uncertain:北宋嘉祐具体公服色与带饰受官阶、场合影响；未取得更直接制度与图像证据前按低饱和保守设计，不宣称精确复原；evidence_refs:SRC_CNSM_ZHAO_BOYUN；SRC_DPM_QINGMING；SRC_NMC_COSTUME；SRC_SHUIHU_SOURCE；status:confirmed

本套服装契约：
character_id:CHAR_HONG_XIN；outfit_id:OUTFIT_MOUNTAIN_PLAIN；name:斋戒上山素衣；identity_rank:奉天师要求斋戒更衣的官员；以行动便利为主；occasion_activity:独自登山；雨后林地；遇虎蛇；layers:素色内衣；灰褐交领/斜襟窄袖布衣；必要时短外层；silhouette:收袖、束腰、下摆利于攀行，仍保留成年官员整洁习惯；collar_neckline:克制交领/斜襟，不露现代T恤领；closure:布带系结，方向固定；sleeves:窄袖；hem:膝下至小腿，便于登山；waist_belt:素布带；headwear:不戴正式幞头；发式整齐固定；footwear:麻履/便于山行的布鞋语法；materials:麻/粗细适中的布质外观；palette:素灰；土褐；旧麻色；patterns:无显眼纹样；state_variants:clean_departure；humid_mountain；fall_dust；continuity_keys:交领方向；布带结位；袖宽；跌倒后尘湿范围；forbidden:官袍幞头残留；仙侠飘带；现代汉服影楼层叠；把诏包/银炉固化为衣饰；uncertain:小说只明确斋戒更衣，具体素服结构为证据约束下的原创设计；evidence_refs:SRC_CNSM_ZHAO_BOYUN；SRC_DPM_QINGMING；SRC_NMC_COSTUME；SRC_SHUIHU_SOURCE；status:confirmed

画面要求：
1. 单人站立全身正面参考，从头顶到鞋底完整入画，中性表情和站姿，手脚与鞋履不裁切。
2. 中性浅灰或低饱和纯色背景，柔和均匀光；不要场景叙事、其他人物、气泡、文字、logo 或水印。
3. 严格执行服装的层次、轮廓、领襟、开合、袖摆、带具、冠帽、鞋履、材质、色域、佩饰和禁用项；不以泛化“古装/汉服/仙侠”先验替代契约。
4. 保持项目基础视觉风格：自定义(宋画工笔淡彩×国漫写实人物×电影级光影，低饱和矿物色，粗粝江湖质感，竖向步移景异)。不复制影视演员脸、剧照构图或某版影视整套造型。
5. 画幅固定为 3:4，这是可长期复用的服装锚点，不是剧情分镜。
6. 生成完成后只回复一句完成，不要写文件、不要搜索文件系统、不要输出 Markdown。
