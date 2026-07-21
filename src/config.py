"""
AI Marathon Coach - Configuration
アプリケーション全体の設定値を管理
"""
from datetime import datetime
from zoneinfo import ZoneInfo


def jst_now() -> datetime:
    """日本時間の現在時刻をnaive datetimeで返す

    本番（Streamlit Cloud）はUTCで動くため、素の datetime.now() では
    日本の利用者と最大9時間ズレる（開始日の月曜計算・レースまでの週数に影響）。
    既存コードはnaive datetime同士の演算を前提としているため、tzinfoは外して返す。
    """
    return datetime.now(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)


# =============================================
# アプリ情報
# =============================================
APP_NAME = "マラソントレーニング・プランナー"
APP_VERSION = "1.13.2"

# シューマッチング診断ツール（akirun.net内蔵アプリ・アフィリエイトではない）への送客先。
# VDOTをクエリパラメータで渡し、練習ペース帯に合うシューズを診断する。
SHOE_FINDER_URL = "https://akirun.net/lp/shoe-finder/"

# Amazonストアフロント（おすすめギア一覧）への送客先。
# 汎用CTAはストアトップ、シューズCTAは下のアイデアリスト個別URLを使う。
AMAZON_STORE_URL = "https://www.amazon.co.jp/shop/yancearmstron"
AMAZON_RACE_SHOES_LIST_URL = "https://amzn.to/44ZTgZQ"      # リスト①: サブ3を狙うレースシューズ
AMAZON_DAILY_TRAINER_LIST_URL = "https://amzn.to/4wBLAsD"   # リスト②: 練習用デイリートレーナー

# 計画連動シューズ提案CTAの文言バリアント（plan_stats.judge_shoe_cta_category の戻り値がキー）
# point_heavy はレースシューズ、balanced/easy_focus はデイリートレーナーのアイデアリストへ送客する
# （2026-07-12発行の短縮URL）。general のみ保険としてストアトップ
# 文言中の {km} は週平均走行距離で置換する。「ポイント練習◯回」という回数表示は、ユーザーの
# 入力欄「ポイント練習回数」や計画本文のラベルと語が衝突して混乱を招くため使わない（2026-07-16）。
# 速い練習の量は定性的に表現し、争いのない週間距離を数値の軸にする。
SHOE_CTA_VARIANTS = {
    "point_heavy": {
        "title": "速い練習用とジョグ用、2足ローテーションが合う計画です",
        "sub": "閾値走やインターバルなど速いペースの練習と、まとまった距離の両方が入る計画です。速い練習・レース用のシューズと、Eジョグ用のデイリートレーナーを分けると、練習の質を保ちながら脚への負担を分散しやすくなります。私が実走で使っているおすすめ一覧から探せます。",
        "url": AMAZON_RACE_SHOES_LIST_URL,
    },
    "balanced": {
        "title": "デイリートレーナーを軸に、速い練習用の1足があると心強い計画です",
        "sub": "週平均{km}kmの走り込みを支えるデイリートレーナーを軸に、閾値走やインターバルなど速いペースの練習用にもう1足。用途別のおすすめ一覧にまとめています。",
        "url": AMAZON_DAILY_TRAINER_LIST_URL,
    },
    "easy_focus": {
        "title": "距離を踏む計画。脚を守るデイリートレーナーが主役です",
        "sub": "週平均{km}kmを積み上げる計画では、クッション性と耐久性のあるデイリートレーナーが練習の土台になります。私が実走で使っているおすすめ一覧から選べます。",
        "url": AMAZON_DAILY_TRAINER_LIST_URL,
    },
    "general": {
        "title": "練習用とレース用のシューズの使い分けが、練習の質を支えます",
        "sub": "毎日の練習を支えるデイリートレーナーと、速い練習・レース用の1足。私が実走で使っているおすすめ一覧にまとめています。",
        "url": AMAZON_STORE_URL,
    },
}

# =============================================
# Gemini API Configuration (Gemini 3.6)
# =============================================
GEMINI_AVAILABLE_MODELS = {
    "gemini-3.6-flash": "Gemini 3.6 Flash（高性能）",
    "gemini-3.5-flash-lite": "Gemini 3.5 Flash Lite（軽量・高速）",
}
GEMINI_DEFAULT_MODEL = "gemini-3.6-flash"

# 計画生成リクエストのタイムアウト（秒）。SDKデフォルトは無期限のためハング対策として明示
PLAN_TIMEOUT_SEC = 600
# 503（モデル高負荷）でリトライが尽きた際のフォールバックモデル。
# UIのモデル選択とは独立に常にこのモデルへ切り替える（2026-07-11ユーザー決定）。
# gemini-3.5-flashは2026-07-22までメイン生成モデルとして本番稼働していたGA版であり、
# JSONモード＋thinking_level互換は実運用で実証済み（preview版のような廃止リスクがない）
GEMINI_FALLBACK_MODEL = "gemini-3.5-flash"
FALLBACK_MAX_ATTEMPTS = 2

# Generation Config
# 注: temperature / top_p / top_k は全 Gemini 3.x モデルで非推奨となり削除（公式: デフォルト設定が最適化済み）
# 注: thinkingトークンも max_output_tokens を消費するため、計画本文の必要量に思考分の余裕を上乗せした床値にする
#     （16384だと12週計画の本文約16,400トークンでギリギリ→24576へ引き上げ後も、thinkingが長い生成回で
#     途中切断＝変換エラーが実際に発生したため32768へ再引き上げ・2026-07-12。上限キャップであり課金は実生成分のみ）
GEMINI_MAX_OUTPUT_TOKENS = 32768  # 最低保証値

# Response Format
GEMINI_RESPONSE_MIME_TYPE = "application/json"

