"""
AIマラソンコーチ - Streamlit App
ジャック・ダニエルズのVDOT理論に基づくトレーニング計画生成

Version: 1.0.0
"""

import streamlit as st
import time
from datetime import datetime, timedelta

# ローカルモジュール
from src.config import (
    APP_NAME, APP_VERSION, MIN_TRAINING_WEEKS,
    get_max_vdot_diff, validate_training_conditions,
    get_max_output_tokens,
    GEMINI_AVAILABLE_MODELS, GEMINI_DEFAULT_MODEL,
)
from src.data_loader import load_csv_data
from src.vdot import (
    calculate_vdot_from_time,
    calculate_training_paces,
    calculate_marathon_time_from_vdot,
    get_training_start_date,
)
from src.ai import GeminiClient, create_training_prompt
from src.ai.gemini_client import sanitize_gemini_output, create_md_download
from src.ui import load_css, render_vdot_display, render_phase_table
from src.ui.components import (
    render_header,
    render_footer,
    render_vdot_explanation,
    render_warning_box,
)


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
# セッション状態の初期化
# =============================================
def init_session_state():
    """セッション状態を初期化"""
    defaults = {
        "form_submitted": False,
        "user_data": {},
        "calculated_vdot": None,
        "target_vdot": None,
        "training_paces": None,
        "training_plan": None,
        "data_loaded": False,
        "training_weeks": 12,
        "start_date": None,
        "selected_model": GEMINI_DEFAULT_MODEL,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# =============================================
# メイン UI
# =============================================
def main():
    init_session_state()
    
    # CSS読み込み
    load_css()
    
    # ヘッダー
    render_header()
    
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
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("⚠️ Gemini API Keyが設定されていません。.streamlit/secrets.tomlで設定してください。")
        return
    
    # メインコンテンツ
    if not st.session_state.form_submitted:
        render_input_form(df_vdot, df_pace)
    else:
        render_result_page(df_vdot, df_pace, api_key)
    
    # フッター
    render_footer()


def render_input_form(df_vdot, df_pace):
    """入力フォームを表示"""
    
    # URLパラメータから初期値を取得（AMC連携）
    # ?best_h=4&best_m=0&best_s=0&target_h=3&target_m=30&target_s=0
    query_params = st.query_params
    
    # デバッグ用：パラメータ表示（本番では削除またはコメントアウト）
    # with st.expander("Debug: URL Parameters"):
    #     st.write(query_params)

    def get_param(key, default):
        try:
            val = query_params.get(key)
            if val is None:
                return default
            # リスト（古いバージョンや複数指定）の場合の対応
            if isinstance(val, list):
                val = val[0]
            return int(val)
        except (ValueError, TypeError):
            return default

    # デフォルト設定（パラメータがない場合はこの値）
    default_best_h = get_param("best_h", 4)
    default_best_m = get_param("best_m", 0)
    default_best_s = get_param("best_s", 0)
    
    default_target_h = get_param("target_h", 3)
    default_target_m = get_param("target_m", 30)
    default_target_s = get_param("target_s", 0)
    
    # 3ステップフロー（ファーストビュー改善）
    st.markdown("""
<div style="display: flex; justify-content: center; gap: clamp(0.3rem, 1vw, 0.8rem); flex-wrap: nowrap; margin: 1rem 0 1.5rem 0;">
    <div style="background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%); padding: clamp(0.5rem, 1.5vw, 1rem) clamp(0.6rem, 2vw, 1.5rem); border-radius: 10px; text-align: center; min-width: 70px; flex: 1; max-width: 150px; box-shadow: 0 3px 8px rgba(0,0,0,0.15);">
        <div style="font-size: clamp(1.2rem, 3vw, 2rem);">📝</div>
        <div style="font-weight: bold; color: white; font-size: clamp(0.9rem, 2vw, 1.2rem); margin: 0.3rem 0;">STEP 1</div>
        <div style="font-size: clamp(0.8rem, 1.5vw, 1rem); color: rgba(255,255,255,0.9);">情報を入力</div>
    </div>
    <div style="display: flex; align-items: center; color: #1E88E5; font-size: clamp(1.6rem, 3vw, 2.5rem);">→</div>
    <div style="background: linear-gradient(135deg, #43A047 0%, #2E7D32 100%); padding: clamp(0.5rem, 1.5vw, 1rem) clamp(0.6rem, 2vw, 1.5rem); border-radius: 10px; text-align: center; min-width: 70px; flex: 1; max-width: 150px; box-shadow: 0 3px 8px rgba(0,0,0,0.15);">
        <div style="font-size: clamp(1.2rem, 3vw, 2rem);">🤖</div>
        <div style="font-weight: bold; color: white; font-size: clamp(0.9rem, 2vw, 1.2rem); margin: 0.3rem 0;">STEP 2</div>
        <div style="font-size: clamp(0.8rem, 1.5vw, 1rem); color: rgba(255,255,255,0.9);">AIが分析</div>
    </div>
    <div style="display: flex; align-items: center; color: #43A047; font-size: clamp(1.6rem, 3vw, 2.5rem);">→</div>
    <div style="background: linear-gradient(135deg, #FB8C00 0%, #EF6C00 100%); padding: clamp(0.5rem, 1.5vw, 1rem) clamp(0.6rem, 2vw, 1.5rem); border-radius: 10px; text-align: center; min-width: 70px; flex: 1; max-width: 150px; box-shadow: 0 3px 8px rgba(0,0,0,0.15);">
        <div style="font-size: clamp(1.2rem, 3vw, 2rem);">📋</div>
        <div style="font-weight: bold; color: white; font-size: clamp(0.9rem, 2vw, 1.2rem); margin: 0.3rem 0;">STEP 3</div>
        <div style="font-size: clamp(0.8rem, 1.5vw, 1rem); color: rgba(255,255,255,0.9);">計画を取得！</div>
    </div>
</div>
    """, unsafe_allow_html=True)
    

    
    # ユーザーマニュアル・利用規約
    with st.expander("📖 使い方・用語説明・利用規約", expanded=False):
        st.markdown("""
### 🚀 使い方
1. 基礎走力（現在と目標のマラソンタイム）を入力
2. トレーニング条件（週間距離、練習日数）を入力
3. 目標レース情報を入力
4. 「トレーニング計画を生成」ボタンをクリック

---

### 💡 用語説明

#### VDOT
ジャック・ダニエルズ博士が考案した走力指標。マラソンタイムから算出されます。

#### ペースの種類
| 記号 | 名称 | 説明 |
|:-----|:-----|:-----|
| E | Easy | ゆっくりジョグ。会話できるペース |
| M | Marathon | マラソンレースペース |
| T | Threshold | 閾値ペース。1時間維持できる強度 |
| I | Interval | インターバル走のペース |
| R | Repetition | 短距離の全力に近いペース |

#### 練習スタイル
| 用語 | 説明 |
|:-----|:-----|
| 2部練 | Eペースジョグを午前と午後に分ける |
| セット練 | 土日連続でポイント練習 |
| ダブルスレッショルド | 午前と午後に閾値走（要望時のみ） |

---

### ⚙️ 自動調整機能

- **VDOT差の調整**: 目標が高すぎる場合、中間目標が自動設定されます
- **トレーニング条件の調整**: 最低条件を満たさない場合、自動で調整されます

---

### 📜 利用規約・注意事項

1. 本サービスはAIによるトレーニング計画の参考情報を提供するものであり、医療・運動指導の専門家によるアドバイスに代わるものではありません。
2. 生成されるトレーニング計画の正確性・安全性を保証するものではありません。実施にあたっては、ご自身の体調や健康状態を考慮し、**自己責任**で行ってください。
3. 怪我、体調不良、その他いかなる損害が生じた場合も、運営者は一切の責任を負いません。
4. 持病のある方、健康に不安のある方は、事前に医師や専門家にご相談ください。
5. 入力された情報はトレーニング計画の生成にのみ使用され、保存・収集されません。
6. **ご利用のお願い**: 本サービスはAPI利用料の関係で、1日の生成回数に制限があります。より多くの方にご利用いただくため、**お一人様1日1回の利用**にご協力ください。
        """)
    
    st.markdown('<h3 class="form-heading">📝 情報を入力してください</h3>', unsafe_allow_html=True)
    
    with st.form("user_info_form"):
        # 基本情報
        st.markdown('<div class="form-section-title">👤 基本情報</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('ニックネーム <span style="background-color: #E53935; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 4px;">必須</span>', unsafe_allow_html=True)
            name = st.text_input("ニックネーム", placeholder="例: 太郎", label_visibility="collapsed")
        with col2:
            age = st.number_input("年齢", min_value=10, max_value=100, value=40)
        with col3:
            gender = st.selectbox("性別", ["男性", "女性", "その他"])
        
        st.markdown("---")
        
        # タイム情報
        st.markdown('<div class="form-section-title">⏱ タイム情報</div>', unsafe_allow_html=True)
        
        st.markdown("**現在のベストタイム（フルマラソン）**")
        col1, col2, col3 = st.columns(3)
        with col1:
            current_h = st.number_input("時間", min_value=2, max_value=6, value=default_best_h, step=1, key="current_h")
        with col2:
            current_m = st.number_input("分", min_value=0, max_value=59, value=default_best_m, step=1, key="current_m")
        with col3:
            current_s = st.number_input("秒", min_value=0, max_value=59, value=default_best_s, step=1, key="current_s")
        
        st.markdown("**目標タイム（フルマラソン）**")
        col1, col2, col3 = st.columns(3)
        with col1:
            target_h = st.number_input("時間", min_value=2, max_value=6, value=default_target_h, step=1, key="target_h")
        with col2:
            target_m = st.number_input("分", min_value=0, max_value=59, value=default_target_m, step=1, key="target_m")
        with col3:
            target_s = st.number_input("秒", min_value=0, max_value=59, value=default_target_s, step=1, key="target_s")
        
        st.markdown("---")
        
        # レース情報
        st.markdown('<div class="form-section-title">🏁 レース情報</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('本番レース名 <span style="background-color: #E53935; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 4px;">必須</span>', unsafe_allow_html=True)
            race_name = st.text_input("本番レース名", placeholder="例: 東京マラソン", label_visibility="collapsed")
            race_date = st.date_input("本番レース日", value=datetime.now() + timedelta(days=90))
        with col2:
            st.markdown('練習レース <span style="background-color: #1976D2; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 4px;">任意</span>', unsafe_allow_html=True)
            practice_races = st.text_area("練習レース", placeholder="例: 1/11 NYハーフ\n1/18 赤羽ハーフ", height=100, label_visibility="collapsed")
        
        st.markdown("---")
        
        # 練習情報
        st.markdown('<div class="form-section-title">🏃‍♂️ 練習情報</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            weekly_distance = st.number_input("週間走行距離（km）", min_value=10, max_value=250, value=60, step=5)
        with col2:
            training_days = st.selectbox("練習可能日数/週", [1, 2, 3, 4, 5, 6, 7], index=5)
        with col3:
            max_point_days = min(training_days, 4)
            point_options = list(range(1, max_point_days + 1))
            default_index = min(1, len(point_options) - 1)
            point_training_days = st.selectbox("ポイント練習回数/週", point_options, index=default_index)
        
        st.markdown('AIコーチへの連絡事項 <span style="background-color: #1976D2; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 4px;">任意</span>', unsafe_allow_html=True)
        concerns = st.text_area(
            "AIコーチへの連絡事項", 
            placeholder="例: 右膝に違和感がある、2/5は練習できない、土日セット練希望",
            height=80,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # AIモデル選択
        # AIモデル選択（開発者オプション: URLに ?dev=1 を指定した場合のみ表示）
        is_dev_mode = query_params.get("dev") == "1"
        if is_dev_mode:
            st.markdown('<div class="form-section-title">🤖 AIモデル選択（開発者オプション）</div>', unsafe_allow_html=True)
            model_options = list(GEMINI_AVAILABLE_MODELS.keys())
            model_labels = list(GEMINI_AVAILABLE_MODELS.values())
            default_idx = model_options.index(GEMINI_DEFAULT_MODEL)
            selected_model_label = st.selectbox(
                "使用するAIモデル",
                model_labels,
                index=default_idx,
                help="Gemini 3 Flash: 高精度な計画生成 / Gemini 3.1 Flash Lite: 高速・軽量な計画生成"
            )
            selected_model = model_options[model_labels.index(selected_model_label)]
            st.markdown("---")
        else:
            selected_model = GEMINI_DEFAULT_MODEL
        
        # 送信ボタン
        submitted = st.form_submit_button("🚀 トレーニング計画を作成", use_container_width=True, type="primary")
        
        if submitted:
            st.session_state.selected_model = selected_model
            process_form_submission(
                name, age, gender, current_h, current_m, current_s,
                target_h, target_m, target_s, race_name, race_date,
                practice_races, weekly_distance, training_days,
                point_training_days, concerns, df_vdot, df_pace
            )


def process_form_submission(name, age, gender, current_h, current_m, current_s,
                           target_h, target_m, target_s, race_name, race_date,
                           practice_races, weekly_distance, training_days,
                           point_training_days, concerns, df_vdot, df_pace):
    """フォーム送信を処理"""
    # バリデーション
    errors = []
    if not name:
        errors.append("ニックネームを入力してください")
    if not race_name:
        errors.append("本番レース名を入力してください")
    
    if errors:
        st.toast("必須項目が未入力です", icon="⚠️")
        for error in errors:
            st.error(f"❌ {error}")
        return
    
    # タイムを秒に変換
    current_seconds = current_h * 3600 + current_m * 60 + current_s
    target_seconds = target_h * 3600 + target_m * 60 + target_s
    
    current_time = f"{current_h}:{current_m:02d}:{current_s:02d}"
    target_time = f"{target_h}:{target_m:02d}:{target_s:02d}"
    
    # VDOT計算
    vdot_result = calculate_vdot_from_time(df_vdot, "フルマラソン", current_seconds)
    target_vdot_result = calculate_vdot_from_time(df_vdot, "フルマラソン", target_seconds)
    
    if not vdot_result["vdot"] or not target_vdot_result["vdot"]:
        st.error("VDOT計算に失敗しました")
        return
    
    vdot_diff = target_vdot_result["vdot"] - vdot_result["vdot"]
    
    # トレーニング期間の計算（VDOT差判定に必要なため先に計算）
    race_dt = datetime.combine(race_date, datetime.min.time())
    today = datetime.now()
    days_until_race = (race_dt - today).days
    actual_weeks = days_until_race // 7
    
    # 12週未満の場合はレース日から逆算して12週前を開始日に設定
    # 12週以上の場合は今日から開始
    if actual_weeks < MIN_TRAINING_WEEKS:
        # レース日から12週前の月曜日を計算
        start_date = race_dt - timedelta(weeks=MIN_TRAINING_WEEKS)
        # 月曜日に調整（その週の月曜日）
        days_since_monday = start_date.weekday()
        start_date = start_date - timedelta(days=days_since_monday)
        # 月曜調整後の実際の週数を再計算（端数は切り上げて1週間とする）
        actual_days = (race_dt - start_date).days
        training_weeks = (actual_days + 6) // 7
    else:
        training_weeks = actual_weeks
        # 開始日は今日の次の月曜日（または今日が月曜なら今日）
        if today.weekday() == 0:
            start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            days_until_monday = 7 - today.weekday()
            start_date = today + timedelta(days=days_until_monday)
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 現在のVDOTとトレーニング期間に応じた許容VDOT差を取得
    max_vdot_diff = get_max_vdot_diff(vdot_result["vdot"], training_weeks)
    
    # VDOT差が大きい場合の調整
    original_target_vdot = target_vdot_result["vdot"]
    adjusted_target_vdot = None
    if vdot_diff > max_vdot_diff:
        adjusted_target_vdot = round(vdot_result["vdot"] + max_vdot_diff, 2)
    
    # トレーニング条件の判定
    training_validation = validate_training_conditions(
        target_vdot_result["vdot"], 
        weekly_distance, 
        training_days, 
        point_training_days
    )
    
    # 最低条件を満たさない場合、自動調整
    effective_weekly_distance = weekly_distance
    effective_training_days = training_days
    effective_point_training_days = point_training_days
    
    if not training_validation['is_valid']:
        effective_weekly_distance = max(weekly_distance, training_validation['min_distance'])
        effective_training_days = max(training_days, training_validation['min_days'])
        effective_point_training_days = max(point_training_days, training_validation['min_point'])
    
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
        "weekly_distance": effective_weekly_distance,  # 調整済み
        "training_days": effective_training_days,      # 調整済み
        "point_training_days": effective_point_training_days,  # 調整済み
        "original_weekly_distance": weekly_distance,   # 元の入力
        "original_training_days": training_days,       # 元の入力
        "original_point_training_days": point_training_days,  # 元の入力
        "concerns": concerns,
        "vdot_diff": round(vdot_diff, 2),
        "max_vdot_diff": max_vdot_diff,
        "original_target_vdot": original_target_vdot,
        "adjusted_target_vdot": adjusted_target_vdot,
        "training_validation": training_validation
    }
    
    st.session_state.calculated_vdot = vdot_result
    st.session_state.target_vdot = target_vdot_result
    
    if vdot_result["vdot"]:
        pace_result = calculate_training_paces(df_pace, vdot_result["vdot"])
        st.session_state.training_paces = pace_result
    
    st.session_state.training_weeks = training_weeks
    st.session_state.start_date = start_date
    st.session_state.form_submitted = True
    st.rerun()


def render_result_page(df_vdot, df_pace, api_key):
    """結果ページを表示"""
    user_data = st.session_state.user_data
    vdot_info = st.session_state.calculated_vdot
    pace_info = st.session_state.training_paces
    target_vdot = st.session_state.target_vdot
    paces = pace_info.get("paces", {}) if pace_info else {}
    vdot_diff = user_data.get("vdot_diff", 0)
    training_weeks = st.session_state.training_weeks
    start_date = st.session_state.start_date
    
    # ユーザー入力情報の表示
    with st.expander("📝 入力内容を確認", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
**基本情報**
- ニックネーム: {user_data.get('name', '-')}
- 年齢: {user_data.get('age', '-')}歳
- 性別: {user_data.get('gender', '-')}
            """)
            st.markdown(f"""
**トレーニング条件**
- 週間走行距離: {user_data.get('weekly_distance', '-')}km
- 練習可能日数: {user_data.get('training_days', '-')}日/週
- ポイント練習: {user_data.get('point_training_days', '-')}回/週
            """)
        with col2:
            st.markdown(f"""
**目標設定**
- 現在のタイム: {user_data.get('current_time', '-')}
- 目標タイム: {user_data.get('target_time', '-')}
- 本番レース: {user_data.get('race_name', '-')}
- レース日: {user_data.get('race_date', '-')}
            """)
            if user_data.get('practice_races'):
                st.markdown(f"""
**練習レース**
{user_data.get('practice_races', 'なし')}
                """)
        if user_data.get('concerns'):
            st.markdown(f"""
**その他要望・相談事項**
{user_data.get('concerns', 'なし')}
            """)
    
    # VDOT表示
    render_vdot_display(
        user_data.get('name', ''),
        vdot_info,
        target_vdot,
        paces,
        vdot_diff
    )
    
    # 調整済み目標VDOTの取得
    adjusted_target_vdot = user_data.get("adjusted_target_vdot")
    original_target_vdot = user_data.get("original_target_vdot")
    max_vdot_diff = user_data.get("max_vdot_diff", 3.0)
    effective_target_vdot = adjusted_target_vdot if adjusted_target_vdot else target_vdot['vdot']
    
    # トレーニング条件の警告と自動調整
    training_validation = user_data.get("training_validation", {})
    if training_validation and not training_validation.get('is_valid', True):
        original_distance = user_data.get("original_weekly_distance", user_data.get("weekly_distance"))
        original_days = user_data.get("original_training_days", user_data.get("training_days"))
        original_point = user_data.get("original_point_training_days", user_data.get("point_training_days"))
        
        adjustments = []
        if original_distance < training_validation['min_distance']:
            adjustments.append(f"週間走行距離: {original_distance}km → <strong>{training_validation['min_distance']}km</strong>")
        if original_days < training_validation['min_days']:
            adjustments.append(f"練習日数: {original_days}日 → <strong>{training_validation['min_days']}日</strong>")
        if original_point < training_validation['min_point']:
            adjustments.append(f"ポイント練習: {original_point}回 → <strong>{training_validation['min_point']}回</strong>")
        
        adjustments_html = "".join([f"<li>{a}</li>" for a in adjustments])
        st.markdown(f"""
<div class="warning-box">
    <h4>⚠️ トレーニング条件の自動調整</h4>
    <p>目標タイム達成に必要な最低条件を満たしていないため、以下のように自動調整してトレーニング計画を生成します：</p>
    <ul>
        {adjustments_html}
    </ul>
    <p>入力された条件と異なりますが、目標達成に必要な練習量です。現在の条件で難しい場合は、目標タイムの見直しをご検討ください。</p>
</div>
        """, unsafe_allow_html=True)
    
    # VDOT差チェックと警告/確認
    if vdot_diff > max_vdot_diff and adjusted_target_vdot:
        adjusted_marathon_time = calculate_marathon_time_from_vdot(df_vdot, adjusted_target_vdot)
        # user_dataに中間目標マラソンタイムを保存（Markdown変換で使用）
        user_data['adjusted_marathon_time'] = adjusted_marathon_time
        st.markdown(f"""
<div class="warning-box">
    <h4>⚠️ 目標タイムについての重要なお知らせ</h4>
    <p>現在のVDOT（{vdot_info['vdot']}）と入力された目標VDOT（{original_target_vdot}）の差が<strong>{vdot_diff}</strong>あります。</p>
    <p>現在の走力レベルでは、VDOT差<strong>{max_vdot_diff}</strong>までが1サイクルで達成可能な目安です。</p>
    <h4>📊 今回のトレーニング計画について</h4>
    <p>そこで、今回のトレーニング計画では<strong>中間目標</strong>を設定します：</p>
    <ul>
        <li><strong>中間目標VDOT:</strong> {adjusted_target_vdot}（VDOT差 {max_vdot_diff}）</li>
        <li><strong>中間目標マラソンタイム:</strong> {adjusted_marathon_time}</li>
    </ul>
    <p>この中間目標を達成した後、次のトレーニングサイクルで最終目標（VDOT {original_target_vdot} / {user_data.get('target_time', '')}）を目指すことをお勧めします。</p>
    <p><strong>段階的なアプローチ</strong>により、怪我のリスクを減らし、着実にタイムを縮めていくことができます。</p>
</div>
        """, unsafe_allow_html=True)
    else:
        # 目標設定が適切な場合
        st.markdown(f"""
<div class="success-box">
    <h4>✅ 目標設定は適切です</h4>
    <p>VDOT差 <strong>{vdot_diff}</strong> は、{training_weeks}週間のトレーニングで十分達成可能な範囲です。</p>
</div>
        """, unsafe_allow_html=True)
    
    # トレーニング期間の警告（12週未満の場合のみ）
    today = datetime.now()
    days_until_race = (datetime.strptime(user_data.get("race_date", ""), "%Y-%m-%d") - today).days
    weeks_until_race = days_until_race // 7
    
    if weeks_until_race < MIN_TRAINING_WEEKS:
        st.markdown(f"""
<div class="warning-box">
    <h4>📅 トレーニング期間について</h4>
    <p>レース日までの期間が<strong>{weeks_until_race}週間</strong>と、推奨される最低{MIN_TRAINING_WEEKS}週間に満たないため、{MIN_TRAINING_WEEKS}週間のトレーニング計画を生成しました。</p>
    <p>計画上の開始日は<strong>{start_date.strftime('%Y/%m/%d')}（過去の日付）</strong>になっています。</p>
    <p>実際には<strong>本日から計画を参考に</strong>して、残りの{weeks_until_race}週間でできる限りのトレーニングを行ってください。過去の週のメニューは飛ばして、現在の週から始めてください。</p>
</div>
        """, unsafe_allow_html=True)

    
    # VDOT解説
    render_vdot_explanation()
    
    # 計算過程
    with st.expander("📐 VDOT計算過程を確認"):
        st.code(vdot_info.get("calculation_log", "計算ログなし"))
        if pace_info and pace_info.get("calculation_log"):
            st.code(pace_info.get("calculation_log", ""))
    
    # フェーズテーブル
    render_phase_table(vdot_info['vdot'], effective_target_vdot, training_weeks)
    
    # トレーニング計画生成
    if not st.session_state.training_plan:
        st.toast("🏃 トレーニング計画を作成中です。1〜2分お待ちください...", icon="🏃")
        
        # 待ち時間コンテンツ（スピナーの下に表示）
        st.markdown("""
<div style="
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid rgba(0, 229, 255, 0.2);
    border-radius: 16px;
    padding: 1.5rem;
    margin: 1.5rem 0;
">
    <p style="color: #00E5FF; font-size: 1.1rem; font-weight: bold; margin-bottom: 1rem; text-align: center;">
        📖 計画ができるまで、こちらの記事はいかがですか？
    </p>
    <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
        <a href="https://akirun.net/polar-verity-sense-review/" target="_blank" style="
            flex: 1; min-width: 250px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 1rem;
            text-decoration: none;
            transition: background 0.2s;
        ">
            <p style="font-size: 1.3rem; margin-bottom: 0.3rem;">⌚</p>
            <p style="color: #E2E8F0; font-size: 0.95rem; font-weight: bold; margin-bottom: 0.3rem;">
                Eペースを心拍で管理する方法
            </p>
            <p style="color: #94A3B8; font-size: 0.8rem; margin: 0;">
                アームバンド型心拍計で心肺機能の成長を高精度に測定 →
            </p>
        </a>
        <a href="https://akirun.net/marathon-gear-recommend/" target="_blank" style="
            flex: 1; min-width: 250px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 1rem;
            text-decoration: none;
            transition: background 0.2s;
        ">
            <p style="font-size: 1.3rem; margin-bottom: 0.3rem;">👟</p>
            <p style="color: #E2E8F0; font-size: 0.95rem; font-weight: bold; margin-bottom: 0.3rem;">
                マラソンおすすめギア総まとめ
            </p>
            <p style="color: #94A3B8; font-size: 0.8rem; margin: 0;">
                シューズ・ウェア・補給を科学的根拠で厳選 →
            </p>
        </a>
    </div>
</div>
        """, unsafe_allow_html=True)
        
        with st.spinner("🏃 トレーニング計画を作成中...（1〜2分程度かかります）"):
            try:
                selected_model = st.session_state.get('selected_model', GEMINI_DEFAULT_MODEL)
                client = GeminiClient(api_key, model_name=selected_model)
                effective_target_vdot_for_prompt = {"vdot": effective_target_vdot}
                prompt = create_training_prompt(
                    user_data, vdot_info, pace_info, effective_target_vdot_for_prompt,
                    df_pace, training_weeks, start_date, df_vdot
                )
                
                # 週数に応じた出力トークン数を計算
                max_tokens = get_max_output_tokens(training_weeks)
                
                # 自動リトライ機構（最大2回リトライ＝計3回試行）
                MAX_RETRIES = 2
                for attempt in range(MAX_RETRIES + 1):
                    try:
                        response = client.generate_content(prompt, max_output_tokens=max_tokens)
                        if response:
                            # JSONからMarkdownへの変換
                            from src.ai.gemini_client import convert_json_to_markdown
                            markdown_plan = convert_json_to_markdown(response, user_data=user_data)
                            
                            # 週数チェック（警告のみ、ブロックはしない）
                            import json
                            try:
                                json_data = json.loads(response.strip().lstrip('```json').lstrip('```').rstrip('```'))
                                plan_data = json_data.get('plan', json_data) if isinstance(json_data, dict) else json_data
                                if isinstance(plan_data, dict):
                                    actual_weeks = len(plan_data.get('weekly_schedules', []))
                                    if actual_weeks < training_weeks:
                                        st.warning(f"⚠️ AIが{training_weeks}週中{actual_weeks}週分しか出力できませんでした。再度お試しください。")
                            except (json.JSONDecodeError, AttributeError):
                                pass  # JSONパース失敗時はチェックをスキップ
                            
                            st.session_state.training_plan = markdown_plan
                            break
                        else:
                            # 応答が空の場合
                            if attempt < MAX_RETRIES:
                                wait_time = 2 ** (attempt + 1)  # 2s, 4s（指数バックオフ）
                                time.sleep(wait_time)
                                continue
                            else:
                                st.error("⚠️ AIからの応答が空でした。混雑している可能性があります。時間をおいて再試行してください。")
                                st.session_state.training_plan = None
                    except Exception as e:
                        # APIエラー発生時
                        if attempt < MAX_RETRIES:
                            wait_time = 2 ** (attempt + 1)  # 2s, 4s（指数バックオフ）
                            time.sleep(wait_time)
                            continue
                        else:
                            err_str = str(e)
                            if "503_SERVICE_UNAVAILABLE" in err_str:
                                st.error(f"⚠️ サーバーが混雑しているため応答できませんでした（{MAX_RETRIES+1}回試行）。しばらく待ってから再度お試しください。")
                            elif "429_RATE_LIMITED" in err_str:
                                st.error(f"⚠️ APIのリクエスト上限に達しました（{MAX_RETRIES+1}回試行）。時間をおいてから再度お試しください。")
                            else:
                                st.error(f"APIエラーが発生しました（{MAX_RETRIES+1}回試行）: {err_str}")
                            st.session_state.training_plan = None

            except Exception as e:
                # その他の予期せぬエラー
                st.error(f"処理中にエラーが発生しました: {str(e)}")
                st.session_state.training_plan = None
    
    # トレーニング計画表示
    if st.session_state.training_plan:
        st.markdown("---")
        st.markdown("## 📋 トレーニング計画")
        
        st.markdown(st.session_state.training_plan)
        
        # 計画下部: 2カラムCTA
        col_cta1, col_cta2 = st.columns(2)
        with col_cta1:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #1E3A5F 0%, #0F172A 100%);
                border: 1px solid #00E5FF;
                border-radius: 12px;
                padding: 1.2rem;
                text-align: center;
                height: 100%;
            ">
                <p style="font-size: 1.5rem; margin-bottom: 0.3rem;">⌚</p>
                <p style="color: #00E5FF; font-size: 1rem; font-weight: bold; margin-bottom: 0.5rem;">
                    心拍計の精度で走りが変わる
                </p>
                <p style="color: #94A3B8; font-size: 0.85rem; margin-bottom: 0.8rem;">
                    心肺機能の成長を<br>高精度心拍計で測定
                </p>
                <a href="https://akirun.net/polar-verity-sense-review/" target="_blank" style="
                    display: inline-block;
                    background: linear-gradient(135deg, #00E5FF 0%, #0EA5E9 100%);
                    color: #0F172A;
                    padding: 0.5rem 1.2rem;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: bold;
                    font-size: 0.9rem;
                ">レビューを読む →</a>
            </div>
            """, unsafe_allow_html=True)
        with col_cta2:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #1E3A5F 0%, #0F172A 100%);
                border: 1px solid #00E5FF;
                border-radius: 12px;
                padding: 1.2rem;
                text-align: center;
                height: 100%;
            ">
                <p style="font-size: 1.5rem; margin-bottom: 0.3rem;">👟</p>
                <p style="color: #00E5FF; font-size: 1rem; font-weight: bold; margin-bottom: 0.5rem;">
                    ギア選びで差をつける
                </p>
                <p style="color: #94A3B8; font-size: 0.85rem; margin-bottom: 0.8rem;">
                    練習効率とレース本番のパフォーマンスを<br>最大化する厳選ギア
                </p>
                <a href="https://akirun.net/marathon-gear-recommend/" target="_blank" style="
                    display: inline-block;
                    background: linear-gradient(135deg, #00E5FF 0%, #0EA5E9 100%);
                    color: #0F172A;
                    padding: 0.5rem 1.2rem;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: bold;
                    font-size: 0.9rem;
                ">おすすめギアを見る →</a>
            </div>
            """, unsafe_allow_html=True)
        
        # ダウンロードボタン
        st.markdown("---")
        
        md_content = st.session_state.training_plan
        md_bytes = create_md_download(md_content)
        filename = f"training_plan_{user_data.get('name', 'user')}_{datetime.now().strftime('%Y%m%d')}.md"
        
        st.download_button(
            label="📥 週間トレーニング計画をダウンロード",
            data=md_bytes,
            file_name=filename,
            mime="text/markdown",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
