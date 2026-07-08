# PROD_STARBOX_APP 产品/App 定妆 prompt

资产身份注册：PROD_STARBOX_APP
品牌资产：BRAND_STARBOX
产品名称：星盒手账 App
产品类型：mobile_app
参考图/资产引用：本 prompt 生成的定妆图作为 image2image / 多参考母图，后续所有产品镜必须引用 PROD_STARBOX_APP。

Hero surfaces：
- 手机界面
- 今日手账草稿
- 明日清单
- 片尾 end card

UI states：
- HOME_SCATTERED: 星盒 | locked_text=照片、语音、待办 | 镜头01：痛点钩子，通知和碎片信息散落
- JOURNAL_DRAFT: 今日手账 | locked_text=照片、语音、待办、今日手账草稿 | 镜头03：卡片归入今日页面
- TOMORROW_LIST: 明日清单 | locked_text=明日清单、立即预约内测 | 镜头04：待办折叠到明日清单，轻露出 CTA
- ENDCARD: 星盒 | locked_text=星盒、把今天稳稳收好、立即预约内测 | 镜头06：片尾品牌收束

身份锁定句：
- 与产品参考图①同一款 App UI、同一 logo、同一品牌色、同一文字标识“星盒”。
- 品牌色严格保持 #2E9E97，辅助色 #F6C85F，文字清晰可读，不乱码。

Prompt locks：
- same PROD_STARBOX_APP mobile app interface
- same BRAND_STARBOX text logo 星盒
- brand color #2E9E97
- accent color #F6C85F
- Chinese UI text clear and readable
- no third-party real app UI

安全框：
- grid=8x8; core_in_center_4x4=True; keep_text_inside_center_6x6=True

负向：
- 不要改包装文字，不要变形 logo，不要改 logo，不要改品牌色，不要乱码，不要出现第三方真实 App UI。
