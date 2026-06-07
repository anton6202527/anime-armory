#!/usr/bin/env python3
# MiniMax 声音复刻：上传参考音频 → voice_clone → 输出自定义 voice_id
# 用法: source .minimax_env && VOICE_CLONE_AUTHORIZED=1 python3 voice_clone.py <参考音频路径> <自定义voiceID>
#   自定义voiceID 规则：字母开头、≥8位、字母数字（如 shennian_yujie01）
#
# ⚠️ 合规闸门（CLAUDE.md：声音克隆 non-negotiable，每次确认）：
#   参考音频必须是 ①本人嗓 / ②已获明确授权的他人嗓 / ③纯合成音色 之一。
#   复刻真人歌手/演员/公众人物声音需本人书面授权（2026 opt-in）。未授权复刻属违规。
#   必须显式声明 VOICE_CLONE_AUTHORIZED=1 才放行——这一步刻意每次重确认，不做静默默认。
import sys, os, json, subprocess, urllib.request

ref, vid = sys.argv[1], sys.argv[2]
if os.environ.get('VOICE_CLONE_AUTHORIZED') != '1':
    print('⛔ 声音克隆合规闸门未通过。')
    print(f'   参考音频：{ref}')
    print('   仅限 本人嗓 / 已授权他人嗓 / 纯合成音色；复刻真人声音需本人授权（2026 opt-in）。')
    print('   确认来源合规后，显式声明授权再跑：')
    print(f'     VOICE_CLONE_AUTHORIZED=1 python3 voice_clone.py {ref} {vid}')
    sys.exit(3)
if not os.path.isfile(ref):
    print(f'⛔ 参考音频不存在：{ref}'); sys.exit(2)
print(f'✅ 已声明授权（VOICE_CLONE_AUTHORIZED=1）；参考音频={ref}')
KEY = os.environ['MINIMAX_API_KEY']; GROUP = os.environ['MINIMAX_GROUP_ID']
BASE = os.environ.get('MINIMAX_BASE', 'https://api.minimaxi.com/v1')

# 1) 上传文件（multipart，用 curl 最稳）
up = subprocess.run(['curl','-s','-X','POST',
    f'{BASE}/files/upload?GroupId={GROUP}',
    '-H', f'Authorization: Bearer {KEY}',
    '-F', 'purpose=voice_clone',
    '-F', f'file=@{ref}'], capture_output=True, text=True)
j = json.loads(up.stdout)
fid = (j.get('file') or {}).get('file_id')
if not fid:
    print('上传失败:', up.stdout[:500]); sys.exit(1)
print('file_id =', fid)

# 2) 复刻
body = {"file_id": fid, "voice_id": vid, "need_noise_reduction": True, "need_volume_normalization": True}
req = urllib.request.Request(f'{BASE}/voice_clone?GroupId={GROUP}',
    data=json.dumps(body).encode(), headers={'Authorization': f'Bearer {KEY}','Content-Type':'application/json'})
with urllib.request.urlopen(req, timeout=120) as r:
    cj = json.loads(r.read().decode())
st = (cj.get('base_resp') or {}).get('status_code', -1)
if st != 0:
    print('复刻失败:', cj); sys.exit(1)
print('✅ 复刻成功 voice_id =', vid)
print('   把它填进 .minimax_env:  export MM_SHEN=' + vid)
