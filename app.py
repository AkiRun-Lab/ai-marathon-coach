"""
AIマラソンコーチ - Streamlit App
ジャック・ダニエルズのVDOT理論に基づくトレーニング計画生成

Version: 1.0.0
"""

import streamlit as st
from datetime import datetime, timedelta

# ローカルモジュール
from src.config import APP_NAME, APP_VERSION, MAX_VDOT_DIFF_PER_CYCLE, MIN_TRAINING_WEEKS
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
    render_disclaimer,
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
    # お知らせ
    st.warning("""
⚠️ **ご利用にあたってのお願い**

本サービスはAPI利用料の関係で、1日の生成回数に制限があります。
より多くの方にご利用いただくため、**お一人様1日1回の利用**にご協力ください。
""")
    
    # 利用規約
    render_disclaimer()
    
    st.markdown("### 📝 あなたの情報を入力してください")
    
    with st.form("user_info_form"):
        # 基本情報
        st.markdown('<div class="form-section-title">👤 基本情報</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("ニックネーム", placeholder="例: 太郎")
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
            current_h = st.number_input("時間", min_value=2, max_value=6, value=3, step=1, key="current_h")
        with col2:
            current_m = st.number_input("分", min_value=0, max_value=59, value=30, step=1, key="current_m")
        with col3:
            current_s = st.number_input("秒", min_value=0, max_value=59, value=0, step=1, key="current_s")
        
        st.markdown("**目標タイム（フルマラソン）**")
        col1, col2, col3 = st.columns(3)
        with col1:
            target_h = st.number_input("時間", min_value=2, max_value=6, value=3, step=1, key="target_h")
        with col2:
            target_m = st.number_input("分", min_value=0, max_value=59, value=15, step=1, key="target_m")
        with col3:
            target_s = st.number_input("秒", min_value=0, max_value=59, value=0, step=1, key="target_s")
        
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
            training_days = st.selectbox("練習可能日数/週", [1, 2, 3, 4, 5, 6, 7], index=5)
        with col3:
            max_point_days = min(training_days, 4)
            point_options = list(range(1, max_point_days + 1))
            default_index = min(1, len(point_options) - 1)
            point_training_days = st.selectbox("ポイント練習回数/週", point_options, index=default_index)
        
        concerns = st.text_area(
            "AIコーチへの連絡事項（任意）", 
            placeholder="例: 右膝に違和感がある、2/5は練習できない、土日セット練希望",
            height=80
        )
        
        st.markdown("---")
        
        # 送信ボタン
        submitted = st.form_submit_button("🚀 トレーニング計画を作成", use_container_width=True, type="primary")
        
        if submitted:
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
        for error in errors:
            st.error(error)
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
    
    # VDOT差が大きい場合の調整
    original_target_vdot = target_vdot_result["vdot"]
    adjusted_target_vdot = None
    if vdot_diff > MAX_VDOT_DIFF_PER_CYCLE:
        adjusted_target_vdot = round(vdot_result["vdot"] + MAX_VDOT_DIFF_PER_CYCLE, 2)
    
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
        "concerns": concerns,
        "vdot_diff": round(vdot_diff, 2),
        "original_target_vdot": original_target_vdot,
        "adjusted_target_vdot": adjusted_target_vdot
    }
    
    st.session_state.calculated_vdot = vdot_result
    st.session_state.target_vdot = target_vdot_result
    
    if vdot_result["vdot"]:
        pace_result = calculate_training_paces(df_pace, vdot_result["vdot"])
        st.session_state.training_paces = pace_result
    
    # トレーニング期間の計算
    race_dt = datetime.combine(race_date, datetime.min.time())
    today = datetime.now()
    days_until_race = (race_dt - today).days
    actual_weeks = days_until_race // 7
    
    # 12週未満の場合はレース日から逆算して12週前を開始日に設定
    # 12週以上の場合は今日から開始
    if actual_weeks < MIN_TRAINING_WEEKS:
        training_weeks = MIN_TRAINING_WEEKS
        # レース日から12週前の月曜日を計算
        start_date = race_dt - timedelta(weeks=MIN_TRAINING_WEEKS)
        # 月曜日に調整（その週の月曜日）
        days_since_monday = start_date.weekday()
        start_date = start_date - timedelta(days=days_since_monday)
    else:
        training_weeks = actual_weeks
        # 開始日は今日の次の月曜日（または今日が月曜なら今日）
        if today.weekday() == 0:
            start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            days_until_monday = 7 - today.weekday()
            start_date = today + timedelta(days=days_until_monday)
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
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
    effective_target_vdot = adjusted_target_vdot if adjusted_target_vdot else target_vdot['vdot']
    
    # VDOT差チェックと警告/確認
    if vdot_diff > MAX_VDOT_DIFF_PER_CYCLE and adjusted_target_vdot:
        adjusted_marathon_time = calculate_marathon_time_from_vdot(df_vdot, adjusted_target_vdot)
        st.markdown(f"""
<div class="warning-box">
    <h4>⚠️ 目標タイムについての重要なお知らせ</h4>
    <p>現在のVDOT（{vdot_info['vdot']}）と入力された目標VDOT（{original_target_vdot}）の差が<strong>{vdot_diff}</strong>あります。</p>
    <p>VDOT差が3.0を超える場合、1つのトレーニングサイクル（約12〜16週間）で達成するのは難しい可能性があります。</p>
    <h4>📊 今回のトレーニング計画について</h4>
    <p>そこで、今回のトレーニング計画では<strong>中間目標</strong>を設定します：</p>
    <ul>
        <li><strong>中間目標VDOT:</strong> {adjusted_target_vdot}（VDOT差 3.0）</li>
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
        with st.spinner("🏃 トレーニング計画を作成中...（1〜2分程度かかります）"):
            try:
                client = GeminiClient(api_key)
                effective_target_vdot_for_prompt = {"vdot": effective_target_vdot}
                prompt = create_training_prompt(
                    user_data, vdot_info, pace_info, effective_target_vdot_for_prompt,
                    df_pace, training_weeks, start_date, df_vdot
                )
                response = client.generate_content(prompt)
                st.session_state.training_plan = sanitize_gemini_output(response)
            except Exception as e:
                st.error(f"APIエラーが発生しました: {str(e)}")
                st.session_state.training_plan = None
    
    # トレーニング計画表示
    if st.session_state.training_plan:
        st.markdown("---")
        st.markdown("## 📋 トレーニング計画")
        st.markdown(st.session_state.training_plan)
        
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
