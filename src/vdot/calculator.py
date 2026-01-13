"""
AI Marathon Coach - VDOT Calculator
タイムからVDOTを計算するロジック
"""
import pandas as pd
from typing import Optional


def time_to_seconds(time_str: str) -> Optional[int]:
    """時間文字列を秒に変換
    
    Args:
        time_str: 時間文字列 (例: "3:30:00", "25:00", "5:30")
        
    Returns:
        秒数（変換できない場合はNone）
    """
    if not time_str or pd.isna(time_str):
        return None
    
    time_str = str(time_str).strip()
    
    try:
        parts = time_str.replace("：", ":").split(":")
        parts = [int(p) for p in parts]
        
        if len(parts) == 3:
            # H:MM:SS
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            # M:SS or MM:SS
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return parts[0]
        else:
            return None
    except (ValueError, AttributeError):
        return None


def seconds_to_time(seconds: int, include_hours: bool = False) -> str:
    """秒を時間文字列に変換
    
    Args:
        seconds: 秒数
        include_hours: 時間を含めるかどうか
        
    Returns:
        時間文字列 (例: "3:30:00" or "5:30")
    """
    if seconds is None:
        return "N/A"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if include_hours or hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def calculate_vdot_from_time(df_vdot: pd.DataFrame, distance: str, time_seconds: int) -> dict:
    """タイムからVDOTを線形補間で算出
    
    Args:
        df_vdot: VDOTデータフレーム
        distance: 距離（"5km", "10km", "ハーフ", "フルマラソン"等）
        time_seconds: タイム（秒）
        
    Returns:
        dict: {
            "vdot": 計算されたVDOT値,
            "calculation_log": 計算過程の説明,
            "reference_data": 参照データ
        }
    """
    result = {
        "vdot": None,
        "calculation_log": "",
        "reference_data": {}
    }
    
    # 距離名のマッピング
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
    
    # VDOTとタイムのペアを作成
    vdot_times = []
    for _, row in df_vdot.iterrows():
        vdot = int(row['VDOT'])
        time_val = row[col_name]
        time_sec = time_to_seconds(str(time_val))
        if time_sec:
            vdot_times.append((vdot, time_sec))
    
    # タイムの降順（遅い順）にソート
    vdot_times.sort(key=lambda x: x[1], reverse=True)
    
    # 入力タイムを挟む2つのVDOTを見つける
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
    
    # 線形補間
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


def calculate_marathon_time_from_vdot(df_vdot: pd.DataFrame, vdot: float) -> str:
    """VDOTからマラソンタイムを線形補間で計算
    
    Args:
        df_vdot: VDOTデータフレーム
        vdot: VDOT値
        
    Returns:
        マラソンタイム文字列（例: "3:30:00"）
    """
    try:
        vdot_low = int(vdot)
        vdot_high = vdot_low + 1
        decimal_ratio = vdot - vdot_low
        
        row_low = df_vdot[df_vdot['VDOT'] == vdot_low]
        row_high = df_vdot[df_vdot['VDOT'] == vdot_high]
        
        if row_low.empty:
            return "N/A"
        
        time_low_str = str(row_low.iloc[0]['Marathon'])
        time_low_sec = time_to_seconds(time_low_str)
        
        if row_high.empty or time_low_sec is None:
            return time_low_str if time_low_sec else "N/A"
        
        time_high_str = str(row_high.iloc[0]['Marathon'])
        time_high_sec = time_to_seconds(time_high_str)
        
        if time_high_sec is None:
            return time_low_str
        
        # 線形補間（VDOTが上がるとタイムは短くなる）
        time_sec = time_low_sec + (time_high_sec - time_low_sec) * decimal_ratio
        
        # HH:MM:SS形式に変換
        hours = int(time_sec // 3600)
        minutes = int((time_sec % 3600) // 60)
        seconds = int(time_sec % 60)
        
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    except Exception:
        return "N/A"
