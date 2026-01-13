"""
AI Marathon Coach - Gemini Client
Google Gemini API との統合（新SDK google.genai 使用）
"""
import re
from datetime import datetime
from typing import Optional

import pandas as pd
from google import genai
from google.genai import types

from ..config import (
    APP_NAME,
    APP_VERSION,
    GEMINI_MODEL_NAME,
    GEMINI_TEMPERATURE,
    GEMINI_TOP_P,
    GEMINI_MAX_OUTPUT_TOKENS,
    NUM_PHASES,
)
from ..vdot import (
    calculate_training_paces,
    calculate_phase_vdots,
    calculate_marathon_time_from_vdot,
)


class GeminiClient:
    """Gemini APIクライアント（新SDK対応）"""
    
    def __init__(self, api_key: str):
        """
        Args:
            api_key: Gemini API Key
        """
        self.client = genai.Client(api_key=api_key)
        self.model_name = GEMINI_MODEL_NAME
    
    def generate_content(self, prompt: str) -> Optional[str]:
        """コンテンツを生成
        
        Args:
            prompt: プロンプト
            
        Returns:
            生成されたテキスト（失敗時はNone）
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=GEMINI_TEMPERATURE,
                    top_p=GEMINI_TOP_P,
                    max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                ),
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini API エラー: {str(e)}")


def sanitize_gemini_output(content: str) -> str:
    """Geminiの出力からHTMLタグを除去してMarkdownのみにする
    
    Args:
        content: Geminiの出力テキスト
        
    Returns:
        HTMLタグを除去したテキスト
    """
    lines = content.split('\n')
    cleaned_lines = []
    
    # HTMLタグのパターン
    html_patterns = [
        r'<hr[^>]*>',
        r'</?h[1-6][^>]*>',
        r'</?p[^>]*>',
        r'</?strong[^>]*>',
        r'</?em[^>]*>',
        r'</?div[^>]*>',
        r'</?span[^>]*>',
        r'</?br[^>]*>',
        r'</?ul[^>]*>',
        r'</?li[^>]*>',
        r'</?ol[^>]*>',
        r'</?a[^>]*>',
        r'</?table[^>]*>',
        r'</?tr[^>]*>',
        r'</?td[^>]*>',
        r'</?th[^>]*>',
    ]
    
    for line in lines:
        has_html = False
        for pattern in html_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                has_html = True
                break
        
        if has_html:
            continue
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def create_training_prompt(
    user_data: dict,
    vdot_info: dict,
    pace_info: dict,
    target_vdot_info: dict,
    df_pace: pd.DataFrame,
    training_weeks: int,
    start_date: datetime,
    df_vdot: pd.DataFrame = None
) -> str:
    """トレーニング計画生成用のプロンプトを作成
    
    Args:
        user_data: ユーザー入力データ
        vdot_info: 現在のVDOT情報
        pace_info: ペース情報
        target_vdot_info: 目標VDOT情報
        df_pace: ペースデータフレーム
        training_weeks: トレーニング週数
        start_date: 開始日
        df_vdot: VDOTデータフレーム（オプション）
        
    Returns:
        Gemini APIに送信するプロンプト
    """
    paces = pace_info.get("paces", {}) if pace_info else {}
    current_vdot = vdot_info['vdot']
    target_vdot = target_vdot_info['vdot'] if target_vdot_info else current_vdot
    vdot_diff = round(target_vdot - current_vdot, 2)
    
    # 元の目標VDOTと調整済み目標VDOTの情報
    original_target_vdot = user_data.get("original_target_vdot")
    adjusted_target_vdot = user_data.get("adjusted_target_vdot")
    
    # 中間目標マラソンタイムを計算
    adjusted_marathon_time = ""
    if adjusted_target_vdot and df_vdot is not None:
        adjusted_marathon_time = calculate_marathon_time_from_vdot(df_vdot, adjusted_target_vdot)
    
    # 過去遡り開始の判定
    today = datetime.now()
    is_past_start = start_date < today
    
    # VDOT調整の説明文
    vdot_adjustment_note = ""
    if adjusted_target_vdot and original_target_vdot and adjusted_target_vdot != original_target_vdot:
        vdot_adjustment_note = f"""
## ⚠️ 目標VDOTの調整について（情報）

ユーザーが入力した目標タイム（{user_data.get('target_time', '')}、VDOT {original_target_vdot}）と現在のVDOT（{current_vdot}）の差が3.0を超えています。
今回のトレーニング計画では中間目標を設定しています：

- 中間目標VDOT: {adjusted_target_vdot}（VDOT差 3.0）
- 中間目標マラソンタイム: {adjusted_marathon_time}
- 最終目標: VDOT {original_target_vdot} / {user_data.get('target_time', '')}

※この情報は出力テンプレートの「基本情報」セクションに既に反映されています。追加の説明セクションを作成しないでください。
"""
    
    # レース日（フォーマット統一: YYYY/MM/DD）
    race_date_raw = user_data.get("race_date", "")
    try:
        race_dt = datetime.strptime(race_date_raw, "%Y-%m-%d")
        race_date_str = race_dt.strftime("%Y/%m/%d")
        race_weekday = ["月", "火", "水", "木", "金", "土", "日"][race_dt.weekday()]
        race_date_with_day = f"{race_dt.strftime('%m/%d')}（{race_weekday}）"
    except:
        race_date_str = race_date_raw
        race_date_with_day = race_date_raw
        race_weekday = ""
    
    # フェーズは4つ固定
    num_phases = NUM_PHASES
    weeks_per_phase = training_weeks // num_phases
    
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
    
    # 練習レース情報
    practice_races_note = ""
    if user_data.get('practice_races'):
        practice_races_note = f"""
