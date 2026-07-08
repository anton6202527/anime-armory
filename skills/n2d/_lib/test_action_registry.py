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
    assert "episode_promise_gate" in spec["prework_steps"]
    assert "director_blocking_pack" in spec["prework_steps"]


def test_script_stage1_declares_source_comprehension_prework():
    spec = reg.stage_action_spec("script_stage1")
    assert "source_comprehension_gate" in spec["prework_steps"]


def test_image_prompt_declares_production_breakdown_prework():
    spec = reg.stage_action_spec("image_prompt")
    assert "story_economy_audit" in spec["prework_steps"]
    assert "shot_intent_gate" in spec["prework_steps"]
    assert "production_breakdown" in spec["prework_steps"]


def test_paid_image_declares_production_breakdown_prework_for_legacy_projects():
    spec = reg.stage_action_spec("image")
    assert "production_breakdown" in spec["prework_steps"]
    assert "reference_slot_gate" in spec["prework_steps"]


def test_video_and_compose_declare_preventive_contract_gates():
    video_prompt = reg.stage_action_spec("video_prompt")
    video = reg.stage_action_spec("video")
    compose = reg.stage_action_spec("compose")
    assert "interaction_physics_gate" in video_prompt["prework_steps"]
    assert "audio_timing_gate" in video_prompt["prework_steps"]
    assert "interaction_physics_gate" in video["prework_steps"]
    assert "audio_timing_gate" in video["prework_steps"]
    assert "audio_timing_gate" in compose["prework_steps"]


def test_review_declares_episode_closeout_prework():
    spec = reg.stage_action_spec("review")
    for step in ("progress_dag", "production_breakdown", "failure_taxonomy", "pilot_release_gate", "release_verdict"):
        assert step in spec["prework_steps"]


def test_pack_paths_are_stable_and_safe():
    assert reg.context_pack_relpath("第1集", "image_prompt").endswith("context_pack_第1集_image_prompt.json")
    assert reg.creative_loop_relpath("第1集", "video_prompt").endswith("creative_loop_第1集_video_prompt.json")
