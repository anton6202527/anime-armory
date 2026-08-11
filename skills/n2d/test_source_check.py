import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("n2d_source_check", HERE / "source_check.py")
assert SPEC and SPEC.loader
source_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(source_check)


def test_hui_hashes_win_over_volume_wrapper(tmp_path):
    source = tmp_path / "classic.txt"
    source.write_text(
        "第1章 卷之一\n"
        "[编辑]第一囬 景陽岡武松打虎\n正文一。\n"
        "第二囘 西門慶簾下遇金蓮\n正文二。\n"
        "第三廻 王婆定十件挨光計\n正文三。\n",
        encoding="utf-8",
    )

    hashes = source_check.hashes_from_txt(source)

    assert sorted(hashes) == [1, 2, 3]
    assert len(set(hashes.values())) == 3


def test_plain_chapter_source_remains_backward_compatible(tmp_path):
    source = tmp_path / "modern.txt"
    source.write_text("第1章 起\n正文一。\n第2章 承\n正文二。\n", encoding="utf-8")

    assert sorted(source_check.hashes_from_txt(source)) == [1, 2]
