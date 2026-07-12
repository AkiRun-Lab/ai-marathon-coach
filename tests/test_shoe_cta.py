"""
AI Marathon Coach - Shoe CTA Tests
計画連動シューズ提案CTAの表示内容組み立て（build_shoe_cta_content）のテスト
"""
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import SHOE_CTA_VARIANTS
from src.ui.components import build_shoe_cta_content


def _make_stats(cta_category="general", avg_weekly_km=55.4, avg_point_sessions=1.5):
    return {
        "weekly_load": [{"week": 1, "total_km": avg_weekly_km, "breakdown": {}, "point_sessions": 2}],
        "cta_category": cta_category,
        "avg_weekly_km": avg_weekly_km,
        "avg_point_sessions": avg_point_sessions,
    }


class TestBuildShoeCtaContentCategories:
    """各カテゴリでvariantが正しく選ばれ、プレースホルダが埋まること"""

    def test_point_heavy(self):
        stats = _make_stats(cta_category="point_heavy", avg_weekly_km=80, avg_point_sessions=2.5)
        content = build_shoe_cta_content(stats)
        assert content is not None
        assert content["title"] == SHOE_CTA_VARIANTS["point_heavy"]["title"].format(sessions="2.5", km="80")
        assert "{sessions}" not in content["title"]
        assert "{sessions}" not in content["sub"]
        assert "{km}" not in content["sub"]
        assert content["url"] == SHOE_CTA_VARIANTS["point_heavy"]["url"]

    def test_balanced(self):
        stats = _make_stats(cta_category="balanced", avg_weekly_km=60, avg_point_sessions=1.0)
        content = build_shoe_cta_content(stats)
        assert content is not None
        assert content["title"] == SHOE_CTA_VARIANTS["balanced"]["title"]
        assert "{sessions}" not in content["sub"]
        assert "{km}" not in content["sub"]

    def test_easy_focus(self):
        stats = _make_stats(cta_category="easy_focus", avg_weekly_km=45, avg_point_sessions=0.3)
        content = build_shoe_cta_content(stats)
        assert content is not None
        assert content["title"] == SHOE_CTA_VARIANTS["easy_focus"]["title"]
        assert "{km}" not in content["sub"]

    def test_general(self):
        stats = _make_stats(cta_category="general", avg_weekly_km=50, avg_point_sessions=0)
        content = build_shoe_cta_content(stats)
        assert content is not None
        assert content["title"] == SHOE_CTA_VARIANTS["general"]["title"]
        assert content["sub"] == SHOE_CTA_VARIANTS["general"]["sub"]


class TestNumberFormatting:
    """sessionsは小数1桁（末尾.0は落とす）、kmは四捨五入の整数文字列"""

    def test_sessions_integer_value_drops_trailing_zero(self):
        stats = _make_stats(cta_category="point_heavy", avg_weekly_km=80, avg_point_sessions=2.0)
        content = build_shoe_cta_content(stats)
        assert "週平均2回" in content["data_line"]
        assert "2.0" not in content["data_line"]

    def test_sessions_decimal_kept(self):
        stats = _make_stats(cta_category="point_heavy", avg_weekly_km=80, avg_point_sessions=2.5)
        content = build_shoe_cta_content(stats)
        assert "週平均2.5回" in content["data_line"]

    def test_km_rounds_up(self):
        stats = _make_stats(cta_category="balanced", avg_weekly_km=55.6, avg_point_sessions=1.2)
        content = build_shoe_cta_content(stats)
        assert "平均56km" in content["data_line"]

    def test_km_rounds_down(self):
        stats = _make_stats(cta_category="balanced", avg_weekly_km=55.4, avg_point_sessions=1.2)
        content = build_shoe_cta_content(stats)
        assert "平均55km" in content["data_line"]

    def test_data_line_format(self):
        stats = _make_stats(cta_category="balanced", avg_weekly_km=60, avg_point_sessions=1.2)
        content = build_shoe_cta_content(stats)
        assert content["data_line"] == "ポイント練習 週平均1.2回 ・ 週間走行距離 平均60km"


class TestInvalidInput:
    """None・空dict・キー欠落はNoneを返す（例外を投げない）"""

    def test_none(self):
        assert build_shoe_cta_content(None) is None

    def test_empty_dict(self):
        assert build_shoe_cta_content({}) is None

    def test_missing_key(self):
        stats = _make_stats()
        del stats["avg_weekly_km"]
        assert build_shoe_cta_content(stats) is None

    def test_not_a_dict(self):
        assert build_shoe_cta_content("not a dict") is None
        assert build_shoe_cta_content([]) is None

    def test_non_numeric_values(self):
        stats = _make_stats()
        stats["avg_weekly_km"] = "invalid"
        assert build_shoe_cta_content(stats) is None


class TestUnknownCategoryFallback:
    """未知カテゴリはgeneralにフォールバックする"""

    def test_unknown_category(self):
        stats = _make_stats(cta_category="unknown_category_xyz", avg_weekly_km=50, avg_point_sessions=1.0)
        content = build_shoe_cta_content(stats)
        assert content is not None
        assert content["title"] == SHOE_CTA_VARIANTS["general"]["title"]


class TestAllVariantsHaveUrl:
    """全variantのurlが空でないこと"""

    def test_all_urls_non_empty(self):
        for category, variant in SHOE_CTA_VARIANTS.items():
            assert variant["url"], f"{category} のurlが空です"
