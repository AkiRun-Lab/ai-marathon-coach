"""
AI Marathon Coach - UI Components
再利用可能なUIコンポーネント
"""
import html
import os
from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st

from ..config import APP_NAME, APP_VERSION, NUM_PHASES, SHOE_CTA_VARIANTS, SHOE_FINDER_URL, jst_now
from ..vdot import calculate_phase_vdots


# 週間負荷グラフの強度種別（積み上げ順）と色
# 当初は青の濃淡（強度順のordinalランプ）だったが、凡例で同系色の区別がつきにくい
# というユーザーフィードバックにより、強度ごとに色相を分けた配色へ変更（2026-07-13）。
# ダーク背景 #0F172A に対して色覚多様性・コントラスト検証済み。「その他」のみ中立グレー
_LOAD_CHART_TYPES = [
    ("E", "E（イージー）", "#3987e5"),      # 青
    ("M", "M（マラソン）", "#199e70"),      # 緑
    ("T", "T（閾値）", "#c98500"),          # 黄
    ("I", "I（インターバル）", "#9085e9"),  # 紫
    ("R", "R（レペ）", "#e66767"),          # 赤（最高強度＝最も熱い色）
    ("other", "その他", "#94a3b8"),
]


def build_shoe_cta_content(stats) -> Optional[dict]:
    """plan_stats（st.session_state.plan_stats）から計画連動シューズCTAの表示内容を組み立てる

    Args:
        stats: summarize_plan_stats() の戻り値の形式
               （{"weekly_load", "cta_category", "avg_weekly_km", "avg_point_sessions"}）または None

    Returns:
        {"title": str, "sub": str, "url": str, "data_line": str}
        stats不正・必須キー欠落の場合はNone（例外は投げない）

    Note:
        シューズのカテゴリ判定には avg_point_sessions（強度M/T/I/Rの日数）を内部で使うが、
        表示（data_line/文言）には回数を出さない。ユーザー入力欄「ポイント練習回数」や
        計画本文のラベルと語が衝突して混乱を招くため（2026-07-16）。表示の数値軸は
        争いのない週間走行距離のみとする。
    """
    if not isinstance(stats, dict):
        return None

    required_keys = ("weekly_load", "cta_category", "avg_weekly_km", "avg_point_sessions")
    if not all(key in stats for key in required_keys):
        return None

    try:
        km_str = str(round(float(stats["avg_weekly_km"])))
    except (TypeError, ValueError):
        return None

    weekly_load = stats["weekly_load"]
    num_weeks = len(weekly_load) if isinstance(weekly_load, list) else 0

    category = stats["cta_category"]
    variant = SHOE_CTA_VARIANTS.get(category, SHOE_CTA_VARIANTS["general"])

    title = variant["title"].format(km=km_str)
    sub = variant["sub"].format(km=km_str)
    if num_weeks:
        data_line = f"あなたの計画：全{num_weeks}週 ・ 週間走行距離 平均{km_str}km"
    else:
        data_line = f"あなたの計画：週間走行距離 平均{km_str}km"

    return {
        "title": title,
        "sub": sub,
        "url": variant["url"],
        "data_line": data_line,
    }


