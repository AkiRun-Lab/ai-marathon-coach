"""
AI Marathon Coach - Plan Stats
計画JSON（weekly_schedules）から週間走行距離・強度種別の内訳を集計する基盤。

後続の「シューズ提案CTA」「週間負荷グラフ」機能の土台。Gemini API呼び出しは行わない
（`convert_json_to_markdown` がパース済みの plan dict をこのモジュールに渡すだけ）。

集計対象のJSONはAIが生成するため、キー欠落・空文字・非数値が実運用で発生する
（gemini_client.py の `_repair_json` 参照）。本モジュールは例外を外に漏らさず、
集計不能な日・週はスキップ／other扱いにする（アプリ本体の計画表示を壊さないため）。
"""
import re
from typing import Optional


# 休養系キーワード（menu/paceのいずれかに含まれていれば "rest" 扱い）
# 注意: 「レスト」は練習内の回復（例: "I 1000m×5（レスト200mジョグ）"）に頻出するため
# 部分一致には入れない。menu単独が「レスト」のときのみ休養扱い（classify_day参照）
_REST_KEYWORDS = ["休養", "休み", "完全休", "オフ"]

# menuキーワードによる強度分類フォールバック（pace記号で判定できない場合に使う）
# 先勝ち。「クルーズインターバル」は閾値系のため「インターバル」より先に判定する
_MENU_KEYWORD_MAP = [
    (["クルーズ", "閾値", "テンポ"], "T"),
    (["インターバル"], "I"),
    (["レペ"], "R"),
    (["マラソンペース", "Mペース"], "M"),
    (["ジョグ", "イージー", "回復", "ロング", "LSD", "Eペース"], "E"),
]

# 文字列中の強度記号（E/M/T/I/R）を検出する正規表現
# 例: "E 4:50〜5:00/km" / "R 3:12/km（200m≒38秒）" / "T20分" / "E＋流し" /
#     複合練習 "E 5:33〜4:55/km, M 4:30/km" 等（先頭に限らずすべて拾う）
# 前後に英字が続く場合（"Easy"のE等、英単語の一部）は記号ではないため除外
_PACE_SYMBOL_RE = re.compile(r"(?<![A-Za-z])(E|M|T|I|R)(?=[\s:：0-9ペ+＋/／])")

# 複合練習（例: Eジョグ + Mペース刺激）は最も強度の高い要素で分類する
# （ポイント練習を含む日をポイント練習として数えるため）
_INTENSITY_RANK = {"E": 0, "M": 1, "T": 2, "I": 3, "R": 4}

# distanceの数値抽出（範囲表記 "10-12km" / "10〜12km" にも対応）
_DISTANCE_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-〜~]\s*(\d+(?:\.\d+)?)")
_DISTANCE_SINGLE_RE = re.compile(r"(\d+(?:\.\d+)?)")


def parse_distance_km(text) -> Optional[float]:
    """"12km"・"10-12km"・"10〜12km" 等から距離(km)を数値抽出する

    範囲表記の場合は平均値を返す。数値が取れない場合はNone。

    Args:
        text: distanceフィールドの文字列（None・空文字・非文字列も許容）

    Returns:
        距離(km)。抽出不能ならNone
    """
    if text is None:
        return None
    text = str(text).strip()
    if not text:
        return None

    range_match = _DISTANCE_RANGE_RE.search(text)
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        return (low + high) / 2

    single_match = _DISTANCE_SINGLE_RE.search(text)
    if single_match:
        return float(single_match.group(1))

    return None


def classify_day(menu, pace) -> str:
    """1日分のmenu/paceから強度種別を判定する

    判定順序:
        1. paceにE/M/T/I/Rの記号がある → 最も強度の高い記号
           （複合練習 "E 5:33/km, M 4:30/km" はM。「レスト3分」等の休養系語が
           練習メニュー内に混在しても誤判定しないよう最優先）
        2. menu/paceに休養系キーワードが含まれる、またはmenu単独が「レスト」 → "rest"
        3. menuの強度記号・キーワードでフォールバック判定（複数該当時は最も強度の高いもの）
        4. いずれも該当なし → "other"

    Args:
        menu: メニュー文字列（None・空文字も許容）
        pace: ペース文字列（None・空文字も許容）

    Returns:
        "E"/"M"/"T"/"I"/"R"/"rest"/"other" のいずれか
    """
    menu_str = str(menu).strip() if menu else ""
    pace_str = str(pace).strip() if pace else ""

    pace_symbols = _PACE_SYMBOL_RE.findall(pace_str)
    if pace_symbols:
        return max(pace_symbols, key=lambda s: _INTENSITY_RANK[s])

    combined = f"{menu_str} {pace_str}"
    if any(keyword in combined for keyword in _REST_KEYWORDS) or menu_str == "レスト":
        return "rest"

    menu_symbols = _PACE_SYMBOL_RE.findall(menu_str)
    if menu_symbols:
        return max(menu_symbols, key=lambda s: _INTENSITY_RANK[s])

    for keywords, category in _MENU_KEYWORD_MAP:
        if any(keyword in menu_str for keyword in keywords):
            return category

    return "other"


