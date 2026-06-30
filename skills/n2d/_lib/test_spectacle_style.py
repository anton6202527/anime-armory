"""Style-adaptive combat-spectacle profile tests.

cd skills/n2d/_lib && python -m pytest test_spectacle_style.py

P0-1：打斗镜「经费在燃烧」四层注入按风格族分流，避免给赛璐璐/水墨/Q版剧
硬塞写实体积光与 motion blur（和 global_style/风格禁忌 打架·糊成四不像）。
"""
import importlib.util
import sys
from pathlib import Path


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


const = _load("n2d_const")


def test_family_classification():
    fam = const.spectacle_style_family
    # cinematic 默认（含本就含写实体积光/大气纵深的风格）
    assert fam("") == "cinematic"
    assert fam("冷灰写实3D国风漫剧") == "cinematic"
    assert fam("写实电影感") == "cinematic"
    assert fam("厚涂幻想") == "cinematic"
    assert fam("日漫剧场版光影") == "cinematic"
    assert fam("暗黑悬疑写实") == "cinematic"
    # cel：赛璐璐/二次元/条漫/韩漫/乙女
    assert fam("二次元赛璐璐") == "cel"
    assert fam("动态漫画条漫风") == "cel"
    assert fam("韩漫精致清透") == "cel"
    assert fam("古风乙女清雅") == "cel"
    # ink：水墨
    assert fam("水墨国风") == "ink"
    # flat：Q版/剪影/定格/低多边形/玩具
    assert fam("Q版轻喜") == "flat"
    assert fam("纸片剪影 / 定格动画") == "flat"
    assert fam("低多边形玩具感") == "flat"


def test_precedence_ink_before_cel():
    # 含「水墨」即归 ink，即使句中还混了其它词
    assert const.spectacle_style_family("水墨国风，风格禁忌：赛璐璐平涂") == "ink"


def test_guidance_matches_family_and_avoids_realist_terms_for_nonrealist():
    g = const.combat_spectacle_guidance_for_style
    # cinematic 走原写实四层（向后兼容：含「经费在燃烧」「体积光」「motion blur」）
    cine = g("写实电影感")
    assert cine == const.COMBAT_SPECTACLE_RICHNESS_GUIDANCE
    assert "经费在燃烧" in cine and "体积光" in cine and "motion blur" in cine
    # cel：换赛璐璐速度线·硬边卡通光束，明确不混写实 motion blur 长拖影/景深虚焦
    cel = g("二次元赛璐璐")
    assert "赛璐璐" in cel and "速度线" in cel
    assert "非写实长拖影 motion blur" in cel
    assert "胶片颗粒" in cel  # 以否定形式出现：不混入写实胶片颗粒
    # ink：飞白泼墨气劲·留白纵深，不用写实体积光/景深
    ink = g("水墨国风")
    assert "飞白" in ink and "留白" in ink
    assert "不用写实体积光" in ink
    # flat：夸张图形化冲击·克制堆料，绝不注入写实电影摄影语言
    flat = g("Q版轻喜")
    assert "夸张" in flat and "星芒" in flat
    assert "绝不注入写实电影摄影语言" in flat


def test_nonrealist_profiles_drop_bare_volumetric_motion_blur_demand():
    # cel/ink/flat 三个变体都不得「正向要求」写实体积光雾化 + motion blur 长拖影
    # （只能以否定/替代形式出现）。用 cinematic 的正向措辞做反例对照。
    for style in ("二次元赛璐璐", "水墨国风", "Q版轻喜"):
        g = const.combat_spectacle_guidance_for_style(style)
        assert "丁达尔光束穿过烟尘" not in g
        assert "顺攻击方向给速度线 + 拖影 motion blur" not in g
    cine = const.combat_spectacle_guidance_for_style("写实电影感")
    assert "丁达尔" in cine
    assert "拖影 motion blur" in cine


def test_all_profiles_keep_face_and_anchor_guardrails():
    # 不论风格族，四层注入都必须保留「不糊脸/不盖受力点 + 遵守光位锚与风格禁忌」红线。
    for style in ("", "二次元赛璐璐", "水墨国风", "Q版轻喜"):
        g = const.combat_spectacle_guidance_for_style(style)
        assert "绝不糊脸或盖过受力点" in g
        assert "光位锚" in g and "风格禁忌" in g
