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
import json

from ..config import (
    APP_NAME,
    APP_VERSION,
    GEMINI_MODEL_NAME,
    GEMINI_TEMPERATURE,
    GEMINI_TOP_P,
    GEMINI_MAX_OUTPUT_TOKENS,
    NUM_PHASES,
    GEMINI_RESPONSE_MIME_TYPE,
    GEMINI_THINKING_MODE,
    GEMINI_THINKING_BUDGET,
    get_max_output_tokens,
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
    
    def generate_content(self, prompt: str, max_output_tokens: int = None) -> Optional[str]:
        """コンテンツを生成
        
        Args:
            prompt: プロンプト
            max_output_tokens: 最大出力トークン数（Noneの場合はデフォルト値を使用）
            
        Returns:
            生成されたテキスト（失敗時はNone）
        """
        effective_max_tokens = max_output_tokens or GEMINI_MAX_OUTPUT_TOKENS
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=GEMINI_TEMPERATURE,
                    top_p=GEMINI_TOP_P,
                    max_output_tokens=effective_max_tokens,
                    response_mime_type=GEMINI_RESPONSE_MIME_TYPE,
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_budget=GEMINI_THINKING_BUDGET,
                    ) if GEMINI_THINKING_MODE else None,
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
    # None または空文字列の場合は早期リターン
    if not content:
        return ""
    
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

【重要】出力を作成する前に深く思考し、全体の整合性を確認してください。
特に、以下の点を厳重にチェックし、矛盾があれば修正してから出力してください：
1. 長期的な負荷の漸進性：急激な距離や強度の増加がないか。
2. 目標との整合性：中間目標や最終目標と、設定されたペース・距離が矛盾していないか。
3. 文脈の統一：導入文やアドバイスで述べた内容と、実際のメニュースケジュールが食い違っていないか。

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

※ユーザーが明示的に要望していない特殊な練習手法は使用しないでください。
- **2部練（ダブルスプリット）**: ユーザー要望（concerns）に「2部練」「朝晩練習」等の記載がない限り、**絶対に**組み込まないでください。基本は1日1回の練習です。
- **ダブルスレッショルド**: これは2部練の一種ですが、非常に高強度な特殊練習です。ユーザー要望に「ダブルスレッショルド」と明確に記載がない限り、**絶対に**使用しないでください。「2部練したい」という要望だけではダブルスレッショルドにはせず、通常の「ポイント練習＋Eジョグ」等の構成にしてください。
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
全{training_weeks}週間のトレーニング計画を、**必ず以下のJSON形式（JSONスキーマに従う）**で出力してください。Markdownのコードブロックは不要です。生JSONのみを出力してください。

## ⚠️ 絶対遵守事項：全週出力
- weekly_schedulesには**必ず第1週から第{training_weeks}週まで全{training_weeks}週分**を省略せず出力してください。
- 代表的な週だけを出力して残りを省略することは**禁止**です。
- weekly_schedulesの配列要素数は**正確に{training_weeks}個**でなければなりません。
- 各週で7日分のdaysを必ず含めてください。

JSON Schema:
{{
    "reasoning_summary": "string (プラン作成の思考プロセス要約)",
    "plan": {{
        "introduction": "string (挨拶、走力評価、プランのポイント)",
        "basic_info": {{
            "target_race": "string",
            "target_time": "string",
            "weekly_mileage": "string",
            "current_vdot": float,
            "target_vdot": float
        }},
        "vdot_paces": {{
            "phase_1": {{ "E": "string", "M": "string", "T": "string", "I": "string", "R": "string" }},
            "phase_2": {{ "E": "string", "M": "string", "T": "string", "I": "string", "R": "string" }},
            "phase_3": {{ "E": "string", "M": "string", "T": "string", "I": "string", "R": "string" }},
            "phase_4": {{ "E": "string", "M": "string", "T": "string", "I": "string", "R": "string" }}
        }},
        "phase_overview": "string (4フェーズ構成の概要説明)",
        "weekly_schedules": [
            {{
                "week": int,
                "dates": "string (MM/DD - MM/DD)",
                "days": [
                    {{
                        "date": "string (MM/DD (曜))",
                        "menu": "string",
                        "distance": "string",
                        "pace": "string",
                        "advice": "string"
                    }}
                ],
                "total_distance": "string"
            }}
        ],
        "precautions": ["string (注意事項1)", "string (注意事項2)", ...],
        "coach_message": "string",
        "footer": "string"
    }}
}}

