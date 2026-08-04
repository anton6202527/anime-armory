export type ToolboxRecipe = "video" | "storyboard" | "interior";

export type ToolboxTemplate = {
  id: string;
  title: string;
  description: string;
  cover: string;
  category: "运镜" | "电商" | "特效" | "转场" | "角色" | "分镜" | "空间";
  recipe: ToolboxRecipe;
  inputLabel: string;
  resultLabel: string;
  prompt: string;
};

export type ToolboxClassic = {
  id: string;
  title: string;
  description: string;
  cover: string;
};

const tool = (
  id: string,
  title: string,
  description: string,
  cover: string,
  category: ToolboxTemplate["category"],
  prompt: string,
  recipe: ToolboxRecipe = "video",
  inputLabel = "上传参考图像",
  resultLabel = recipe === "video" ? "视频生成结果" : "图片生成结果",
): ToolboxTemplate => ({ id, title, description, cover, category, prompt, recipe, inputLabel, resultLabel });

// Snapshot of the toolbox cards visible in LibTV on 2026-08-04. Covers are
// stored locally so the canvas remains usable when the source CDN is offline.
export const TOOLBOX_TEMPLATES: ToolboxTemplate[] = [
  tool("left-arc", "左弧滑行", "围绕主体沿左侧弧线平稳滑行，形成明显的空间视差和高级产品运镜。", "/toolbox-covers/01-left-arc.webp", "运镜", "主体始终保持画面中心，摄影机沿左侧弧线平稳横移并轻微向前推进；保持主体结构、背景连续性和真实运动模糊，结尾稳定停在英雄构图。"),
  tool("ecommerce-phone-pop", "电商手机弹出效果", "从手机屏幕中的商品图切换到真实三维商品与完整广告环境。", "/toolbox-covers/02-ecommerce-phone.webp", "电商", "纯白无界影棚中，一只手竖直握住手机，屏幕展示用户上传的商品。手指点击后商品图消失，手机向下移开，真实商品从手机后方显现并由二维平滑扩展为高精度三维实体；环境根据商品类别逐层搭建，最后形成稳定、精致的商业英雄镜头。"),
  tool("coffee-entrance", "咖啡杯出场", "让咖啡杯与咖啡元素以广告级节奏进入画面，突出热气、材质和香气感。", "/toolbox-covers/03-coffee-entrance.webp", "电商", "咖啡杯从画外流畅进入中心，杯体稳定落位，咖啡液与细腻热气形成短暂动态层次；镜头轻推并聚焦杯壁材质和品牌展示面，背景保持干净，最终定格为温暖高级的产品广告画面。"),
  tool("turntable-360", "360旋转展示", "围绕单一商品完成一周旋转展示，持续保持形体、材质与比例一致。", "/toolbox-covers/04-360-rotate.webp", "运镜", "商品位于干净影棚中心并保持完全一致，摄影机以恒定半径完成顺时针360度环绕，光线在材质表面自然流动；无形变、无额外物体、无跳帧，结尾回到初始正面机位。"),
  tool("robot-arm", "机械臂视角", "模拟工业机械臂的精准轨迹，完成大范围推进、俯仰与环绕组合运镜。", "/toolbox-covers/05-robot-arm.webp", "运镜", "使用机械臂摄影机的精准轨迹，从高位快速下降并向主体推进，随后沿主体侧面完成小角度环绕；速度变化平滑、焦点锁定、空间透视真实，结尾停在具有冲击力的近景。"),
  tool("live-2d", "Live 2D", "将单张角色立绘转换为轻量呼吸、眨眼、发丝和服装摆动效果。", "/toolbox-covers/06-live-2d.webp", "角色", "保持角色身份、五官、服装和构图完全一致，仅添加自然眨眼、轻微呼吸、发丝与衣角的小幅摆动；动作循环柔和，不改变画风，不出现肢体畸变或背景漂移。"),
  tool("pupil-zoom", "瞳孔拉近", "从人物近景高速推进到瞳孔特写，用眼部反光承接下一段画面。", "/toolbox-covers/07-eye-zoom.webp", "运镜", "镜头从人物面部近景快速而平滑地推进至单侧瞳孔极特写，焦点始终锁定眼睛；瞳孔反光逐渐填满画面并作为转场入口，保持面部结构稳定、无五官漂移。"),
  tool("bird-disintegrate", "飞鸟解体", "主体分解成飞鸟群并向空间散开，保留清晰的形态转换过程。", "/toolbox-covers/08-bird-disintegrate.webp", "特效", "主体边缘先出现细小黑色飞鸟，随后身体由外向内连续分解成大规模鸟群并向远处飞散；转换过程层次清楚、遮挡真实，背景和摄影机保持稳定，最终只留下渐远的鸟群。"),
  tool("break-box", "破盒而出", "商品从封闭包装中冲出，结合碎片、粉尘与冲击波形成强烈登场。", "/toolbox-covers/09-box-break.webp", "电商", "包装盒位于画面中心并短暂蓄力，商品从内部高速破盒而出；纸板碎片和粉尘向外扩散但不遮挡商品，镜头同步轻微后撤并最终锁定完整商品英雄镜头。"),
  tool("product-impact", "商品震撼登场", "通过强光、烟尘和镜头推进完成适合广告开场的产品英雄镜头。", "/toolbox-covers/10-product-hero.webp", "电商", "暗场中轮廓光逐步勾勒商品，冲击光与环境粒子同时爆发，商品稳定进入中心；摄影机低机位快速推进后减速，材质细节清晰，最终形成高级商业英雄构图。"),
  tool("right-arc", "右弧滑行", "围绕主体沿右侧弧线平稳滑行，与左弧运镜形成镜像选择。", "/toolbox-covers/01-left-arc.webp", "运镜", "主体始终保持画面中心，摄影机沿右侧弧线平稳横移并轻微向前推进；保持主体结构、背景连续性和真实运动模糊，结尾稳定停在英雄构图。"),
  tool("left-arc-alt", "左弧滑行", "左侧弧线滑轨的备用模板，适合人物、建筑和产品的空间展示。", "/toolbox-covers/01-left-arc.webp", "运镜", "摄影机从主体右前方出发，沿左侧弧形轨迹移动到正侧方，运动速度先快后慢；主体比例与朝向稳定，空间层次随视差自然展开。"),
  tool("inverted-space", "颠倒空间", "让场景重力方向翻转，墙面、地面和主体形成超现实空间倒置。", "/toolbox-covers/13-inverted-space.webp", "特效", "摄影机缓慢推进，场景空间以连续、可读的方式翻转180度，地面转为顶部、墙面成为新的地面；主体动作遵循新的重力方向，结构连续且无突变。"),
  tool("zero-gravity", "反重力漂浮", "让人物或商品缓慢离地，周围小物随能量变化产生真实漂浮层次。", "/toolbox-covers/14-zero-gravity.webp", "特效", "主体从静止状态逐渐失去重力并缓慢上升，衣物、发丝和周围细小物体以不同速度漂浮；摄影机轻微环绕，动作克制、物理连续、主体外观保持一致。"),
  tool("particle-dissolve", "粒子融解", "主体从边缘开始转化为发光粒子并随风散去，可用作消失或转场。", "/toolbox-covers/15-particle-dissolve.webp", "特效", "主体从一侧边缘开始逐层融解为细密发光粒子，粒子沿统一风向飘散并留下短暂光迹；形体消失过程连续清晰，背景不变，最终粒子完全淡出。"),
  tool("travel-zoom-in", "旅拍转场 zoom in", "快速推入前景遮挡物，在遮挡瞬间无缝连接下一处旅行场景。", "/toolbox-covers/16-travel-zoom-in.webp", "转场", "摄影机快速向前推进，利用门洞、树干或人物等前景完全遮挡画面；遮挡瞬间切换到下一场景并延续相同运动方向和速度，曝光、构图与主体位置自然衔接。"),
  tool("travel-zoom-out", "旅拍转场 zoom out", "从局部细节快速后拉，以匹配构图连接到更开阔的下一场景。", "/toolbox-covers/17-travel-zoom-out.webp", "转场", "镜头从局部特写快速向后拉远，画面结构逐渐展开；在运动最强处匹配切换至下一旅行场景并继续后拉，保持中心主体和地平线位置连续。"),
  tool("travel-rotate-right", "旅拍转场 向右旋转", "使用向右甩镜和旋转模糊连接两个构图相近的旅行画面。", "/toolbox-covers/18-travel-rotate-right.webp", "转场", "摄影机向右快速旋转并产生自然方向性运动模糊，在模糊峰值切换到下一场景；新场景继续相同角速度后平稳减速，主体位置和光线方向匹配。"),
  tool("travel-rotate-left", "旅拍转场 向左旋转", "使用向左甩镜和旋转模糊连接两个构图相近的旅行画面。", "/toolbox-covers/19-travel-rotate-left.webp", "转场", "摄影机向左快速旋转并产生自然方向性运动模糊，在模糊峰值切换到下一场景；新场景继续相同角速度后平稳减速，主体位置和光线方向匹配。"),
  tool("travel-growth", "旅拍转场 生长", "利用植物、建筑或纹理生长铺满画面，再揭示下一旅行地点。", "/toolbox-covers/20-growth.webp", "转场", "前景植物或纹理沿画面快速生长并逐渐覆盖镜头，在完全遮挡时切换到下一地点；遮挡元素反向散开，保持运动连贯、色彩匹配和自然景深。"),
  tool("hero-angle", "英雄视角", "低机位仰拍配合环绕与轮廓光，强化人物或商品的力量感。", "/toolbox-covers/21-hero-angle.webp", "运镜", "摄影机从低机位缓慢向主体推进并做小幅环绕，背景线条向主体汇聚，轮廓光勾勒清晰；主体保持稳固姿态，最终定格为具有压迫感的英雄镜头。"),
  tool("fashion-motion", "AI模特服饰动态展示", "让模特自然转身、行走并展示服装版型、面料和细节。", "/toolbox-covers/22-fashion-model.webp", "角色", "模特在干净空间中完成自然走步、半转身和轻微摆姿，重点展示服装正面、侧面与面料垂坠；面部、身材、服装纹理与颜色始终一致，动作符合真实人体结构。"),
  tool("robot-arm-alt", "机械臂视角", "机械臂高速轨迹的扩展模板，强调俯冲、穿越与精准停机。", "/toolbox-covers/23-robot-arm-alt.webp", "运镜", "摄影机以机械臂轨迹从远处高速俯冲，穿过前景后贴近主体侧面完成半环绕，最终精准停机；运动分段清晰、无突跳、焦点持续锁定主体。"),
  tool("storyboard-noir", "大师分镜九宫格-经典暗调", "把故事简述转换成九个构图、景别和叙事节奏明确的黑白电影分镜。", "/toolbox-covers/24-storyboard-noir.webp", "分镜", "根据故事简述生成九个连续镜头：每格明确景别、人物动作、场景关系和叙事推进；统一使用经典黑白暗调电影风格、高对比侧光、丰富灰阶和清晰焦点，九格人物与空间保持连续。", "storyboard", "输入故事简述", "九宫格分镜结果"),
  tool("interior-preview", "AI室内装修效果预览", "依据房间照片和装修要求生成结构稳定、材质统一的室内改造预览。", "/toolbox-covers/25-interior-preview.webp", "空间", "保持原始房间结构、门窗位置和摄影机视角不变，依据用户要求替换墙面、地面、灯具、家具与软装；材质真实、比例合理、光线统一，输出装修后的高质量室内预览。", "interior", "上传房间照片", "装修效果预览"),
];

export const TOOLBOX_CLASSICS: ToolboxClassic[] = [
  { id: "king-of-comedy-gunfight", title: "喜剧之王-枪战", description: "用狭小空间、快速反应与错位调度复现紧张中带喜感的枪战节奏。", cover: "/toolbox-classics/01-king-of-comedy-gunfight.webp" },
  { id: "king-of-comedy-tycoon", title: "喜剧之王-神秘富豪", description: "通过身份反差、停顿与人物反应镜头构建戏剧性揭示。", cover: "/toolbox-classics/02-king-of-comedy-tycoon.webp" },
  { id: "god-of-cookery-contest", title: "食神-食神大赛", description: "以食物特写、评委反应和快速剪辑组织夸张的比赛场面。", cover: "/toolbox-classics/03-god-of-cookery-contest.webp" },
  { id: "explosive-meatball", title: "食神-撒尿牛丸", description: "用弹性、冲击和群体反应突出食物的夸张喜剧效果。", cover: "/toolbox-classics/04-explosive-meatball.webp" },
  { id: "cj7-fan", title: "七仔-修风扇", description: "通过可爱角色动作、机械故障与反应镜头形成轻喜剧桥段。", cover: "/toolbox-classics/05-cj7-fan.webp" },
];
