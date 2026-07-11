import importlib.util
import json
import sys
from pathlib import Path


def _module():
    path = Path(__file__).with_name("gen_bgm.py")
    spec = importlib.util.spec_from_file_location("n2d_gen_bgm_under_test", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_register_existing_writes_hash_receipt(tmp_path):
    mod = _module()
    contract_path = tmp_path / "合成" / "第1集" / "bgm_contract.json"
    contract_path.parent.mkdir(parents=True)
    audio = tmp_path / "素材" / "bgm.wav"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"RIFF-generated-audio")
    contract_path.write_text(json.dumps({
        "kind": "n2d_bgm_contract", "version": 1, "episode": "第1集", "status": "confirmed",
        "strategy": "generated", "source": {"file": "素材/bgm.wav", "model": "MusicModel 1", "channel": "manual"},
        "cues": [{"intent": "压迫"}], "mix": {},
    }, ensure_ascii=False), encoding="utf-8")
    assert mod.main([str(tmp_path), "第1集", "--register-existing", "--json"]) == 0
    receipt = json.loads(contract_path.with_name("bgm_generation_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "pass" and receipt["output_sha256"]
    assert mod.core.validate(tmp_path, "第1集") == []