def aggregate_weekly_load(plan: dict) -> list:
    """weekly_schedulesを週ごとに集計する

    Args:
        plan: convert_json_to_markdown内部で組み立てるplan dict
              （"weekly_schedules": [{"week", "dates", "total_distance", "days": [...]}, ...]）

    Returns:
        [{"week": int, "total_km": float, "breakdown": {"E","M","T","I","R","other": km}, "point_sessions": int}, ...]
        weekly_schedulesが無い/空、または集計不能な場合は空リスト
    """
    if not isinstance(plan, dict):
        return []

    weeks = plan.get("weekly_schedules")
    if not isinstance(weeks, list):
        return []

    result = []
    for week in weeks:
        if not isinstance(week, dict):
            continue

        try:
            week_num = int(week.get("week", 0))
        except (TypeError, ValueError):
            week_num = 0

        breakdown = {"E": 0.0, "M": 0.0, "T": 0.0, "I": 0.0, "R": 0.0, "other": 0.0}
        point_sessions = 0
        days_total_km = 0.0

        days = week.get("days", [])
        if not isinstance(days, list):
            days = []

        for day in days:
            if not isinstance(day, dict):
                continue

            distance_km = parse_distance_km(day.get("distance"))
            category = classify_day(day.get("menu"), day.get("pace"))

            if category == "rest":
                continue

            if distance_km is not None:
                days_total_km += distance_km
                if category == "other":
                    breakdown["other"] += distance_km
                else:
                    breakdown[category] += distance_km

            if category in ("M", "T", "I", "R"):
                point_sessions += 1

        # total_kmはtotal_distanceのパースを優先、取れなければdays合計にフォールバック
        total_km = parse_distance_km(week.get("total_distance"))
        if total_km is None:
            total_km = days_total_km

        result.append({
            "week": week_num,
            "total_km": total_km,
            "breakdown": breakdown,
            "point_sessions": point_sessions,
        })

    return result


def judge_shoe_cta_category(weekly_load: list) -> str:
    """週平均のポイント練習回数から、シューズ提案CTAのカテゴリを判定する

    Args:
        weekly_load: aggregate_weekly_load() の戻り値

    Returns:
        "point_heavy"（週平均2回以上）/ "balanced"（1回以上2回未満）/
        "easy_focus"（1回未満）/ "general"（weekly_loadが空）
    """
    if not weekly_load:
        return "general"

    total_sessions = sum(week.get("point_sessions", 0) for week in weekly_load)
    avg_sessions = total_sessions / len(weekly_load)

    if avg_sessions >= 2:
        return "point_heavy"
    if avg_sessions >= 1:
        return "balanced"
    return "easy_focus"


def summarize_plan_stats(plan: dict) -> Optional[dict]:
    """計画dictから集計サマリを組み立てるエントリポイント

    Args:
        plan: convert_json_to_markdown内部で組み立てるplan dict

    Returns:
        {
            "weekly_load": [...],
            "cta_category": str,
            "avg_weekly_km": float,
            "avg_point_sessions": float,
        }
        plan不正・集計不能な場合はNone（例外は投げない）
    """
    if not isinstance(plan, dict):
        return None

    try:
        weekly_load = aggregate_weekly_load(plan)
        if not weekly_load:
            return None

        cta_category = judge_shoe_cta_category(weekly_load)
        avg_weekly_km = sum(w.get("total_km", 0.0) for w in weekly_load) / len(weekly_load)
        avg_point_sessions = sum(w.get("point_sessions", 0) for w in weekly_load) / len(weekly_load)

        return {
            "weekly_load": weekly_load,
            "cta_category": cta_category,
            "avg_weekly_km": avg_weekly_km,
            "avg_point_sessions": avg_point_sessions,
        }
    except Exception:
        # 集計失敗時もアプリ本体の計画表示は壊さない（呼び出し側はNone判定でstats非表示にする）
        return None
