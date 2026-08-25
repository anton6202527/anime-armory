from text_renderer_adapter import suitability


def test_draft_renderer_cannot_claim_rtl_publication():
    result = suitability(language_mode="Arabic", direction="rtl", available={"adapter_id": "pillow_draft", "status": "draft_only", "supports": ["cjk_horizontal"]})
    assert result["suitable"] is False
    assert result["publication_claim_allowed"] is False
