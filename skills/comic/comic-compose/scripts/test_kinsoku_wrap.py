from PIL import Image, ImageDraw, ImageFont
import export_longstrip as export


def test_cjk_wrap_does_not_start_with_closing_punctuation():
    draw = ImageDraw.Draw(Image.new("RGB", (200, 100)))
    font = ImageFont.load_default()
    width = export.text_size(draw, "你好", font)[0]
    lines = export.wrap_text(draw, "你好，世界", font, width)
    assert all(not line.startswith("，") for line in lines)
