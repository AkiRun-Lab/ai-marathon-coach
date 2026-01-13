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

# 1回の計画で許容するVDOT差の上限
MAX_VDOT_DIFF_PER_CYCLE = 3.0

# =============================================
# データファイルパス
# =============================================
DATA_DIR = "data"
VDOT_LIST_FILE = "vdot_list.csv"
VDOT_PACE_FILE = "vdot_pace.csv"
