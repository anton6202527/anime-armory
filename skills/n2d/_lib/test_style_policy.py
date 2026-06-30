import style_policy as sp


def test_styleid_model_status_accepts_official_hf_id():
    status = sp.styleid_model_status({"N2D_STYLEID_MODEL": "kwanY/styleid"})

    assert status["status"] == "ready"
    assert status["source"] == "huggingface"
    assert status["model_id"] == "kwanY/styleid"


def test_styleid_model_status_rejects_remote_when_download_disabled():
    status = sp.styleid_model_status({
        "N2D_STYLEID_MODEL": "kwanY/styleid",
        "N2D_ALLOW_MODEL_DOWNLOAD": "0",
    })

    assert status["status"] == "download_disabled"


def test_styleid_model_status_does_not_accept_unapproved_remote_id():
    status = sp.styleid_model_status({"N2D_STYLEID_MODEL": "someone/other-styleid"})

    assert status["status"] == "unapproved_remote"
