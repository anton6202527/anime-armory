# Codex project helpers

This directory mirrors the project-level helper layout used by other agents.

- `skills -> ../skills`: shared project skills; do not duplicate them here.
- `创作偏好-默认.md`: default creative preferences for this project.

Codex already reads the repository `AGENTS.md` as project instructions. The
`skills` symlink is provided so tools or humans expecting a `.codex/skills`
entry can find the same skill set.
