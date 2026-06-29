import os
import glob

def get_stats(prefix):
    dirs = glob.glob(f"skills/{prefix}") + glob.glob(f"skills/{prefix}-*")
    count = len([d for d in dirs if os.path.exists(os.path.join(d, "SKILL.md"))])
    
    skill_lines = 0
    text_lines = 0
    for d in dirs:
        skill_path = os.path.join(d, "SKILL.md")
        if os.path.exists(skill_path):
            with open(skill_path, "r", encoding="utf-8") as f:
                skill_lines += len(f.readlines())
        
        for root, _, files in os.walk(d):
            if "__pycache__" in root: continue
            for file in files:
                if file.endswith((".md", ".py", ".sh", ".json", ".html")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            text_lines += len(f.readlines())
                    except:
                        pass
    return count, skill_lines, text_lines

total_count = 0
total_skill = 0
total_text = 0

for prefix in ["n2d", "novel", "song", "mv", "ad"]:
    c, s, t = get_stats(prefix)
    total_count += c
    total_skill += s
    total_text += t
    print(f"| {prefix} | `{prefix}` + `{prefix}-*` | {c} | {s} | {t} |")

print(f"| **合计** | `skills/*/SKILL.md` | **{total_count}** | {total_skill} | {total_text} |")