# Thinking Config (Gemini 3.x Spec)
# thinking_level: VDOT計算や週間走行距離の整合性チェックなど、深い推論を行わせるための思考レベル
# 値は minimal / low / medium(デフォルト) / high。深い推論を要するため high を指定
GEMINI_THINKING_MODE = True
GEMINI_THINKING_LEVEL = "high"

# Gemini 3.6 Flashの最大出力トークン数
GEMINI_MAX_OUTPUT_TOKENS_LIMIT = 65536

def get_max_output_tokens(training_weeks: int) -> int:
    """トレーニング週数に応じた最大出力トークン数を返す
    
    1週あたり約1200トークン（7日×各行約170トークン）+ ヘッダー等のオーバーヘッド
    最低GEMINI_MAX_OUTPUT_TOKENS（24576）、最大65536を保証。
    
    Args:
        training_weeks: トレーニング週数
        
    Returns:
        最大出力トークン数
    """
    tokens = training_weeks * 1200 + 2048
    return max(GEMINI_MAX_OUTPUT_TOKENS, min(tokens, GEMINI_MAX_OUTPUT_TOKENS_LIMIT))

# =============================================
# トレーニング設定
# =============================================
# 最低トレーニング期間（週）
MIN_TRAINING_WEEKS = 12

# フェーズ数（固定）
NUM_PHASES = 4

# VDOT別の許容VDOT差（12週基準値）
# 実際の許容差はトレーニング期間に応じてスケーリングされる
# (VDOTの下限, VDOTの上限): 12週あたりの許容差
BASE_TRAINING_WEEKS = 12  # VDOT_DIFF_BY_LEVELの基準週数

VDOT_DIFF_BY_LEVEL = {
    (0, 40): 4.0,      # 初心者：伸びしろが大きい
    (40, 50): 3.0,     # 中級者：着実な向上
    (50, 55): 2.5,     # 上級者：改善が難しくなる
    (55, 60): 2.0,     # エリート：1ポイントの差が大きい
    (60, 100): 1.5,    # トップエリート：微細な改善のみ
}

# スケーリング倍率の上限（逓減効果のキャップ）
VDOT_DIFF_SCALE_CAP = 2.5

def get_max_vdot_diff(current_vdot: float, training_weeks: int = BASE_TRAINING_WEEKS) -> float:
    """現在のVDOTとトレーニング期間に応じた許容VDOT差を返す
    
    12週を基準とし、期間が長い場合は平方根スケーリング（逓減効果）で
    許容差を拡大する。最大で基準値の2.5倍まで。
    
    Args:
        current_vdot: 現在のVDOT値
        training_weeks: トレーニング週数（デフォルト12週）
    
    Returns:
        許容VDOT差
    """
    import math
    
    # 基準差を取得
    base_diff = 2.0  # デフォルト
    for (lower, upper), diff in VDOT_DIFF_BY_LEVEL.items():
        if lower <= current_vdot < upper:
            base_diff = diff
            break
    
    # 12週基準のスケーリング（平方根で逓減効果を表現）
    scale = min(math.sqrt(training_weeks / BASE_TRAINING_WEEKS), VDOT_DIFF_SCALE_CAP)
    
    return round(base_diff * scale, 1)

# 目標VDOT別の最低トレーニング条件
# (VDOTの下限, VDOTの上限): (最低週間距離km, 最低練習日数, 最低ポイント練習回数)
MIN_TRAINING_REQUIREMENTS = {
    (0, 40): (40, 3, 1),       # サブ4以上目標
    (40, 45): (50, 4, 1),      # サブ3:40目標
    (45, 50): (60, 4, 2),      # サブ3:20目標
    (50, 55): (80, 5, 2),      # サブ3:00目標
    (55, 60): (100, 5, 2),     # サブ2:45目標
    (60, 100): (120, 6, 3),    # サブ2:35以下目標
}

def get_min_requirements(target_vdot: float) -> tuple:
    """目標VDOTに応じた最低条件を返す (距離, 日数, ポイント練習)"""
    for (lower, upper), requirements in MIN_TRAINING_REQUIREMENTS.items():
        if lower <= target_vdot < upper:
            return requirements
    return (60, 4, 2)  # デフォルト

def validate_training_conditions(target_vdot: float, weekly_distance: int, 
                                  training_days: int, point_training_days: int) -> dict:
    """トレーニング条件が最低条件を満たしているか判定
    
    Returns:
        dict: {
            'is_valid': bool,
            'warnings': list of str,
            'min_distance': int,
            'min_days': int,
            'min_point': int
        }
    """
    min_dist, min_days, min_point = get_min_requirements(target_vdot)
    warnings = []
    
    # 入力値をint型に変換
    weekly_distance = int(weekly_distance) if weekly_distance else 0
    training_days = int(training_days) if training_days else 0
    point_training_days = int(point_training_days) if point_training_days else 0
    
    if weekly_distance < min_dist:
        warnings.append(f"週間走行距離が不足しています（現在: {weekly_distance}km、推奨: {min_dist}km以上）")
    
    if training_days < min_days:
        warnings.append(f"練習日数が不足しています（現在: {training_days}日、推奨: {min_days}日以上）")
    
    if point_training_days < min_point:
        warnings.append(f"ポイント練習回数が不足しています（現在: {point_training_days}回、推奨: {min_point}回以上）")
    
    return {
        'is_valid': len(warnings) == 0,
        'warnings': warnings,
        'min_distance': min_dist,
        'min_days': min_days,
        'min_point': min_point
    }

# =============================================
# データファイルパス
# =============================================
DATA_DIR = "data"
VDOT_LIST_FILE = "vdot_list.csv"
VDOT_PACE_FILE = "vdot_pace.csv"

