"""
AIマラソンコーチ - Streamlit App
ジャック・ダニエルズのVDOT理論に基づくトレーニング計画生成

Version: β0.9
"""

import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import re
from datetime import datetime, timedelta
import io

# =============================================
# アプリ設定
# =============================================
APP_NAME = "AIマラソンコーチ"
APP_VERSION = "β0.9"

# =============================================
# ページ設定
# =============================================
st.set_page_config(
    page_title=f"{APP_NAME} v{APP_VERSION}",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================
# カスタムCSS
# =============================================
st.markdown("""
<style>
    /* サイドバーを非表示 */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .version-tag {
        font-size: 0.9rem;
        color: #888;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .form-section {
        background-color: #F5F5F5;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    .form-section-title {
        font-size: 1.1rem;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .vdot-display {
        background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .training-output {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #FFF3E0;
        border-left: 4px solid #FF9800;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #FFEBEE;
        border-left: 4px solid #F44336;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    .time-selector {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# =============================================
# CSVデータの読み込みとキャッシュ
# =============================================
@st.cache_data
def load_csv_data():
    """CSVファイルを読み込み、検証ログを生成"""
    verification_log = {
        "success": False,
        "files": [],
        "vdot_range": {"min": None, "max": None},
        "columns": {},
        "errors": []
    }
    
    try:
        df_vdot_list = pd.read_csv("data/vdot_list.csv")
        verification_log["files"].append("vdot_list.csv")
        verification_log["columns"]["VDOT_list"] = list(df_vdot_list.columns)

        df_pace = pd.read_csv("data/vdot_pace.csv")
        verification_log["files"].append("vdot_pace.csv")

        df_pace.columns = df_pace.columns.str.strip()
        verification_log["columns"]["VDOT_pace"] = list(df_pace.columns)
        
        vdot_col = "VDot" if "VDot" in df_pace.columns else "VDOT"
        vdot_min = int(df_pace[vdot_col].min())
        vdot_max = int(df_pace[vdot_col].max())
        verification_log["vdot_range"]["min"] = vdot_min
        verification_log["vdot_range"]["max"] = vdot_max
        
        verification_log["success"] = True
        
        return df_vdot_list, df_pace, verification_log
        
    except FileNotFoundError as e:
        verification_log["errors"].append(f"ファイルが見つかりません: {str(e)}")
        return None, None, verification_log
    except Exception as e:
        verification_log["errors"].append(f"読み込みエラー: {str(e)}")
        return None, None, verification_log


# =============================================
# VDOT計算関数群
# =============================================
def time_to_seconds(time_str: str) -> int:
    """時間文字列を秒に変換"""
    if pd.isna(time_str):
        return None
    
    time_str = str(time_str).strip()
    
    if time_str.count(':') == 2:
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + int(s)
    
    elif time_str.count(':') == 1:
        parts = time_str.split(':')
        if len(parts) == 2:
            m, s = parts
            if ':' in str(s):
                return int(m) * 60 + int(s.split(':')[0])
            return int(m) * 60 + int(s)
    
    try:
        return int(float(time_str))
    except:
        return None


def seconds_to_time(seconds: int, include_hours: bool = False) -> str:
    """秒を時間文字列に変換"""
    if seconds is None:
        return "N/A"
    
    seconds = round(seconds)
    
    if include_hours or seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}:{m:02d}:{s:02d}"
    else:
        m = seconds // 60
        s = seconds % 60
        return f"{m}:{s:02d}"


def calculate_vdot_from_time(df_vdot: pd.DataFrame, distance: str, time_seconds: int) -> dict:
    """タイムからVDOTを線型補完で算出"""
    result = {
        "vdot": None,
        "calculation_log": "",
        "reference_data": {}
    }
    
    distance_mapping = {
        "5km": "5000m",
        "5000m": "5000m",
        "10km": "10000m",
        "10000m": "10000m",
        "ハーフ": "HalfMarathon",
        "ハーフマラソン": "HalfMarathon",
        "half": "HalfMarathon",
        "フル": "Marathon",
        "フルマラソン": "Marathon",
        "marathon": "Marathon",
        "マラソン": "Marathon"
    }
    
    col_name = distance_mapping.get(distance, distance)
    
    if col_name not in df_vdot.columns:
        result["calculation_log"] = f"エラー: 距離 '{distance}' が見つかりません"
        return result
    
    vdot_times = []
    for _, row in df_vdot.iterrows():
        vdot = int(row['VDOT'])
        time_val = row[col_name]
        time_sec = time_to_seconds(str(time_val))
        if time_sec:
            vdot_times.append((vdot, time_sec))
    
    vdot_times.sort(key=lambda x: x[1], reverse=True)
    
    lower_vdot = None
    upper_vdot = None
    
    for i, (vdot, time_sec) in enumerate(vdot_times):
        if time_sec <= time_seconds:
            lower_vdot = (vdot, time_sec)
            if i > 0:
                upper_vdot = vdot_times[i - 1]
            break
    
    if lower_vdot is None:
        lower_vdot = vdot_times[-1]
        upper_vdot = vdot_times[-2] if len(vdot_times) > 1 else None
    
    if upper_vdot is None:
        result["vdot"] = float(lower_vdot[0])
        result["calculation_log"] = f"VDOT {lower_vdot[0]} を使用（範囲外のため最も近い値）"
        return result
    
    vdot_low, time_low = upper_vdot
    vdot_high, time_high = lower_vdot
    
    if vdot_low > vdot_high:
        vdot_low, time_low, vdot_high, time_high = vdot_high, time_high, vdot_low, time_low
    
    if time_low != time_high:
        ratio = (time_low - time_seconds) / (time_low - time_high)
        calculated_vdot = vdot_low + (vdot_high - vdot_low) * ratio
    else:
        calculated_vdot = vdot_low
    
    result["vdot"] = round(calculated_vdot, 2)
    result["reference_data"] = {
        "vdot_low": vdot_low,
        "time_low": seconds_to_time(time_low, True),
        "time_low_sec": time_low,
        "vdot_high": vdot_high,
        "time_high": seconds_to_time(time_high, True),
        "time_high_sec": time_high
    }
    result["calculation_log"] = (
        f"【計算過程】\n"
        f"参照データ: VDOT {vdot_low} = {seconds_to_time(time_low, True)}, "
        f"VDOT {vdot_high} = {seconds_to_time(time_high, True)}\n"
        f"入力タイム: {seconds_to_time(time_seconds, True)}\n"
        f"計算式: {vdot_low} + ({vdot_high} - {vdot_low}) × "
        f"({time_low} - {time_seconds}) / ({time_low} - {time_high})\n"
        f"= {vdot_low} + {vdot_high - vdot_low} × {ratio:.4f}\n"
        f"= {calculated_vdot:.2f}"
    )
    
    return result


def calculate_training_paces(df_pace: pd.DataFrame, vdot: float) -> dict:
    """VDOTから練習ペースを線型補完で算出"""
    result = {
        "paces": {},
        "calculation_log": "",
        "success": False
    }
    
    vdot_col = "VDot" if "VDot" in df_pace.columns else "VDOT"
    
    vdot_low = int(vdot)
    vdot_high = vdot_low + 1
    decimal_ratio = vdot - vdot_low
    
    row_low = df_pace[df_pace[vdot_col] == vdot_low]
    row_high = df_pace[df_pace[vdot_col] == vdot_high]
    
    if row_low.empty:
        result["calculation_log"] = f"エラー: VDOT {vdot_low} がファイルに存在しません"
        return result
    
    if row_high.empty:
        row_high = row_low
        decimal_ratio = 0
    
    row_low = row_low.iloc[0]
    row_high = row_high.iloc[0]
    
    pace_types = ["E_min", "E_max", "M", "T", "I", "R"]
    calculation_details = []
    
    for pace_type in pace_types:
        if pace_type not in df_pace.columns:
            continue
        
        pace_low_str = str(row_low[pace_type])
        pace_high_str = str(row_high[pace_type])
        
        pace_low_sec = time_to_seconds(pace_low_str)
        pace_high_sec = time_to_seconds(pace_high_str)
        
        if pace_low_sec is None or pace_high_sec is None:
            continue
        
        pace_sec = pace_low_sec + (pace_high_sec - pace_low_sec) * decimal_ratio
        pace_sec = round(pace_sec)
        
        result["paces"][pace_type] = {
            "seconds": pace_sec,
            "display": seconds_to_time(pace_sec)
        }
        
        calculation_details.append(
            f"  {pace_type}: {pace_low_sec}秒 + ({pace_high_sec}秒 - {pace_low_sec}秒) × {decimal_ratio:.2f} "
            f"= {pace_sec}秒 → {seconds_to_time(pace_sec)}/km"
        )
    
    if "E_min" in result["paces"] and "E_max" in result["paces"]:
        result["paces"]["E"] = {
            "display": f"{result['paces']['E_min']['display']}〜{result['paces']['E_max']['display']}",
            "min": result["paces"]["E_min"],
            "max": result["paces"]["E_max"]
        }
    
    result["calculation_log"] = (
        f"【練習ペース計算過程】\n"
        f"設定VDOT: {vdot} (VDOT {vdot_low} と VDOT {vdot_high} の間、比率 {decimal_ratio:.2f})\n"
        f"参照データ（VDOT {vdot_low}）: E={row_low['E_min']}〜{row_low['E_max']}, "
        f"M={row_low['M']}, T={row_low['T']}, I={row_low['I']}, R={row_low['R']}\n"
        f"参照データ（VDOT {vdot_high}）: E={row_high['E_min']}〜{row_high['E_max']}, "
        f"M={row_high['M']}, T={row_high['T']}, I={row_high['I']}, R={row_high['R']}\n"
        f"計算詳細:\n" + "\n".join(calculation_details)
    )
    
    result["success"] = True
    return result


def calculate_phase_vdots(current_vdot: float, target_vdot: float, num_phases: int) -> list:
    """フェーズごとのVDOT目標を計算"""
    if num_phases <= 1:
        return [target_vdot]
    
    vdot_diff = target_vdot - current_vdot
    step = vdot_diff / num_phases
    
    phase_vdots = []
    for i in range(1, num_phases + 1):
        phase_vdot = round(current_vdot + step * i, 2)
        phase_vdots.append(phase_vdot)
    
    return phase_vdots


# =============================================
# Gemini API 設定
# =============================================
def get_gemini_model():
    """Gemini APIモデルを取得"""
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    
    genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
        generation_config={
            "temperature": 0.7,
            "top_p": 0.95,
            "max_output_tokens": 8192,
        }
    )
    return model


def create_training_prompt(user_data: dict, vdot_info: dict, pace_info: dict, target_vdot_info: dict, df_pace: pd.DataFrame) -> str:
    """トレーニング計画生成用のプロンプトを作成"""
    
    paces = pace_info.get("paces", {}) if pace_info else {}
    current_vdot = vdot_info['vdot']
    target_vdot = target_vdot_info['vdot'] if target_vdot_info else current_vdot
    
    # レース日程から週数を計算
    race_date = user_data.get("race_date")
    weeks_until_race = 12
    race_date_str = ""
    if race_date:
        try:
            race_dt = datetime.strptime(race_date, "%Y-%m-%d")
            today = datetime.now()
            weeks_until_race = max(1, (race_dt - today).days // 7)
            race_date_str = race_dt.strftime("%Y/%m/%d")
        except:
            pass
    
    # フェーズ数を決定（4週間ごと、最低2フェーズ）
    num_phases = max(2, min(4, weeks_until_race // 4))
    weeks_per_phase = weeks_until_race // num_phases
    
    # フェーズごとのVDOT目標を計算
    phase_vdots = calculate_phase_vdots(current_vdot, target_vdot, num_phases)
    
    # 各フェーズのペース情報を生成
    phase_paces_info = []
    for i, phase_vdot in enumerate(phase_vdots):
        phase_pace = calculate_training_paces(df_pace, phase_vdot)
        phase_paces = phase_pace.get("paces", {})
        phase_paces_info.append({
            "phase": i + 1,
            "vdot": phase_vdot,
            "E": phase_paces.get('E', {}).get('display', 'N/A'),
            "M": phase_paces.get('M', {}).get('display', 'N/A'),
            "T": phase_paces.get('T', {}).get('display', 'N/A'),
            "I": phase_paces.get('I', {}).get('display', 'N/A'),
            "R": phase_paces.get('R', {}).get('display', 'N/A'),
        })
    
    # フェーズ情報をテキスト化
    phase_info_text = ""
    for p in phase_paces_info:
        phase_info_text += f"""
### フェーズ{p['phase']}（VDOT {p['vdot']}）
| ペース | 設定 |
|:---|:---|
| E (Easy) | {p['E']}/km |
| M (Marathon) | {p['M']}/km |
| T (Threshold) | {p['T']}/km |
| I (Interval) | {p['I']}/km |
| R (Repetition) | {p['R']}/km |
"""
    
    # 練習レースをQトレーニングとして処理
    practice_races_note = ""
    if user_data.get('practice_races'):
        practice_races_note = f"""
## ⚠️ 練習レースについて（重要）
以下の練習レースは**Qトレーニング（ポイント練習）として扱い**、その週のポイント練習回数に含めてください：
{user_data.get('practice_races')}

**練習レースがある週のルール：**
- 練習レースは週のポイント練習の1回としてカウント
- 練習レース以外のポイント練習を減らすか、軽めの内容に調整
- レース前日は軽いジョグまたは完全休養
- レース翌日はリカバリージョグ
"""
    
    prompt = f"""# Role
あなたは、ジャック・ダニエルズの「ランニング・フォーミュラ（VDOT理論）」を信奉するマラソン専属コーチです。
信念：「Train where you are（今の実力で練習し、目標の実力でレースをする）」

# ユーザー情報
- ニックネーム: {user_data.get('name', '不明')}
- 年齢: {user_data.get('age', '不明')}歳
- 性別: {user_data.get('gender', '不明')}
- 現在のベストタイム: {user_data.get('current_time', '不明')}（フルマラソン）
- 目標タイム: {user_data.get('target_time', '不明')}
- 本番レース: {user_data.get('race_name', '不明')}（{race_date_str}）
- レースまでの週数: 約{weeks_until_race}週間
- 練習レース: {user_data.get('practice_races', 'なし')}
- 週間走行距離: {user_data.get('weekly_distance', '不明')}km
- 練習可能日数: {user_data.get('training_days', '不明')}日/週
- ポイント練習可能回数: {user_data.get('point_training_days', '不明')}回/週
- 怪我・懸念事項: {user_data.get('concerns', 'なし')}

# VDOT段階的向上計画
- 現在のVDOT: {current_vdot}
- 目標VDOT: {target_vdot}
- フェーズ数: {num_phases}（各フェーズ約{weeks_per_phase}週間）

## フェーズごとのVDOTとペース設定（これらの値を必ず使用すること）
{phase_info_text}

{practice_races_note}

# 出力指示
以下の形式で、レースまでの全トレーニング計画を出力してください。
**重要**: 各フェーズでは、上記で指定したそのフェーズのVDOTに対応したペースを必ず使用してください。

## 出力形式（Markdown）

# 🏃‍♂️ {user_data.get('name', 'ユーザー')}さんのトレーニング計画

## 📊 基本情報
- 現在のVDOT: {current_vdot} → 目標VDOT: {target_vdot}
- 目標: {user_data.get('target_time', '')}（{user_data.get('race_name', '')} {race_date_str}）
- 期間: {weeks_until_race}週間（{num_phases}フェーズ）

---

## 📈 フェーズ概要

| フェーズ | 期間 | 目標VDOT | 主な目的 |
|:---|:---|:---|:---|
| フェーズ1 | 第1〜{weeks_per_phase}週 | {phase_vdots[0] if len(phase_vdots) > 0 else ''} | 基礎構築・回復 |
（続きを記載）

---

## 📋 週間トレーニング計画

### フェーズ1（VDOT {phase_vdots[0] if len(phase_vdots) > 0 else ''}）

**このフェーズのペース設定:**
| ペース | 設定 |
|:---|:---|
| E (Easy) | {phase_paces_info[0]['E'] if len(phase_paces_info) > 0 else 'N/A'}/km |
| M (Marathon) | {phase_paces_info[0]['M'] if len(phase_paces_info) > 0 else 'N/A'}/km |
| T (Threshold) | {phase_paces_info[0]['T'] if len(phase_paces_info) > 0 else 'N/A'}/km |
| I (Interval) | {phase_paces_info[0]['I'] if len(phase_paces_info) > 0 else 'N/A'}/km |
| R (Repetition) | {phase_paces_info[0]['R'] if len(phase_paces_info) > 0 else 'N/A'}/km |

#### 第1週（MM/DD（月）〜MM/DD（日））

| 日付 | メニュー | 距離 | ペース | アドバイス |
|:---|:---|:---|:---|:---|
| MM/DD（月） | Easyジョグ | 10km | {phase_paces_info[0]['E'] if len(phase_paces_info) > 0 else 'N/A'}/km | ... |
（以下続く）

---

## ⚠️ 注意事項
（全体を通しての注意点）

## 💪 コーチからのメッセージ
（励ましのメッセージ）

---
*Generated by {APP_NAME} v{APP_VERSION}*

# 重要な指示
1. 日付は「MM/DD（曜日）」形式で記載（例：1/6（月）, 2/14（金））
2. 各フェーズで、上記で指定したそのフェーズのVDOTに対応したペースを必ず使用すること
3. 練習レースはQトレーニング（ポイント練習）としてカウントし、その週の他のポイント練習を調整すること
4. 週間走行距離は{user_data.get('weekly_distance', '不明')}kmを目安にすること
5. ポイント練習は週{user_data.get('point_training_days', '3')}回までにすること
6. フェーズが進むごとにVDOTとペースを段階的に上げること
7. 本番レース日は{race_date_str}であることを考慮し、最終週はテーパリングを入れること
8. 今日の日付は{datetime.now().strftime('%Y/%m/%d')}です。この日付から計画を開始してください。
"""
    
    return prompt


# =============================================
# MDダウンロード用関数
# =============================================
def create_md_download(content: str, filename: str = "training_plan.md") -> bytes:
    """Markdownファイルをダウンロード用バイトに変換（UTF-8 BOM付き）"""
    # UTF-8 BOM付きでエンコード（iPhoneでの文字化け対策）
    bom = b'\xef\xbb\xbf'
    content_bytes = content.encode('utf-8')
    return bom + content_bytes


# =============================================
# セッション状態の初期化
# =============================================
def init_session_state():
    """セッション状態を初期化"""
    if "form_submitted" not in st.session_state:
        st.session_state.form_submitted = False
    if "user_data" not in st.session_state:
        st.session_state.user_data = {}
    if "calculated_vdot" not in st.session_state:
        st.session_state.calculated_vdot = None
    if "target_vdot" not in st.session_state:
        st.session_state.target_vdot = None
    if "training_paces" not in st.session_state:
        st.session_state.training_paces = None
    if "training_plan" not in st.session_state:
        st.session_state.training_plan = None
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False


# =============================================
# メイン UI
# =============================================
def main():
    init_session_state()
    
    # ヘッダー
    st.markdown(f'<h1 class="main-header">🏃 {APP_NAME}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="version-tag">Version {APP_VERSION}</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">ジャック・ダニエルズのVDOT理論に基づく、あなただけのトレーニング計画</p>', unsafe_allow_html=True)
    
    # データ読み込み
    df_vdot, df_pace, verification_log = load_csv_data()
    
    if not verification_log["success"]:
        st.error("CSVデータの読み込みに失敗しました。")
        for error in verification_log["errors"]:
            st.error(error)
        return
    
    st.session_state.data_loaded = True
    st.session_state.df_vdot = df_vdot
    st.session_state.df_pace = df_pace
    
    # API Key確認
    if not st.secrets.get("GEMINI_API_KEY", ""):
        st.error("⚠️ Gemini API Keyが設定されていません。Streamlit CloudのSecretsで設定してください。")
        return
    
    # メインコンテンツ
    if not st.session_state.form_submitted:
        # ================== 入力フォーム ==================
        st.markdown("### 📝 あなたの情報を入力してください")
        
        with st.form("user_info_form"):
            # 基本情報
            st.markdown('<div class="form-section-title">👤 基本情報</div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.text_input("ニックネーム", placeholder="例: あきら")
            with col2:
                age = st.number_input("年齢", min_value=10, max_value=100, value=40)
            with col3:
                gender = st.selectbox("性別", ["男性", "女性", "その他"])
            
            st.markdown("---")
            
            # タイム情報
            st.markdown('<div class="form-section-title">⏱ タイム情報</div>', unsafe_allow_html=True)
            
            # ベストタイム（セレクトボックス）
            st.markdown("**現在のベストタイム（フルマラソン）**")
            col1, col2, col3 = st.columns(3)
            with col1:
                current_h = st.selectbox("時間", list(range(2, 7)), index=1, key="current_h")
            with col2:
                current_m = st.selectbox("分", list(range(0, 60)), index=30, key="current_m")
            with col3:
                current_s = st.selectbox("秒", list(range(0, 60)), index=0, key="current_s")
            
            # 目標タイム（セレクトボックス）
            st.markdown("**目標タイム（フルマラソン）**")
            col1, col2, col3 = st.columns(3)
            with col1:
                target_h = st.selectbox("時間", list(range(2, 7)), index=1, key="target_h")
            with col2:
                target_m = st.selectbox("分", list(range(0, 60)), index=15, key="target_m")
            with col3:
                target_s = st.selectbox("秒", list(range(0, 60)), index=0, key="target_s")
            
            st.markdown("---")
            
            # レース情報
            st.markdown('<div class="form-section-title">🏁 レース情報</div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                race_name = st.text_input("本番レース名", placeholder="例: 東京マラソン")
                race_date = st.date_input("本番レース日", value=datetime.now() + timedelta(days=90))
            with col2:
                practice_races = st.text_area("練習レース（任意）", placeholder="例: 1/11 NYハーフ\n1/18 赤羽ハーフ", height=100)
            
            st.markdown("---")
            
            # 練習情報
            st.markdown('<div class="form-section-title">🏃‍♂️ 練習情報</div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                weekly_distance = st.text_input("週間走行距離（km）", placeholder="例: 50-60")
            with col2:
                training_days = st.selectbox("練習可能日数/週", [3, 4, 5, 6, 7], index=3)
            with col3:
                point_training_days = st.selectbox("ポイント練習回数/週", [1, 2, 3], index=1)
            
            concerns = st.text_area(
                "怪我や懸念事項（任意）", 
                placeholder="例: 右膝に違和感がある、2/5は練習できない、土日セット練希望",
                height=80
            )
            
            st.markdown("---")
            
            # 送信ボタン
            submitted = st.form_submit_button("🚀 トレーニング計画を作成", use_container_width=True, type="primary")
            
            if submitted:
                # バリデーション
                errors = []
                if not name:
                    errors.append("ニックネームを入力してください")
                if not race_name:
                    errors.append("本番レース名を入力してください")
                
                # タイムを秒に変換
                current_seconds = current_h * 3600 + current_m * 60 + current_s
                target_seconds = target_h * 3600 + target_m * 60 + target_s
                
                # タイム文字列を生成
                current_time = f"{current_h}:{current_m:02d}:{current_s:02d}"
                target_time = f"{target_h}:{target_m:02d}:{target_s:02d}"
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    # データ保存
                    st.session_state.user_data = {
                        "name": name,
                        "age": age,
                        "gender": gender,
                        "current_time": current_time,
                        "target_time": target_time,
                        "race_name": race_name,
                        "race_date": race_date.strftime("%Y-%m-%d"),
                        "practice_races": practice_races,
                        "weekly_distance": weekly_distance,
                        "training_days": training_days,
                        "point_training_days": point_training_days,
                        "concerns": concerns
                    }
                    
                    # VDOT計算
                    vdot_result = calculate_vdot_from_time(df_vdot, "フルマラソン", current_seconds)
                    st.session_state.calculated_vdot = vdot_result
                    
                    if vdot_result["vdot"]:
                        pace_result = calculate_training_paces(df_pace, vdot_result["vdot"])
                        st.session_state.training_paces = pace_result
                    
                    # 目標VDOT計算
                    target_vdot_result = calculate_vdot_from_time(df_vdot, "フルマラソン", target_seconds)
                    st.session_state.target_vdot = target_vdot_result
                    
                    st.session_state.form_submitted = True
                    st.rerun()
    
    else:
        # ================== 結果表示 ==================
        user_data = st.session_state.user_data
        vdot_info = st.session_state.calculated_vdot
        pace_info = st.session_state.training_paces
        target_vdot = st.session_state.target_vdot
        paces = pace_info.get("paces", {}) if pace_info else {}
        
        # VDOT情報表示
        target_vdot_display = ""
        if target_vdot and target_vdot.get("vdot"):
            target_vdot_display = f'<span style="margin-left: 2rem;">🎯 目標VDOT: <strong>{target_vdot["vdot"]}</strong></span>'
        
        st.markdown(f"""
<div class="vdot-display">
    <h3 style="margin: 0 0 1rem 0; color: white;">📊 {user_data.get('name', '')}さんのVDOT計算結果</h3>
    <div style="font-size: 1.3rem; margin-bottom: 1rem;">
        🏃 現在のVDOT: <strong>{vdot_info['vdot']}</strong>{target_vdot_display}
    </div>
    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.5rem; text-align: center;">
        <div style="background: rgba(255,255,255,0.2); padding: 0.5rem; border-radius: 8px;">
            <div style="font-size: 0.8rem;">E (Easy)</div>
            <div style="font-weight: bold;">{paces.get('E', {}).get('display', 'N/A')}/km</div>
        </div>
        <div style="background: rgba(255,255,255,0.2); padding: 0.5rem; border-radius: 8px;">
            <div style="font-size: 0.8rem;">M (Marathon)</div>
            <div style="font-weight: bold;">{paces.get('M', {}).get('display', 'N/A')}/km</div>
        </div>
        <div style="background: rgba(255,255,255,0.2); padding: 0.5rem; border-radius: 8px;">
            <div style="font-size: 0.8rem;">T (Threshold)</div>
            <div style="font-weight: bold;">{paces.get('T', {}).get('display', 'N/A')}/km</div>
        </div>
        <div style="background: rgba(255,255,255,0.2); padding: 0.5rem; border-radius: 8px;">
            <div style="font-size: 0.8rem;">I (Interval)</div>
            <div style="font-weight: bold;">{paces.get('I', {}).get('display', 'N/A')}/km</div>
        </div>
        <div style="background: rgba(255,255,255,0.2); padding: 0.5rem; border-radius: 8px;">
            <div style="font-size: 0.8rem;">R (Repetition)</div>
            <div style="font-weight: bold;">{paces.get('R', {}).get('display', 'N/A')}/km</div>
        </div>
    </div>
</div>
        """, unsafe_allow_html=True)
        
        with st.expander("📐 VDOT計算過程を確認"):
            st.code(vdot_info.get("calculation_log", "計算ログなし"))
            if pace_info and pace_info.get("calculation_log"):
                st.code(pace_info.get("calculation_log", ""))
        
        # トレーニング計画生成
        if not st.session_state.training_plan:
            with st.spinner("🏃 トレーニング計画を作成中...（30秒〜1分程度かかります）"):
                try:
                    model = get_gemini_model()
                    if model:
                        prompt = create_training_prompt(
                            user_data, vdot_info, pace_info, target_vdot, df_pace
                        )
                        response = model.generate_content(prompt)
                        st.session_state.training_plan = response.text
                except Exception as e:
                    st.error(f"APIエラーが発生しました: {str(e)}")
                    st.session_state.training_plan = None
        
        # トレーニング計画表示
        if st.session_state.training_plan:
            st.markdown("---")
            st.markdown(st.session_state.training_plan)
            
            # ダウンロードボタン
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                # MDダウンロード
                md_content = st.session_state.training_plan
                md_bytes = create_md_download(md_content)
                filename = f"training_plan_{user_data.get('name', 'user')}_{datetime.now().strftime('%Y%m%d')}.md"
                
                st.download_button(
                    label="📥 MDファイルをダウンロード",
                    data=md_bytes,
                    file_name=filename,
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col2:
                if st.button("🔄 計画を再生成", use_container_width=True):
                    st.session_state.training_plan = None
                    st.rerun()
            
            with col3:
                if st.button("📝 入力からやり直す", use_container_width=True):
                    st.session_state.form_submitted = False
                    st.session_state.training_plan = None
                    st.rerun()
        
        # フッター
        st.markdown("---")
        st.caption(f"{APP_NAME} v{APP_VERSION} | © 2024 VDOT Training System")


if __name__ == "__main__":
    main()
