"""
AI Marathon Coach - Plan Stats Tests
"""
import pytest
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plan_stats import (
    parse_distance_km,
    classify_day,
    aggregate_weekly_load,
    judge_shoe_cta_category,
    summarize_plan_stats,
)


class TestParseDistanceKm:
    """parse_distance_km関数のテスト"""

    def test_simple_km(self):
        assert parse_distance_km("12km") == 12.0

    def test_range_hyphen(self):
        assert parse_distance_km("10-12km") == 11.0

    def test_range_wave_dash(self):
        assert parse_distance_km("10〜12km") == 11.0

    def test_non_numeric(self):
        assert parse_distance_km("休養") is None

    def test_empty_string(self):
        assert parse_distance_km("") is None

    def test_none(self):
        assert parse_distance_km(None) is None

    def test_decimal(self):
        assert parse_distance_km("8.5km") == 8.5


class TestClassifyDay:
    """classify_day関数のテスト"""

    def test_rest_keyword_in_menu(self):
        assert classify_day("完全休養", "") == "rest"

    def test_rest_keyword_in_pace(self):
        assert classify_day("お休み", "-") == "rest"

    def test_pace_symbol_e(self):
        assert classify_day("なにかメニュー", "E 4:50〜5:00/km") == "E"

    def test_pace_symbol_r(self):
        assert classify_day("ポイント練習", "R 3:12/km（200m≒38秒）") == "R"

    def test_pace_symbol_priority_over_menu_keyword(self):
        # menuは閾値(T)を示唆するがpace記号がEなのでE優先
        assert classify_day("閾値走のつもりで軽め", "E 5:00/km") == "E"

    def test_rest_word_inside_workout_not_rest(self):
        # 練習内の回復（レストn分・レストnmジョグ）を休養日と誤判定しない（pace記号を最優先）
        assert classify_day("【ポイント②】T 2000m×3（レスト3分）", "T 3:48/km") == "T"
        assert classify_day("【ポイント①】I 1000m×5（レスト200mジョグ）", "I 3:30/km") == "I"
        assert classify_day("【ポイント①】R 400m×8（レスト400mジョグ）", "R 3:12/km（400m≒77秒）") == "R"

    def test_rest_word_alone_is_rest(self):
        # menu単独の「レスト」は休養日
        assert classify_day("レスト", "") == "rest"

    def test_pace_symbol_followed_by_digit(self):
        # 記号と数字が密着した表記（"T20分"）も記号として判定する
        assert classify_day("なにかメニュー", "T20分") == "T"

    def test_menu_keyword_fallback_interval(self):
        assert classify_day("インターバル走", "") == "I"

    def test_menu_keyword_fallback_threshold(self):
        assert classify_day("閾値走 20分連続", "") == "T"

    def test_menu_keyword_fallback_repetition(self):
        assert classify_day("【ポイント①】レペ 200m×10", "") == "R"

    def test_menu_keyword_fallback_marathon_pace(self):
        assert classify_day("Mペース走", "") == "M"

    def test_menu_keyword_fallback_easy(self):
        assert classify_day("Eジョグ（回復）", "") == "E"

    def test_menu_keyword_fallback_e_pace(self):
        # Gemini実出力で確認されたパターン（paceに記号なし・menuが「Eペース〜」）
        assert classify_day("Eペース走 + WS", "4:53〜4:19/km") == "E"

    def test_menu_keyword_fallback_long_run(self):
        assert classify_day("ロング走（有酸素）", "") == "E"

    def test_no_match_returns_other(self):
        assert classify_day("筋トレ", "") == "other"

    def test_none_inputs(self):
        assert classify_day(None, None) == "other"

    def test_empty_inputs(self):
        assert classify_day("", "") == "other"


