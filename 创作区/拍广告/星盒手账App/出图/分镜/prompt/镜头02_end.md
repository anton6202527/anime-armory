# 镜头02 尾帧 出图 prompt

## 镜头信息
- 场景：书桌前
- 镜头：中近景，主角坐下，手停在空白页面上，手机角标保留星盒
- 时长：5s
- 类型：end_frame continuity handoff
- 安全框：grid=8x8; core_in_center_4x4=True; keep_text_inside_center_6x6=True

## 资产身份注册
- 产品资产：PROD_STARBOX_APP
- 品牌资产：BRAND_STARBOX
- 参考图/资产引用：出图/共享/asset_registry.json；出图/共享/prompt/产品_PROD_STARBOX_APP.md；出图/共享/prompt/品牌_BRAND_STARBOX.md
- image2image / 多参考：使用 PROD_STARBOX_APP 定妆母图 + BRAND_STARBOX 文字标识作为产品和品牌参考。

## 画面 prompt
young female freelancer in casual homewear, tired but calm, blank journal page, smartphone corner shows Starbox logo text 星盒 and teal accent, warm desk lamp, realistic film look, no celebrity likeness, text readable

## 身份锁定句
与产品参考图①同一款 App UI、同一 logo、同一品牌色 #2E9E97；同一文字标识“星盒”；UI 文案清晰可读，不乱码。

## 产品/品牌锁
手机角标保留 BRAND_STARBOX，不出现其他 App 或真实第三方界面。

## 文字锁
文字清晰可读，准确显示并保留原文；CTA、slogan、法律声明保持在中心安全区，不乱码。

## 构图与光位
realistic cinematic vertical ad, warm low-contrast desk light, product/core UI inside center 4x4, text inside center 6x6, leave motion headroom for image-to-video.

## 尾帧接力
need_end_frame：true
transition：主角手指靠近手机屏幕，切入界面特写
本尾帧应作为下一镜首帧接力构图，动作不在峰值，保留运镜余量。

## 负向
不要改包装文字；不要变形 logo；不要改 logo；不要改品牌色；不要乱码；不要出现第三方真实 App UI；不要明星脸；不要医疗/心理疗效暗示；不要把 CTA 或法律声明贴边。
