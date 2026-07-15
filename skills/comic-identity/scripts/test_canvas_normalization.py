import importlib.util
from pathlib import Path

from PIL import Image


P = Path(__file__).with_name("identity.py")
S = importlib.util.spec_from_file_location("identity_canvas_test", P)
M = importlib.util.module_from_spec(S); S.loader.exec_module(M)


def test_normalize_full_body_canvas_is_exact_and_non_cropping(tmp_path):
    path = tmp_path / "view.png"
    image = Image.new("RGB", (500, 1000), (230, 230, 225))
    for x in range(150, 350):
        for y in range(100, 900):
            image.putpixel((x, y), (80, 20, 20))
    image.save(path)
    assert M.normalize_full_body_canvas(path, (600, 800))
    out = Image.open(path)
    assert out.size == (600, 800)
    # Entire colored subject survives proportional containment.
    red = sum(1 for pixel in out.get_flattened_data() if pixel[0] > 60 and pixel[1] < 40)
    assert red > 0
    assert not M.normalize_full_body_canvas(path, (600, 800))
