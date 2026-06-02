#!/usr/bin/env python3
# MiniMax 声音复刻：上传参考音频 → voice_clone → 输出自定义 voice_id
# 用法: source .minimax_env && python3 _voice_clone.py <参考音频路径> <自定义voiceID>
#   自定义voiceID 规则：字母开头、≥8位、字母数字（如 shennian_yujie01）
import sys, os, json, subprocess, urllib.request

ref, vid = sys.argv[1], sys.argv[2]
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
