# 漫画实体在场契约机检 · 第7话

- 格 48 · registry 实体 51 · 显式排程格 0 · warn 1 · info 4

## Findings

- ℹ️ `mentioned_not_bound` P001 台词/旁白提到「史太公」（registry 实体 CHAR_SHI_TAIGONG）但未绑定；若仅口头提及可忽略，若要入画需补 references。
- ℹ️ `mentioned_not_bound` P006 台词/旁白提到「朱武」（registry 实体 CHAR_ZHU_WU）但未绑定；若仅口头提及可忽略，若要入画需补 references。
- ℹ️ `mentioned_not_bound` P006 台词/旁白提到「陈达」（registry 实体 CHAR_CHEN_DA）但未绑定；若仅口头提及可忽略，若要入画需补 references。
- ℹ️ `mentioned_not_bound` P006 台词/旁白提到「杨春」（registry 实体 CHAR_YANG_CHUN）但未绑定；若仅口头提及可忽略，若要入画需补 references。
- ⚠️ `mentioned_not_bound` P017 画面描述提到「史进」（registry 实体 CHAR_SHI_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。