# 練習レース
{user_data.get('practice_races')}
※練習レースは指定日に配置し、Qトレーニングとしてカウント。前日・前々日はEペースのみ。
"""
    
    # 開始日のフォーマット
    start_date_str = start_date.strftime("%Y/%m/%d")
    
    prompt = f"""# Role
あなたは「AIマラソンコーチ」です。ジャック・ダニエルズ博士の「ランニング・フォーミュラ」を熟知し、科学的根拠に基づいたトレーニング計画を提案します。

# ユーザー情報
- ニックネーム: {user_data.get('name', '不明')}
- 年齢: {user_data.get('age', '不明')}歳 / 性別: {user_data.get('gender', '不明')}
- 現在のベストタイム: {user_data.get('current_time', '不明')} → 目標タイム: {user_data.get('target_time', '不明')}
- 本番レース: {user_data.get('race_name', '不明')}（{race_date_str} {race_weekday}曜日）
- トレーニング期間: {start_date_str}から{race_date_str}までの{training_weeks}週間
- 練習レース: {user_data.get('practice_races', 'なし')}
- 週間走行距離: {user_data.get('weekly_distance', '不明')}km / 練習可能日数: 週{user_data.get('training_days', '不明')}日 / ポイント練習: 週{user_data.get('point_training_days', '不明')}回

# ユーザーからの要望（最優先で反映してください）
{user_data.get('concerns', 'なし')}

※ユーザーが明示的に要望していない練習手法（ダブルスレッショルド等）は使用しないでください。
※「2部練可能」はEペースジョグを午前と午後に分けることを指します。

# VDOT情報
- 現在: {current_vdot} → 目標: {target_vdot}（差: {vdot_diff}）
{vdot_adjustment_note}

# 4フェーズ構成（各約{weeks_per_phase}週間）
| フェーズ | 期間 | VDOT | 目的 |
|:---|:---|:---|:---|
| 1（基礎構築期） | 第1〜{weeks_per_phase}週 | {phase_vdots[0]} | Eペース中心、有酸素能力構築 |
| 2（強化期） | 第{weeks_per_phase+1}〜{weeks_per_phase*2}週 | {phase_vdots[1]} | T/I導入、持久力強化 |
| 3（実践期） | 第{weeks_per_phase*2+1}〜{weeks_per_phase*3}週 | {phase_vdots[2]} | Mペース増加、レースシミュレーション |
| 4（調整期） | 第{weeks_per_phase*3+1}〜{training_weeks}週 | {phase_vdots[3]} | テーパリング、疲労抜き |

{phase_info_text}

{practice_races_note}

# 出力構成
全{training_weeks}週間のトレーニング計画を以下の構成で出力してください：

1. はじめに（ユーザーへの挨拶、走力を褒め、計画のポイントを説明）
2. 基本情報
3. VDOTとペースの説明
4. 4フェーズ構成の概要（ユーザーの要望をどう反映したか説明）
5. 週間トレーニング計画（全{training_weeks}週分）
6. 注意事項（ユーザー固有の内容を含む5項目）
7. コーチからのメッセージ（2〜3段落で心を込めて）

# 週間トレーニング計画の出力形式（必須）
週間トレーニング計画は、**必ず以下のMarkdown表形式**で出力してください。箇条書きではなく表を使用してください。

**第1週（{start_date.strftime('%m/%d')} - XX/XX）**

| 日付 | メニュー | 距離 | ペース | 先生からのアドバイス |
|:---|:---|:---|:---|:---|
| {start_date.strftime('%m/%d')} (月) | ジョグ | 10km | E 5:02〜4:27 | ウォーミングアップをしっかりと |
| XX/XX (火) | 2部練 | AM 8km / PM 8km | E 5:02〜4:27 | 腰への負担を分散 |
| ... | ... | ... | ... | ... |
| XX/XX (日) | ロング走 | 25km | E 5:02〜4:27 | ペースよりフォーム維持を意識 |

週間走行距離: 120km

- 全{training_weeks}週分をこの表形式で出力
- 週は月曜始まり〜日曜終わり（7日分すべて記載）
- 各週の最後に「週間走行距離: XXkm」を記載
- 練習レースは本番ではなくトレーニングの一環として無理のないペース設定で

# 出力の最後に以下を必ず含めること
---
📚 もっと詳しく学びたい方へ： 科学的根拠に基づいて選んだ『推奨アイテムリスト』を運営ブログ「AkiRun｜走りを科学でアップデート」で紹介しています。
👉 [【保存版】練習効率を最大化する「厳選ギア」をチェックする](https://akirun.net/recommended-gear/)

---
*Generated by {APP_NAME} v{APP_VERSION}*
"""
    
    return prompt


def create_md_download(content: str) -> bytes:
    """Markdownファイルをダウンロード用バイトに変換（UTF-8 BOM付き）
    
    Args:
        content: Markdownコンテンツ
        
    Returns:
        UTF-8 BOM付きバイト列
    """
    bom = b'\xef\xbb\xbf'
    content_bytes = content.encode('utf-8')
    return bom + content_bytes
