import warnings

import pillow_compat as compat


def test_pixel_data_prefers_new_pillow_api():
    class NewImage:
        def get_flattened_data(self):
            return [(1, 2, 3)]

        def getdata(self):
            raise AssertionError("deprecated API must not be used when the new API exists")

    assert list(compat.pixel_data(NewImage())) == [(1, 2, 3)]


def test_pixel_data_falls_back_for_old_pillow():
    class OldImage:
        def getdata(self):
            return [7, 8]

    assert list(compat.pixel_data(OldImage())) == [7, 8]


def test_pixel_data_current_pillow_emits_no_deprecation_warning():
    from PIL import Image

    image = Image.new("RGB", (1, 1), (1, 2, 3))
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert list(compat.pixel_data(image)) == [(1, 2, 3)]
