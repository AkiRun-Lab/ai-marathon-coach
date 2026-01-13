"""
AI Marathon Coach - Configuration
アプリケーション全体の設定値を管理
"""

# =============================================
# アプリ情報
# =============================================
APP_NAME = "AIマラソンコーチ"
APP_VERSION = "1.0.0"

# =============================================
# Gemini API 設定
# =============================================
GEMINI_MODEL_NAME = "gemini-3-flash-preview"

# Generation config
GEMINI_TEMPERATURE = 0.7
GEMINI_TOP_P = 0.95
GEMINI_MAX_OUTPUT_TOKENS = 32768

# =============================================
# トレーニング設定
# =============================================
# 最低トレーニング期間（週）
MIN_TRAINING_WEEKS = 12

# フェーズ数（固定）
NUM_PHASES = 4

# VDOT別の許容VDOT差（1サイクルあたり）
# (VDOTの下限, VDOTの上限): 許容差
VDOT_DIFF_BY_LEVEL = {
    (0, 40): 4.0,      # 初心者：伸びしろが大きい
    (40, 50): 3.0,     # 中級者：着実な向上
    (50, 55): 2.5,     # 上級者：改善が難しくなる
    (55, 60): 2.0,     # エリート：1ポイントの差が大きい
    (60, 100): 1.5,    # トップエリート：微細な改善のみ
}

def get_max_vdot_diff(current_vdot: float) -> float:
    """現在のVDOTに応じた許容VDOT差を返す"""
    for (lower, upper), diff in VDOT_DIFF_BY_LEVEL.items():
        if lower <= current_vdot < upper:
            return diff
    return 2.0  # デフォルト

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

