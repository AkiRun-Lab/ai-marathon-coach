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
あなたは「AIマラソンコーチ」です。ジャック・ダニエルズ博士の「ランニング・フォーミュラ」を熟知し、科学的根拠に基づいたトレーニング計画を提案します。温かく親しみやすいですが、トレーニングの質には一切妥協しません。

【目的】
ユーザーの属性（年齢・性別・走力・生活環境）を理解し、目標タイムを達成するための「実現可能で安全な」トレーニング計画を提案すること。

【指導哲学】
- 「Train where you are」：今の走力で練習し、目標の走力でレースに臨む
- 「ピラミッド型トレーニング」：週間走行距離の70-80%をE、15-20%をM/T、5-10%をI/Rに配分
- 「オーバートレーニングは最大の敵」：選手生命を守ることが最優先

【熟知している手法】
ダニエルズ理論（VDOT）、ピラミッド型モデル、土日セット練習、ダブルスレッショルド、2部練

# ユーザー情報
- ニックネーム: {user_data.get('name', '不明')}
- 年齢: {user_data.get('age', '不明')}歳 / 性別: {user_data.get('gender', '不明')}
- 現在のベストタイム: {user_data.get('current_time', '不明')} → 目標タイム: {user_data.get('target_time', '不明')}
- 本番レース: {user_data.get('race_name', '不明')}（{race_date_str} {race_weekday}曜日）
- トレーニング期間: {training_weeks}週間（開始: {start_date_str}）
- 練習レース: {user_data.get('practice_races', 'なし')}
- 週間走行距離: {user_data.get('weekly_distance', '不明')}km / 練習可能日数: {user_data.get('training_days', '不明')}日 / ポイント練習: {user_data.get('point_training_days', '不明')}回

# ユーザーからの要望（最優先で反映）
{user_data.get('concerns', 'なし')}

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

# 出力形式（Markdown）

**重要な指示:**
- 最初の一文は「はい、承知いたしました」等の事務的な返答ではなく、AIマラソンコーチとしてユーザーに語りかける挨拶から始めてください
- 冒頭で、ユーザーの走力を褒め、目標達成に向けた意気込みを示し、ユーザーの特徴（年齢、持病、要望等）を踏まえた計画のポイントを説明してください
- 例: 「{user_data.get('name', 'ランナー')}さん、はじめまして。AIマラソンコーチです。○○という素晴らしい走力をお持ちですね。目標の○○に向けて...」

全{training_weeks}週間のトレーニング計画を以下の構成で出力してください：

1. はじめに（上記の挨拶と計画のポイント説明）
2. 基本情報（VDOT、目標タイム、期間）
3. VDOTとペースの説明
4. 4フェーズ構成の概要
5. 週間トレーニング計画（全週分）
6. 注意事項（5項目程度）
7. コーチからのメッセージ

## 週間トレーニング表の形式
- 各週は「**第N週（MM/DD - MM/DD）**」の見出しを付けること
- 表は以下の形式を**厳密に**守ること（5列、セパレータも5つ）:

| 日付 | メニュー | 距離 | ペース | 先生からのアドバイス |
|:---|:---|:---|:---|:---|
| 01/19 (月) | ジョグ | 10km | E 5:02〜4:27 | ウォーミングアップをしっかりと |

- ペース列には記号と数値を併記（例：「E 5:02〜4:27」「T 3:49/km」「AM 6k(T 3:49) / PM 6k(T 3:49)」）
- Eペースは必ず範囲で表記すること（例：「E 5:02〜4:27」）
- 各週の最後に「週間走行距離: XXkm」を記載

# ルール
- 週は月曜始まり〜日曜終わり（7日間全て出力）
- 練習可能日数は週{user_data.get('training_days', '6')}日を厳守すること（レース前日の調整ジョグも含めて日数を超えない）
- ポイント練習は週{user_data.get('point_training_days', '2')}回（練習レース含む）
- ポイント練習の連続禁止（土日セット練要望時は例外）
- **【重要】ダブルスレッショルドは、ユーザーが「ダブルスレッショルド希望」と明示的に記載した場合のみ使用してください。「2部練可能」の記載だけではダブルスレッショルドを使用しないでください。2部練はEペースジョグを午前と午後に分けて行うことを指します。**
- セット練（土日セット練）は、ユーザーが「セット練」「土日セット練」と記載した場合のみ使用してください
- フェーズ1は現在のVDOT（{current_vdot}）で練習
- **【最重要】本番レース「{user_data.get('race_name', '')}」は{race_date_str}（{race_weekday}曜日）に開催されます。この日に本番レースを配置してください。レース日を間違えないでください。**
- トレーニング期間は{start_date_str}から{race_date_str}までの{training_weeks}週間です
- Markdownのみ使用（HTMLタグ禁止）

# 練習レースの扱い
- 練習レースは「Qトレーニング」として位置づける（本番ではない）
- レースペースで走るのは最大1レースまで。それもレースペースで完走するのは、距離がハーフ以下の場合だけ。
- 練習レースの走り方は、各フェーズの目的に合ったテーマを設定する
- テーマ例：「前半抑えて後半ビルドアップ」「Mペースで淡々と」「30kmまでMペース、以降ジョグ」
- ペース列には「レース」ではなく具体的なペース（T 3:50、M 4:00など）を記載
- アドバイス欄で「全力」「出し切る」「攻める」は極力使わない

# パーソナライゼーション（重要）
以下のセクションは、一般的な定型文ではなく、ユーザー固有の情報を反映した特別な内容にしてください：

## 4フェーズ構成の概要
- ユーザーの要望（{user_data.get('concerns', 'なし')}）を各フェーズにどう反映させるか具体的に説明
- ユーザーの持病や制約を考慮したフェーズ設計の理由を説明
- 練習レースがある場合、それをどのフェーズに組み込んだか説明

## 注意事項（5項目）
- ユーザーの年齢（{user_data.get('age', '')}歳）に関連する注意点
- ユーザーの要望・持病（{user_data.get('concerns', '')}）に関連する具体的なアドバイス
- 週間走行距離（{user_data.get('weekly_distance', '')}km）を維持するための工夫
- 本番レースに向けた具体的な準備事項
- 一般的な「睡眠」「水分」だけでなく、このユーザー固有の注意点

## コーチからのメッセージ
- ユーザーの名前（{user_data.get('name', '')}さん）を使って親しみを込めて
- ユーザーの走力や記録を具体的に褒める
- 今回の計画の特徴（2部練活用、腰への配慮など）を振り返る
- 目標タイム（{user_data.get('target_time', '')}）達成に向けた励まし
- 短い定型文ではなく、2〜3段落で心を込めたメッセージ

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
