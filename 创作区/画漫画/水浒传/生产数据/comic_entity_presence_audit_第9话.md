# 漫画实体在场契约机检 · 第9话

- 格 48 · registry 实体 68 · 显式排程格 0 · warn 2 · info 0

## Findings

- ⚠️ `mentioned_not_bound` P030 画面描述提到「王进」（registry 实体 CHAR_WANG_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters）；不入画则改写描述，或在该格写 unbound_mention_ack.CHAR_WANG_JIN 签收理由。
- ⚠️ `mentioned_not_bound` P048 画面描述提到「王进」（registry 实体 CHAR_WANG_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters）；不入画则改写描述，或在该格写 unbound_mention_ack.CHAR_WANG_JIN 签收理由。
