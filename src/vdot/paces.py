"""
AI Marathon Coach - Training Paces
VDOTからトレーニングペースを計算
"""
import pandas as pd
from typing import List

from .calculator import time_to_seconds, seconds_to_time


def calculate_training_paces(df_pace: pd.DataFrame, vdot: float) -> dict:
    """VDOTから練習ペースを線形補間で算出
    
    Args:
        df_pace: ペースデータフレーム
        vdot: VDOT値
        
    Returns:
        dict: {
            "paces": {ペースタイプ: {seconds, display}},
            "calculation_log": 計算過程,
            "success": 成功フラグ
        }
    """
    result = {
        "paces": {},
        "calculation_log": "",
        "success": False
    }
    
    vdot_col = "VDot" if "VDot" in df_pace.columns else "VDOT"
    
    # カラム名の空白を処理
    if vdot_col not in df_pace.columns:
        # 空白付きのカラム名をチェック
        for col in df_pace.columns:
            if col.strip().lower() == "vdot":
                vdot_col = col
                break
    
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
    
    # Eペースの範囲表示を追加
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


def calculate_phase_vdots(current_vdot: float, target_vdot: float, num_phases: int = 4) -> List[float]:
    """フェーズごとのVDOT目標を計算（4フェーズ固定）
    
    フェーズ1: 現在のVDOT（基礎構築期）
    フェーズ2〜4: 段階的に目標VDOTに近づける
    
    Args:
        current_vdot: 現在のVDOT
        target_vdot: 目標VDOT
        num_phases: フェーズ数（デフォルト4）
        
    Returns:
        各フェーズのVDOT目標リスト
    """
    vdot_diff = target_vdot - current_vdot
    # フェーズ1は現在VDOT、残り3フェーズで目標に到達
    step = vdot_diff / (num_phases - 1) if num_phases > 1 else vdot_diff
    
    phase_vdots = []
    for i in range(num_phases):
        if i == 0:
            # フェーズ1は現在のVDOT
            phase_vdots.append(round(current_vdot, 2))
        else:
            # フェーズ2以降は段階的に上昇
            phase_vdot = round(current_vdot + step * i, 2)
            phase_vdots.append(phase_vdot)
    
    return phase_vdots