def render_shoe_cta(stats) -> bool:
    """計画連動シューズ提案CTAカードを表示する

    Args:
        stats: st.session_state.plan_stats の内容（build_shoe_cta_content参照）

    Returns:
        描画できた場合True。stats不正で描画できない場合はFalse（呼び出し側は汎用CTAにフォールバックする）
    """
    content = build_shoe_cta_content(stats)
    if content is None:
        return False

    st.markdown(
        f"""
<style>
.akirun-shoe-cta {{
    background: linear-gradient(135deg, #F4C66B 0%, #E0A23D 100%);
    border-radius: 16px;
    padding: 2rem 1.5rem 1.6rem;
    margin: 1.5rem 0 0.6rem;
    text-align: center;
    position: relative;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.28);
}}
.akirun-shoe-cta .shoe-cta-badge {{
    position: absolute;
    top: -1px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(135deg, #1F3A6B, #2E5AA8);
    color: white;
    padding: 0.25rem 1.2rem;
    border-radius: 0 0 8px 8px;
    font-size: 0.72rem;
    font-weight: bold;
    letter-spacing: 0.5px;
}}
.akirun-shoe-cta .shoe-cta-data {{
    color: #4a3b14;
    font-size: 0.8rem;
    margin: 1.1rem 0 0.4rem;
}}
.akirun-shoe-cta .shoe-cta-title {{
    color: #1F3A6B;
    font-weight: 800;
    font-size: clamp(1.15rem, 4.6vw, 1.5rem);
    margin: 0 0 0.5rem;
}}
.akirun-shoe-cta .shoe-cta-sub {{
    color: #4a3b14;
    font-size: clamp(0.85rem, 3.2vw, 0.98rem);
    line-height: 1.6;
    margin: 0 auto 1.3rem;
    max-width: 34em;
}}
.akirun-shoe-cta-btn {{
    display: inline-block;
    background: #1F3A6B;
    color: #ffffff !important;
    padding: 0.95rem 2.4rem;
    border-radius: 10px;
    text-decoration: none !important;
    font-weight: 800;
    font-size: clamp(1rem, 3.8vw, 1.2rem);
    box-shadow: 0 5px 16px rgba(0, 0, 0, 0.3);
}}
.akirun-shoe-cta-btn:hover, .akirun-shoe-cta-btn:visited, .akirun-shoe-cta-btn:focus {{
    color: #ffffff !important;
    text-decoration: none !important;
}}
.akirun-shoe-cta .shoe-cta-note {{
    color: #5a4a1f;
    font-size: 0.72rem;
    margin: 1rem 0 0;
}}
</style>
<div class="akirun-shoe-cta">
    <div class="shoe-cta-badge">📊 この計画の分析から</div>
    <p style="font-size: 2.2rem; margin: 1.1rem 0 0.2rem;">👟</p>
    <p class="shoe-cta-data">{content["data_line"]}</p>
    <p class="shoe-cta-title">{content["title"]}</p>
    <p class="shoe-cta-sub">{content["sub"]}</p>
    <a class="akirun-shoe-cta-btn" href="{content["url"]}" target="_blank" rel="noopener noreferrer sponsored">👟 おすすめシューズ一覧（Amazon）を見る ›</a>
    <p class="shoe-cta-note">ウェア・補給などの愛用ギア一覧も同じページにあります<br>※ Amazonのアソシエイトとして適格販売により収入を得ています</p>
</div>
        """,
        unsafe_allow_html=True,
    )
    return True


# シューマッチング診断ツールが受け付けるVDOTの範囲（apps/shoe-finder/index.html のclampVdotと同一）
SHOE_FINDER_VDOT_MIN = 30
SHOE_FINDER_VDOT_MAX = 85


def build_shoe_finder_url(vdot) -> Optional[str]:
    """VDOTからシューマッチング診断ツールのURLを組み立てる（純粋関数）

    Args:
        vdot: VDOT値（float/int想定）。None・数値以外の場合はNoneを返す

    Returns:
        "{SHOE_FINDER_URL}?vdot={整数}" 形式のURL。vdotがNone・数値変換不可の場合はNone。
        範囲外（30〜85）の値は診断ツール側と同じ規則でクランプする。
    """
    if vdot is None:
        return None
    if isinstance(vdot, bool):
        return None
    try:
        vdot_float = float(vdot)
    except (TypeError, ValueError):
        return None

    vdot_int = int(round(vdot_float))
    vdot_int = max(SHOE_FINDER_VDOT_MIN, min(vdot_int, SHOE_FINDER_VDOT_MAX))
    return f"{SHOE_FINDER_URL}?vdot={vdot_int}"


