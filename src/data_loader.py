"""
AI Marathon Coach - Data Loader
CSVデータの読み込みと検証
"""
import os
import pandas as pd
import streamlit as st
from typing import Tuple

from .config import DATA_DIR, VDOT_LIST_FILE, VDOT_PACE_FILE


@st.cache_data
def load_csv_data() -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """CSVファイルを読み込み、検証ログを生成
    
    Returns:
        Tuple[df_vdot, df_pace, verification_log]
    """
    verification_log = {
        "success": False,
        "errors": [],
        "warnings": []
    }
    
    # 基準ディレクトリを取得（app.pyの場所を基準）
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, DATA_DIR)
    
    vdot_list_path = os.path.join(data_dir, VDOT_LIST_FILE)
    vdot_pace_path = os.path.join(data_dir, VDOT_PACE_FILE)
    
    try:
        # VDOTリストの読み込み
        if not os.path.exists(vdot_list_path):
            verification_log["errors"].append(f"VDOTリストファイルが見つかりません: {vdot_list_path}")
            return None, None, verification_log
        
        df_vdot = pd.read_csv(vdot_list_path)
        
        # 必須カラムの確認
        required_vdot_cols = ['VDOT', 'Marathon']
        missing_cols = [col for col in required_vdot_cols if col not in df_vdot.columns]
        if missing_cols:
            verification_log["errors"].append(f"VDOTリストに必須カラムがありません: {missing_cols}")
            return None, None, verification_log
        
        # ペースリストの読み込み
        if not os.path.exists(vdot_pace_path):
            verification_log["errors"].append(f"ペースファイルが見つかりません: {vdot_pace_path}")
            return None, None, verification_log
        
        df_pace = pd.read_csv(vdot_pace_path)
        
        # VDotカラムの空白を除去
        if 'VDot ' in df_pace.columns:
            df_pace = df_pace.rename(columns={'VDot ': 'VDot'})
        
        verification_log["success"] = True
        return df_vdot, df_pace, verification_log
        
    except Exception as e:
        verification_log["errors"].append(f"CSV読み込みエラー: {str(e)}")
        return None, None, verification_log
