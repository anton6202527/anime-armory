import os
import glob
import re
from datetime import datetime

def count_lines(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except:
        return 0

def get_stats():
    series = ['n2d', 'novel', 'song', 'mv', 'ad']
    stats = {s: {'skills': 0, 'skill_md_lines': 0, 'total_lines': 0} for s in series}
    
    for s in series:
        # Match 'series' and 'series-*'
        skill_dirs = [d for d in os.listdir('skills') if os.path.isdir(os.path.join('skills', d)) and (d == s or d.startswith(s + '-'))]
        stats[s]['skills'] = len(skill_dirs)
        
        for sd in skill_dirs:
            skill_path = os.path.join('skills', sd)
            skill_md = os.path.join(skill_path, 'SKILL.md')
            if os.path.isfile(skill_md):
                stats[s]['skill_md_lines'] += count_lines(skill_md)
                
            # Count text files in the skill directory
            for ext in ['.md', '.py', '.sh', '.json', '.html']:
                for filepath in glob.glob(os.path.join(skill_path, '**', f'*{ext}'), recursive=True):
                    # Exclude __pycache__
                    if '__pycache__' not in filepath:
                        stats[s]['total_lines'] += count_lines(filepath)
                        
    return stats

def update_readme(stats):
    with open('skills/README.md', 'r', encoding='utf-8') as f:
        content = f.read()
        
    today = datetime.now().strftime('%Y-%m-%d')
    
    total_skills = sum(s['skills'] for s in stats.values())
    total_md_lines = sum(s['skill_md_lines'] for s in stats.values())
    total_text_lines = sum(s['total_lines'] for s in stats.values())
    
    # Update date
    content = re.sub(r'> 统计时间：\d{4}-\d{2}-\d{2}。', f'> 统计时间：{today}。', content)
    
    # Update table rows
    for s in ['n2d', 'novel', 'song', 'mv', 'ad']:
        pattern = r'\| ' + s + r' \| `(?:' + s + r')` \+ `(?:' + s + r')-\*` \| \d+ \| \d+ \| \d+ \|'
        replacement = f"| {s} | `{s}` + `{s}-*` | {stats[s]['skills']} | {stats[s]['skill_md_lines']} | {stats[s]['total_lines']} |"
        content = re.sub(pattern, replacement, content)
        
    # Update total row
    pattern = r'\| \*\*合计\*\* \| `skills/\*/SKILL\.md` \| \*\*\d+\*\* \| \d+ \| \d+ \|'
    replacement = f"| **合计** | `skills/*/SKILL.md` | **{total_skills}** | {total_md_lines} | {total_text_lines} |"
    content = re.sub(pattern, replacement, content)
    
    with open('skills/README.md', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    stats = get_stats()
    print("New Stats:", stats)
    update_readme(stats)
    print("Updated README.md")