def render_shoe_finder_cta(vdot) -> bool:
    """シューマッチング診断ツールへの誘導CTAカードを表示する

    Args:
        vdot: st.session_state.calculated_vdot["vdot"] の値

    Returns:
        描画できた場合True。vdotが不正で描画できない場合はFalse（何も表示しない）
    """
    url = build_shoe_finder_url(vdot)
    if url is None:
        return False

    st.markdown(
        f"""
<style>
.akirun-shoe-finder-cta {{
    background: linear-gradient(135deg, #4A7FE0 0%, #2C56A8 100%);
    border-radius: 16px;
    padding: 1.8rem 1.5rem 1.5rem;
    margin: 1rem 0 0.6rem;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.28);
}}
.akirun-shoe-finder-cta .shoe-finder-title {{
    color: #ffffff;
    font-weight: 800;
    font-size: clamp(1.1rem, 4.4vw, 1.4rem);
    margin: 0 0 0.5rem;
}}
.akirun-shoe-finder-cta .shoe-finder-sub {{
    color: #eaf0ff;
    font-size: clamp(0.85rem, 3.2vw, 0.95rem);
    line-height: 1.6;
    margin: 0 auto 1.2rem;
    max-width: 34em;
}}
.akirun-shoe-finder-cta-btn {{
    display: inline-block;
    background: #ffffff;
    color: #2C56A8 !important;
    padding: 0.85rem 2.2rem;
    border-radius: 10px;
    text-decoration: none !important;
    font-weight: 800;
    font-size: clamp(1rem, 3.8vw, 1.1rem);
    box-shadow: 0 5px 16px rgba(0, 0, 0, 0.2);
}}
.akirun-shoe-finder-cta-btn:hover, .akirun-shoe-finder-cta-btn:visited, .akirun-shoe-finder-cta-btn:focus {{
    color: #2C56A8 !important;
    text-decoration: none !important;
}}
</style>
<div class="akirun-shoe-finder-cta">
    <p class="shoe-finder-title">あなたの練習ペースに合うシューズは？</p>
    <p class="shoe-finder-sub">VDOTから練習ペース帯を算出し、レース用・スピード練用・デイリー用のおすすめを診断します。</p>
    <a class="akirun-shoe-finder-cta-btn" href="{url}" target="_blank" rel="noopener noreferrer">👟 シューズ診断を開く ›</a>
</div>
        """,
        unsafe_allow_html=True,
    )
    return True


def build_weekly_load_df(stats) -> Optional[pd.DataFrame]:
    """plan_stats（st.session_state.plan_stats）から週間負荷グラフ用のlong形式DataFrameを組み立てる

    Args:
        stats: summarize_plan_stats() の戻り値の形式
               （{"weekly_load", "cta_category", "avg_weekly_km", "avg_point_sessions"}）または None

    Returns:
        列: "週"(int)・"種別"(str・表示ラベル)・"距離"(float)・"順序"(int・積み上げ順インデックス)
        distanceが0の行は含めない。statsが不正・weekly_loadが空・全breakdown合計が0の場合はNone
    """
    if not isinstance(stats, dict):
        return None

    weekly_load = stats.get("weekly_load")
    if not isinstance(weekly_load, list) or not weekly_load:
        return None

    rows = []
    for week in weekly_load:
        if not isinstance(week, dict):
            continue

        week_num = week.get("week")
        breakdown = week.get("breakdown")
        if not isinstance(breakdown, dict):
            continue

        for order, (key, label, _color) in enumerate(_LOAD_CHART_TYPES):
            try:
                distance = float(breakdown.get(key, 0.0) or 0.0)
            except (TypeError, ValueError):
                distance = 0.0

            if distance <= 0:
                continue

            rows.append({
                "週": week_num,
                "種別": label,
                "距離": distance,
                "順序": order,
            })

    if not rows:
        return None

    return pd.DataFrame(rows)


