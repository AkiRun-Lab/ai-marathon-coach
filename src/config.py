"""
AI Marathon Coach - Configuration
アプリケーション全体の設定値を管理
"""

# =============================================
# アプリ情報
# =============================================
APP_NAME = "AIマラソンコーチ"
APP_VERSION = "1.6.1"

# =============================================
# Gemini API Configuration (Corrected for Gemini 3)
# =============================================
GEMINI_MODEL_NAME = "gemini-3-flash-preview"

# Generation Config
# VDOT計算の正確性を担保するため、創造性を抑える
GEMINI_TEMPERATURE = 0.1
GEMINI_TOP_P = 0.95
GEMINI_MAX_OUTPUT_TOKENS = 16384  # 最低保証値

# Response Format
GEMINI_RESPONSE_MIME_TYPE = "application/json"

# Thinking Config (Gemini 3 Spec)
# thinking_budget: VDOT計算や週間走行距離の整合性チェックなど、深い推論を行わせるための思考予算
GEMINI_THINKING_MODE = True
GEMINI_THINKING_BUDGET = 8192

# Gemini 3 Flashの最大出力トークン数
GEMINI_MAX_OUTPUT_TOKENS_LIMIT = 65536

def get_max_output_tokens(training_weeks: int) -> int:
    """トレーニング週数に応じた最大出力トークン数を返す
    
    1週あたり約1200トークン（7日×各行約170トークン）+ ヘッダー等のオーバーヘッド
    最低16384、最大65536を保証。
    
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

