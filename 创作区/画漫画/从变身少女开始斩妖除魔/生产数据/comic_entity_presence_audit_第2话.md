# 漫画实体在场契约机检 · 第2话

- 格 30 · registry 实体 5 · 显式排程格 0 · warn 2 · info 0

## Findings

- ⚠️ `mentioned_not_bound` P026 画面描述提到「虎山神」（registry 实体 MON_TIGER_SHANSHEN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。
- ⚠️ `mentioned_not_bound` P030 画面描述提到「虎妖」（registry 实体 MON_TIGER_SHANSHEN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。
