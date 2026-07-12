"""panel_variety 单测。运行：cd skills/comic-review/scripts && python -m pytest test_panel_variety.py"""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).with_name("panel_variety.py")
spec = importlib.util.spec_from_file_location("comic_panel_variety", SCRIPT)
pv = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(pv)


def _img(path, kind):
    from PIL import Image
    if kind == "solid":
        img = Image.new("RGB", (64, 64), (100, 100, 100))
    else:
        # 棋盘纹理：相邻列亮度交替 → dHash 位串 1010…，与纯色（全 0）显著不同
        img = Image.new("L", (64, 64))
        for x in range(64):
            for y in range(64):
                img.putpixel((x, y), 255 if (x // 4 + y // 4) % 2 else 0)
        img = img.convert("RGB")
    img.save(path)


def test_non_adjacent_duplicates_flagged(tmp_path):
    d = tmp_path / "出图" / "第1话" / "panels"
    d.mkdir(parents=True)
    _img(d / "P001.png", "solid")
    _img(d / "P005.png", "solid")   # 非相邻同图 → warn
    _img(d / "P003.png", "grad")
    report = pv.build_report(tmp_path, "第1话")
    pairs = report["duplicate_pairs"]
    assert len(pairs) == 1 and pairs[0]["panels"] == ["P001", "P005"]
    assert report["findings"][0]["code"] == "near_duplicate_panels"


def test_adjacent_micro_diff_exempt(tmp_path):
    d = tmp_path / "出图" / "第1话" / "panels"
    d.mkdir(parents=True)
    _img(d / "P001.png", "solid")
    _img(d / "P002.png", "solid")   # 相邻且 d=0 ≤ ADJACENT_OK → 豁免
    report = pv.build_report(tmp_path, "第1话")
    assert report["duplicate_pairs"] == []


def test_missing_dir_graceful(tmp_path):
    report = pv.build_report(tmp_path, "第1话")
    assert report["summary"]["panels"] == 0 and report["findings"] == []