class TestAggregateWeeklyLoad:
    """aggregate_weekly_load関数のテスト"""

    @pytest.fixture
    def sample_plan(self):
        """実サンプル形式に忠実なfixture"""
        return {
            "weekly_schedules": [
                {
                    "week": 1,
                    "dates": "07/14 - 07/20",
                    "total_distance": "42km",
                    "days": [
                        {"date": "07/14 (月)", "menu": "休養", "distance": "", "pace": "", "advice": ""},
                        {"date": "07/15 (火)", "menu": "Eジョグ（回復）", "distance": "10km", "pace": "E 4:50〜5:00/km", "advice": ""},
                        {"date": "07/16 (水)", "menu": "【ポイント①】R 200m×10", "distance": "8km", "pace": "R 3:12/km（200m≒38秒）", "advice": ""},
                        {"date": "07/17 (木)", "menu": "Eジョグ（回復）", "distance": "10km", "pace": "E 4:50〜5:00/km", "advice": ""},
                        {"date": "07/18 (金)", "menu": "閾値走 T 20分連続", "distance": "10km", "pace": "T 4:00/km", "advice": ""},
                        {"date": "07/19 (土)", "menu": "E＋流し", "distance": "8km", "pace": "E 4:50/km", "advice": ""},
                        {"date": "07/20 (日)", "menu": "ロング走（有酸素）", "distance": "12km", "pace": "E 5:00/km", "advice": ""},
                    ],
                },
            ]
        }

    def test_full_week_aggregation(self, sample_plan):
        result = aggregate_weekly_load(sample_plan)
        assert len(result) == 1
        week = result[0]
        assert week["week"] == 1
        # total_distanceのパース優先（42km）
        assert week["total_km"] == 42.0
        assert week["breakdown"]["E"] == pytest.approx(10 + 10 + 8 + 12)
        assert week["breakdown"]["R"] == pytest.approx(8)
        assert week["breakdown"]["T"] == pytest.approx(10)
        # rest日はカウントしない
        assert week["point_sessions"] == 2  # R + T

    def test_fallback_to_days_sum_when_total_distance_missing(self):
        plan = {
            "weekly_schedules": [
                {
                    "week": 1,
                    "days": [
                        {"date": "d1", "menu": "Eジョグ", "distance": "10km", "pace": "E 5:00/km"},
                        {"date": "d2", "menu": "Eジョグ", "distance": "10km", "pace": "E 5:00/km"},
                    ],
                }
            ]
        }
        result = aggregate_weekly_load(plan)
        assert result[0]["total_km"] == pytest.approx(20.0)

    def test_range_distance(self):
        plan = {
            "weekly_schedules": [
                {
                    "week": 1,
                    "total_distance": "",
                    "days": [
                        {"date": "d1", "menu": "Eジョグ", "distance": "10-12km", "pace": "E 5:00/km"},
                    ],
                }
            ]
        }
        result = aggregate_weekly_load(plan)
        assert result[0]["breakdown"]["E"] == pytest.approx(11.0)

    def test_non_numeric_distance_skipped(self):
        plan = {
            "weekly_schedules": [
                {
                    "week": 1,
                    "total_distance": "",
                    "days": [
                        {"date": "d1", "menu": "休養", "distance": "休養", "pace": ""},
                        {"date": "d2", "menu": "Eジョグ", "distance": "10km", "pace": "E 5:00/km"},
                    ],
                }
            ]
        }
        result = aggregate_weekly_load(plan)
        assert result[0]["total_km"] == pytest.approx(10.0)

    def test_empty_distance_string(self):
        plan = {
            "weekly_schedules": [
                {
                    "week": 1,
                    "total_distance": "",
                    "days": [
                        {"date": "d1", "menu": "Eジョグ", "distance": "", "pace": "E 5:00/km"},
                    ],
                }
            ]
        }
        result = aggregate_weekly_load(plan)
        assert result[0]["total_km"] == 0.0
        assert result[0]["point_sessions"] == 0

    def test_missing_keys_in_day(self):
        plan = {
            "weekly_schedules": [
                {
                    "week": 1,
                    "total_distance": "10km",
                    "days": [
                        {"date": "d1"},  # menu/distance/pace欠落
                    ],
                }
            ]
        }
        result = aggregate_weekly_load(plan)
        assert result[0]["total_km"] == 10.0
        assert result[0]["breakdown"]["other"] == 0.0

    def test_rest_day_excluded_from_breakdown(self):
        plan = {
            "weekly_schedules": [
                {
                    "week": 1,
                    "total_distance": "",
                    "days": [
                        {"date": "d1", "menu": "休養", "distance": "5km", "pace": ""},
                    ],
                }
            ]
        }
        result = aggregate_weekly_load(plan)
        assert result[0]["total_km"] == 0.0
        assert sum(result[0]["breakdown"].values()) == 0.0

    def test_empty_weekly_schedules(self):
        assert aggregate_weekly_load({"weekly_schedules": []}) == []

    def test_missing_weekly_schedules_key(self):
        assert aggregate_weekly_load({}) == []

    def test_non_dict_plan(self):
        assert aggregate_weekly_load(None) == []
        assert aggregate_weekly_load("not a dict") == []


class TestJudgeShoeCtaCategory:
    """judge_shoe_cta_category関数のテスト"""

    def test_point_heavy_boundary_exactly_two(self):
        weekly_load = [
            {"week": 1, "point_sessions": 2},
            {"week": 2, "point_sessions": 2},
        ]
        assert judge_shoe_cta_category(weekly_load) == "point_heavy"

    def test_point_heavy_above_two(self):
        weekly_load = [{"week": 1, "point_sessions": 3}]
        assert judge_shoe_cta_category(weekly_load) == "point_heavy"

    def test_balanced(self):
        weekly_load = [
            {"week": 1, "point_sessions": 1},
            {"week": 2, "point_sessions": 1},
        ]
        assert judge_shoe_cta_category(weekly_load) == "balanced"

    def test_easy_focus(self):
        weekly_load = [
            {"week": 1, "point_sessions": 0},
            {"week": 2, "point_sessions": 0},
        ]
        assert judge_shoe_cta_category(weekly_load) == "easy_focus"

    def test_empty_list(self):
        assert judge_shoe_cta_category([]) == "general"


class TestSummarizePlanStats:
    """summarize_plan_stats関数のテスト"""

    def test_valid_plan(self):
        plan = {
            "weekly_schedules": [
                {
                    "week": 1,
                    "total_distance": "20km",
                    "days": [
                        {"date": "d1", "menu": "Eジョグ", "distance": "10km", "pace": "E 5:00/km"},
                        {"date": "d2", "menu": "閾値走", "distance": "10km", "pace": "T 4:00/km"},
                    ],
                }
            ]
        }
        stats = summarize_plan_stats(plan)
        assert stats is not None
        assert stats["cta_category"] in ("point_heavy", "balanced", "easy_focus")
        assert stats["avg_weekly_km"] == pytest.approx(20.0)
        assert len(stats["weekly_load"]) == 1

    def test_none_input(self):
        assert summarize_plan_stats(None) is None

    def test_empty_dict(self):
        assert summarize_plan_stats({}) is None

    def test_missing_weekly_schedules(self):
        assert summarize_plan_stats({"introduction": "test"}) is None

    def test_non_dict_input(self):
        assert summarize_plan_stats("not a dict") is None
        assert summarize_plan_stats([1, 2, 3]) is None
