#!/usr/bin/env python3
from image_backend_adapter import resolve_capabilities


def test_dreamina_official_cli_exposes_verified_ten_image_budget() -> None:
    caps = resolve_capabilities("Dreamina 5.0", "Dreamina/即梦官方 CLI")
    assert caps.adapter_id == "dreamina_image2image"
    assert caps.reference_image_limit == 10
    assert caps.single_character_reference_limit == 5
    assert caps.multi_character_reference_limit == 4
    assert caps.non_character_reference_limit == 2
    assert caps.style_reference_limit == 1