※ 重要: weekly_schedulesの要素数は必ず{training_weeks}個です。省略は一切認めません。
"""
    
    return prompt


def _repair_json(json_str: str) -> str:
    """Geminiが出力する不正なJSONの修復を試みる
    
    よくあるパターン:
    - "menu"キーの欠落: { "date": "...", "休息", "distance": ... }
    - 裸の文字列値がキーなしで出現
    """
    # パターン1: "date"の後に"menu"キーなしで裸の文字列が来る場合
    # 例: "date": "07/16 (木)", "休息", "distance"
    #   → "date": "07/16 (木)", "menu": "休息", "distance"
    repaired = re.sub(
        r'("date"\s*:\s*"[^"]*")\s*,\s*"([^"]*?)"\s*,\s*"distance"',
        r'\1, "menu": "\2", "distance"',
        json_str
    )
    
    # パターン2: 任意のキーの後にキーなし裸文字列が来る場合（汎用）
    # 例: "key": "value", "bare_string", "next_key":
    #   → "key": "value", "unknown": "bare_string", "next_key":
    repaired = re.sub(
        r'(:\s*"[^"]*")\s*,\s*"([^"]*?)"\s*,\s*"(\w+)"\s*:',
        r'\1, "menu": "\2", "\3":',
        repaired
    )
    
    return repaired


def convert_json_to_markdown(json_str: str) -> str:
    """GeminiのJSON応答をMarkdown形式に変換する"""
    try:
        # JSON文字列のクリーニング（Markdownコードブロックなどで囲まれている場合の対策）
        json_str = json_str.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        
        # まずそのままパースを試みる
        data = None
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # パース失敗時はJSON修復を試みる
            repaired = _repair_json(json_str)
            try:
                data = json.loads(repaired)
            except json.JSONDecodeError:
                # 修復も失敗した場合はエラーメッセージを返す
                return "⚠️ AIの応答データに問題がありました。お手数ですが、ページを再読み込みして再度お試しください。"
        
        # 配列のトップレベルか、オブジェクト内のplanかを確認
        plan = {}
        if isinstance(data, list) and len(data) > 0:
             # 一部のモデルは配列で返すことがある
             if "plan" in data[0]:
                 plan = data[0]["plan"]
             else:
                 plan = data[0]
        elif isinstance(data, dict):
            if "plan" in data:
                plan = data["plan"]
            else:
                plan = data
        
        # Markdown構築
        md = []
        
        # 1. はじめに
        md.append(f"## はじめに\n\n{plan.get('introduction', '')}\n")
        
        # 2. 基本情報
        info = plan.get('basic_info', {})
        md.append("## 基本情報\n")
        md.append(f"- 目標レース: {info.get('target_race', '')}")
        md.append(f"- 目標タイム: {info.get('target_time', '')}")
        md.append(f"- 週間走行距離: {info.get('weekly_mileage', '')}")
        md.append(f"- 現在VDOT: {info.get('current_vdot', '')} → 目標VDOT: {info.get('target_vdot', '')}\n")
        
        # 3. VDOTとペース
        md.append("## VDOTと設定ペース\n")
        paces = plan.get('vdot_paces', {})
        
        available_phases = []
        for i in range(1, 5):
            if paces.get(f"phase_{i}"):
                available_phases.append(i)
                
        if available_phases:
            header = "| ペース |"
            align = "|:---|"
            for i in available_phases:
                header += f" フェーズ{i} |"
                align += ":---|"
                
            md.append(header)
            md.append(align)
            
            pace_types = [
                ("E (Easy)", "E"),
                ("M (Marathon)", "M"),
                ("T (Threshold)", "T"),
                ("I (Interval)", "I"),
                ("R (Repetition)", "R")
            ]
            
            for label, key in pace_types:
                row = f"| {label} |"
                for i in available_phases:
                    val = str(paces.get(f"phase_{i}", {}).get(key, '')).strip()
                    if val.endswith('/km'):
                        row += f" {val} |"
                    elif val:
                        row += f" {val}/km |"
                    else:
                        row += " |"
                md.append(row)
            md.append("")
        
        # 4. フェーズ構成
        md.append(f"## 4フェーズ構成の概要\n\n{plan.get('phase_overview', '')}\n")
        
        # 5. 週間トレーニング計画
        md.append("## 週間トレーニング計画\n")
        weeks = plan.get('weekly_schedules', [])
        for week in weeks:
            md.append(f"**第{week.get('week', '?')}週（{week.get('dates', '')}）**\n")
            md.append("| 日付 | メニュー | 距離 | ペース | AIコーチからのアドバイス |")
            md.append("|:---|:---|:---|:---|:---|")
            
            for day in week.get('days', []):
                md.append(f"| {day.get('date', '')} | {day.get('menu', '')} | {day.get('distance', '')} | {day.get('pace', '')} | {day.get('advice', '')} |")
            
            md.append(f"\n週間走行距離: {week.get('total_distance', '')}\n")
        
        # 6. 注意事項
        md.append("## 注意事項\n")
        for item in plan.get('precautions', []):
            md.append(f"- {item}")
        md.append("")
        
        # 7. コーチからのメッセージ
        md.append(f"## コーチからのメッセージ\n\n{plan.get('coach_message', '')}\n")
        
        # フッター
        md.append("---")
        md.append(f"*{plan.get('footer', 'Generated by AI Marathon Coach')}*")
        
        return "\n".join(md)

    except Exception as e:
        return f"⚠️ データの変換中にエラーが発生しました。お手数ですが、ページを再読み込みして再度お試しください。\n\n詳細: {str(e)}"



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
