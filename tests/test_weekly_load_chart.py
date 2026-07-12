"""
AI Marathon Coach - Weekly Load Chart Tests
週間負荷グラフ用データ組み立て（build_weekly_load_df）のテスト
"""
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.components import build_weekly_load_df, _LOAD_CHART_TYPES


_LABELS = {key: label for key, label, _color in _LOAD_CHART_TYPES}
_ORDER_INDEX = {key: idx for idx, (key, _label, _color) in enumerate(_LOAD_CHART_TYPES)}


def _make_stats(weekly_load):
    return {
        "weekly_load": weekly_load,
        "cta_category": "balanced",
        "avg_weekly_km": 50.0,
        "avg_point_sessions": 1.5,
    }


class TestBuildWeeklyLoadDfShape:
    """2週分の実データ形式statsで行数・週・ラベル変換・距離値・順序列を検証"""

    def _sample_weekly_load(self):
        return [
            {
                "week": 1,
                "total_km": 40.0,
                "breakdown": {"E": 25.0, "M": 0.0, "T": 5.0, "I": 0.0, "R": 0.0, "other": 10.0},
                "point_sessions": 1,
            },
            {
                "week": 2,
                "total_km": 55.0,
                "breakdown": {"E": 30.0, "M": 10.0, "T": 0.0, "I": 15.0, "R": 0.0, "other": 0.0},
                "point_sessions": 2,
            },
        ]

    def test_zero_breakdown_rows_are_dropped(self):
        df = build_weekly_load_df(_make_stats(self._sample_weekly_load()))
        assert df is not None
        # week1: E,T,other(3件) / week2: E,M,I(3件) = 計6行（0の種別は落ちる）
        assert len(df) == 6

    def test_weeks_present(self):
        df = build_weekly_load_df(_make_stats(self._sample_weekly_load()))
        assert set(df["週"]) == {1, 2}

    def test_label_conversion(self):
        df = build_weekly_load_df(_make_stats(self._sample_weekly_load()))
        week1_types = set(df[df["週"] == 1]["種別"])
        assert week1_types == {_LABELS["E"], _LABELS["T"], _LABELS["other"]}

        week2_types = set(df[df["週"] == 2]["種別"])
        assert week2_types == {_LABELS["E"], _LABELS["M"], _LABELS["I"]}

    def test_distance_values(self):
        df = build_weekly_load_df(_make_stats(self._sample_weekly_load()))
        row = df[(df["週"] == 1) & (df["種別"] == _LABELS["E"])].iloc[0]
        assert row["距離"] == 25.0

        row = df[(df["週"] == 2) & (df["種別"] == _LABELS["I"])].iloc[0]
        assert row["距離"] == 15.0

    def test_order_column(self):
        df = build_weekly_load_df(_make_stats(self._sample_weekly_load()))
        row = df[(df["週"] == 1) & (df["種別"] == _LABELS["E"])].iloc[0]
        assert row["順序"] == _ORDER_INDEX["E"]

        row = df[(df["週"] == 1) & (df["種別"] == _LABELS["other"])].iloc[0]
        assert row["順序"] == _ORDER_INDEX["other"]

        row = df[(df["週"] == 2) & (df["種別"] == _LABELS["M"])].iloc[0]
        assert row["順序"] == _ORDER_INDEX["M"]

    def test_all_labels_are_known(self):
        df = build_weekly_load_df(_make_stats(self._sample_weekly_load()))
        known_labels = set(_LABELS.values())
        assert set(df["種別"]).issubset(known_labels)


class TestBuildWeeklyLoadDfInvalidInput:
    """None・不正statsの扱い"""

    def test_none_stats(self):
        assert build_weekly_load_df(None) is None

    def test_not_a_dict(self):
        assert build_weekly_load_df("not a dict") is None
        assert build_weekly_load_df([]) is None

    def test_empty_weekly_load(self):
        assert build_weekly_load_df(_make_stats([])) is None

    def test_missing_weekly_load_key(self):
        stats = _make_stats([{"week": 1, "total_km": 10.0, "breakdown": {"E": 10.0}, "point_sessions": 0}])
        del stats["weekly_load"]
        assert build_weekly_load_df(stats) is None

    def test_weekly_load_not_a_list(self):
        stats = _make_stats("not a list")
        assert build_weekly_load_df(stats) is None

    def test_all_zero_breakdown(self):
        weekly_load = [
            {
                "week": 1,
                "total_km": 0.0,
                "breakdown": {"E": 0.0, "M": 0.0, "T": 0.0, "I": 0.0, "R": 0.0, "other": 0.0},
                "point_sessions": 0,
            },
            {
                "week": 2,
                "total_km": 0.0,
                "breakdown": {"E": 0.0, "M": 0.0, "T": 0.0, "I": 0.0, "R": 0.0, "other": 0.0},
                "point_sessions": 0,
            },
        ]
        assert build_weekly_load_df(_make_stats(weekly_load)) is None

    def test_week_with_invalid_breakdown_is_skipped(self):
        weekly_load = [
            {"week": 1, "total_km": 10.0, "breakdown": "not a dict", "point_sessions": 0},
            {
                "week": 2,
                "total_km": 20.0,
                "breakdown": {"E": 20.0, "M": 0.0, "T": 0.0, "I": 0.0, "R": 0.0, "other": 0.0},
                "point_sessions": 0,
            },
        ]
        df = build_weekly_load_df(_make_stats(weekly_load))
        assert df is not None
        assert set(df["週"]) == {2}

    def test_non_dict_week_entry_is_skipped(self):
        weekly_load = [
            "not a dict",
            {
                "week": 2,
                "total_km": 20.0,
                "breakdown": {"E": 20.0, "M": 0.0, "T": 0.0, "I": 0.0, "R": 0.0, "other": 0.0},
                "point_sessions": 0,
            },
        ]
        df = build_weekly_load_df(_make_stats(weekly_load))
        assert df is not None
        assert set(df["週"]) == {2}
