"""
AI Marathon Coach - UI Components
再利用可能なUIコンポーネント
"""
import os
import streamlit as st

from ..config import APP_NAME, APP_VERSION, NUM_PHASES
from ..vdot import calculate_phase_vdots


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
    <p><strong>👤 開発者: あきら</strong><br>🏃 フルマラソンPB 2:46:27（56歳）</p>
    <p>
        📝 <a href="https://akirun.net/" target="_blank">AkiRun｜走りを科学でアップデート</a><br>
        📖 <a href="https://akirun.net/ai-marathon-coach-guide/" target="_blank">AIマラソンコーチの使い方</a>
    </p>
</div>
    """, unsafe_allow_html=True)
    
    st.markdown(
        f'<p style="text-align: center; color: #888; font-size: 0.85rem; margin-top: 1rem;">'
        f'{APP_NAME} v{APP_VERSION} | © 2025 AkiRun</p>',
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
    
    st.markdown(f"""
<div class="vdot-display">
    <h3 style="margin: 0 0 1rem 0; color: white;">📊 {user_name}さんのVDOT計算結果</h3>
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
