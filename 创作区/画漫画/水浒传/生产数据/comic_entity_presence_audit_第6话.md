# 漫画实体在场契约机检 · 第6话

- 格 48 · registry 实体 43 · 显式排程格 0 · warn 1 · info 1

## Findings

- ⚠️ `mentioned_not_bound` P026 画面描述提到「高俅」（registry 实体 CHAR_GAO_QIU），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。
- ℹ️ `mentioned_not_bound` P045 台词/旁白提到「史太公」（registry 实体 CHAR_SHI_TAIGONG）但未绑定；若仅口头提及可忽略，若要入画需补 references。