def render_weekly_load_chart(stats) -> bool:
    """週間負荷（強度種別ごとの走行距離）の積み上げ棒グラフを表示する

    Args:
        stats: st.session_state.plan_stats の内容（build_weekly_load_df参照）

    Returns:
        描画できた場合True。statsが不正で描画できない場合はFalse
    """
    df = build_weekly_load_df(stats)
    if df is None:
        return False

    st.subheader("📊 週間負荷の推移")

    labels = [label for _key, label, _color in _LOAD_CHART_TYPES]
    colors = [color for _key, _label, color in _LOAD_CHART_TYPES]

    chart = (
        alt.Chart(df)
        .mark_bar(stroke="#0F172A", strokeWidth=1)
        .encode(
            x=alt.X("週:O", title="週"),
            y=alt.Y("sum(距離):Q", title="距離（km）"),
            color=alt.Color(
                "種別:N",
                scale=alt.Scale(domain=labels, range=colors),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            order=alt.Order("順序:Q"),
            tooltip=[
                alt.Tooltip("週:O", title="週"),
                alt.Tooltip("種別:N", title="種別"),
                alt.Tooltip("距離:Q", title="距離", format=".1f"),
            ],
        )
        .properties(height=320)
    )

    st.altair_chart(chart, width="stretch")

    total_km_values = []
    peak_week = None
    peak_km = 0.0
    for week in stats["weekly_load"]:
        if not isinstance(week, dict):
            continue
        try:
            week_km = float(week.get("total_km", 0.0) or 0.0)
        except (TypeError, ValueError):
            week_km = 0.0
        total_km_values.append(week_km)
        if peak_week is None or week_km > peak_km:
            peak_week = week.get("week")
            peak_km = week_km

    num_weeks = len(total_km_values)
    total_km = sum(total_km_values)
    avg_km = total_km / num_weeks if num_weeks else 0.0

    st.caption(
        f"全{num_weeks}週 合計{round(total_km)}km ・ 週平均{round(avg_km)}km "
        f"・ ピーク週は第{peak_week}週（{round(peak_km)}km）"
    )
    st.caption(
        "週間走行距離の増やし方は、前週比10%以内が目安としてよく用いられます。"
        "距離が下がる週は回復週で、意図的な設計です。"
    )

    return True


def load_css() -> None:
    """外部CSSファイルを読み込んで適用"""
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        # フォールバック：インラインCSS
        st.markdown("""
        <style>
            .main-header { font-size: 2.5rem; color: #1E88E5; text-align: center; }
            .version-tag { font-size: 0.9rem; color: #888; text-align: center; }
            .sub-header { font-size: 1.2rem; color: #666; text-align: center; margin-bottom: 2rem; }
        </style>
        """, unsafe_allow_html=True)


def render_header() -> None:
    """アプリヘッダーを表示"""
    st.markdown(f'<h1 class="main-header">🏃 {APP_NAME}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="version-tag">Version {APP_VERSION}</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">ジャック・ダニエルズのVDOT理論に基づく、あなただけのトレーニング計画</p>', unsafe_allow_html=True)


def render_footer() -> None:
    """フッターを表示（開発者情報・ブログリンク含む）"""
    st.markdown("---")
    
    # 更新履歴（CHANGELOG.mdから読み込み）
    with st.expander("📋 更新履歴", expanded=False):
        changelog_path = os.path.join(os.path.dirname(__file__), "../../CHANGELOG.md")
        try:
            with open(changelog_path, "r", encoding="utf-8") as f:
                changelog_content = f.read()
            st.markdown(changelog_content)
        except FileNotFoundError:
            st.markdown("更新履歴ファイルが見つかりません。")
    
    # 開発者情報（縦並び・中央揃え）
    st.markdown("""
<div style="text-align: center;">
    <p><strong>👤 開発者: あきら</strong><br>🏃 フルマラソンPB 2:46:27</p>
    <p>
        📝 <a href="https://akirun.net/" target="_blank">AkiRun｜走りを科学でアップデート</a><br>
        📖 <a href="https://akirun.net/ai-marathon-coach-guide/" target="_blank">マラソントレーニング・プランナーの使い方</a>
    </p>
</div>
    """, unsafe_allow_html=True)
    
    st.markdown(
        f'<p style="text-align: center; color: #888; font-size: 0.85rem; margin-top: 1rem;">'
        f'{APP_NAME} v{APP_VERSION} | © 2025–{jst_now().year} AkiRun</p>',
        unsafe_allow_html=True
    )


def render_vdot_display(user_name: str, vdot_info: dict, target_vdot: dict, 
                         paces: dict, vdot_diff: float) -> None:
    """VDOT計算結果を表示
    
    Args:
        user_name: ユーザー名
        vdot_info: 現在のVDOT情報
        target_vdot: 目標VDOT情報
        paces: ペース情報
        vdot_diff: VDOT差
    """
    target_vdot_display = ""
    if target_vdot and target_vdot.get("vdot"):
        target_vdot_display = f'<span style="margin-left: 2rem;">🎯 目標VDOT: <strong>{target_vdot["vdot"]}</strong></span>'

    # ユーザー入力をunsafe_allow_htmlのHTMLに埋め込むためエスケープする
    safe_user_name = html.escape(user_name or "")

    st.markdown(f"""
<div class="vdot-display">
    <h3 style="margin: 0 0 1rem 0; color: white;">📊 {safe_user_name}さんのVDOT計算結果</h3>
    <div style="font-size: 1.3rem; margin-bottom: 1rem;">
        🏃 現在のVDOT: <strong>{vdot_info['vdot']}</strong>{target_vdot_display}
        <span style="margin-left: 2rem;">📈 VDOT差: <strong>{vdot_diff}</strong></span>
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


def render_vdot_explanation() -> None:
    """VDOT解説を表示"""
    st.markdown("""
<div class="vdot-explanation">
    <h4>📖 VDOTとは</h4>
    <p>VDOTは、ジャック・ダニエルズ博士が考案した走力指標です。現在のタイムから算出され、適切なトレーニングペースを導き出すことができます。</p>
    <ul>
        <li><strong>E (Easy)</strong>: 会話ができる楽なペース。全体の70-80%をこのペースで。</li>
        <li><strong>M (Marathon)</strong>: フルマラソンの目標ペース。</li>
        <li><strong>T (Threshold)</strong>: 乳酸閾値ペース。20〜30分維持できる強度。</li>
        <li><strong>I (Interval)</strong>: インターバルペース。3〜5分維持できる強度。</li>
        <li><strong>R (Repetition)</strong>: 反復ペース。短い距離のスピード練習用。</li>
    </ul>
</div>
    """, unsafe_allow_html=True)


def render_phase_table(current_vdot: float, target_vdot: float, training_weeks: int) -> None:
    """4フェーズ構成テーブルを表示
    
    Args:
        current_vdot: 現在のVDOT
        target_vdot: 目標VDOT
        training_weeks: トレーニング週数
    """
    phase_vdots = calculate_phase_vdots(current_vdot, target_vdot, NUM_PHASES)
    weeks_per_phase = training_weeks // NUM_PHASES
    
    st.markdown(f"""
<div class="phase-explanation">
    <h4>📈 4フェーズ構成（全{training_weeks}週間）</h4>
    <table style="width: 100%; border-collapse: collapse;">
        <tr style="background-color: #E3F2FD;">
            <th style="padding: 8px; text-align: left;">フェーズ</th>
            <th style="padding: 8px; text-align: left;">期間</th>
            <th style="padding: 8px; text-align: left;">目標VDOT</th>
            <th style="padding: 8px; text-align: left;">主な目的</th>
        </tr>
        <tr>
            <td style="padding: 8px;">フェーズ1（基礎構築期）</td>
            <td style="padding: 8px;">第1〜{weeks_per_phase}週</td>
            <td style="padding: 8px;">{phase_vdots[0]}</td>
            <td style="padding: 8px;">基礎体力の構築</td>
        </tr>
        <tr style="background-color: #F5F5F5;">
            <td style="padding: 8px;">フェーズ2（強化期）</td>
            <td style="padding: 8px;">第{weeks_per_phase+1}〜{weeks_per_phase*2}週</td>
            <td style="padding: 8px;">{phase_vdots[1]}</td>
            <td style="padding: 8px;">持久力・スピードの強化</td>
        </tr>
        <tr>
            <td style="padding: 8px;">フェーズ3（実践期）</td>
            <td style="padding: 8px;">第{weeks_per_phase*2+1}〜{weeks_per_phase*3}週</td>
            <td style="padding: 8px;">{phase_vdots[2]}</td>
            <td style="padding: 8px;">レースペースへの適応</td>
        </tr>
        <tr style="background-color: #F5F5F5;">
            <td style="padding: 8px;">フェーズ4（調整期）</td>
            <td style="padding: 8px;">第{weeks_per_phase*3+1}〜{training_weeks}週</td>
            <td style="padding: 8px;">{phase_vdots[3]}</td>
            <td style="padding: 8px;">テーパリング・最終調整</td>
        </tr>
    </table>
</div>
    """, unsafe_allow_html=True)


def render_warning_box(title: str, content: str) -> None:
    """警告ボックスを表示"""
    st.markdown(f"""
<div class="warning-box">
    <h4>{title}</h4>
    {content}
</div>
    """, unsafe_allow_html=True)


def render_disclaimer() -> None:
    """利用規約・注意事項を表示"""
    with st.expander("📜 利用規約・注意事項（必ずお読みください）"):
        st.markdown("""
1. 本サービスはAIによるトレーニング計画の参考情報を提供するものであり、医療・運動指導の専門家によるアドバイスに代わるものではありません。

2. 生成されるトレーニング計画の正確性・安全性を保証するものではありません。実施にあたっては、ご自身の体調や健康状態を考慮し、**自己責任**で行ってください。

3. 怪我、体調不良、その他いかなる損害が生じた場合も、運営者は一切の責任を負いません。

4. 持病のある方、健康に不安のある方は、事前に医師や専門家にご相談ください。

5. 入力された情報はトレーニング計画の生成にのみ使用され、保存・収集されません。

6. **ご利用のお願い**: 本サービスはAPI利用料の関係で、1日の生成回数に制限があります。より多くの方にご利用いただくため、**お一人様1日1回の利用**にご協力ください。
""")
