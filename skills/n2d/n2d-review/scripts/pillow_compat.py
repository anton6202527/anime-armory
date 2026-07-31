"""Small Pillow compatibility helpers used by n2d-review pixel detectors."""
from __future__ import annotations

from typing import Any


def pixel_data(image: Any) -> Any:
    """Return Pillow's pixel sequence on both sides of the Pillow 12 rename.

    ``Image.getdata()`` is deprecated in Pillow 12 and removed in Pillow 14;
    ``get_flattened_data()`` has the same iteration semantics.  Older Pillow
    releases do not expose the new method, so retain the legacy fallback.
    """
    getter = getattr(image, "get_flattened_data", None)
    if callable(getter):
        return getter()
    return image.getdata()
