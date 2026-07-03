import n2d_action_registry as reg


def test_registry_validates_supervisor_boundaries():
    assert reg.validate_action_registry() == []
    image = reg.stage_action_spec("image")
    assert image["paid_or_irreversible"] is True
    assert image["requires_human_approval"] is True
    assert image["supervisor_contract"]["may_execute_paid_work"] is False


def test_creative_stage_declares_loop_and_specialist():
    spec = reg.stage_action_spec("video_prompt")
    assert spec["requires_creative_loop"] is True
    specialist = reg.specialist_for_stage("video_prompt")
    assert specialist["name"] == "n2d-visual-agent"
    assert "video_prompt" in specialist["allowed_stage_keys"]


def test_script_stage2_declares_director_blocking_prework():
    spec = reg.stage_action_spec("script_stage2")
    assert "director_blocking_pack" in spec["prework_steps"]


def test_image_prompt_declares_production_breakdown_prework():
    spec = reg.stage_action_spec("image_prompt")
    assert "production_breakdown" in spec["prework_steps"]


def test_paid_image_declares_production_breakdown_prework_for_legacy_projects():
    spec = reg.stage_action_spec("image")
    assert "production_breakdown" in spec["prework_steps"]


def test_review_declares_episode_closeout_prework():
    spec = reg.stage_action_spec("review")
    for step in ("progress_dag", "production_breakdown", "failure_taxonomy", "release_verdict"):
        assert step in spec["prework_steps"]


def test_pack_paths_are_stable_and_safe():
    assert reg.context_pack_relpath("第1集", "image_prompt").endswith("context_pack_第1集_image_prompt.json")
    assert reg.creative_loop_relpath("第1集", "video_prompt").endswith("creative_loop_第1集_video_prompt.json")
