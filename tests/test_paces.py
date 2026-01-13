"""
AI Marathon Coach - Paces Tests
"""
import pytest
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vdot.paces import calculate_training_paces, calculate_phase_vdots


class TestCalculateTrainingPaces:
    """calculate_training_paces関数のテスト"""
    
    @pytest.fixture
    def df_pace(self):
        """テスト用ペースデータフレーム"""
        import pandas as pd
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "vdot_pace.csv"
        )
        return pd.read_csv(data_path)
    
    def test_vdot_50(self, df_pace):
        """VDOT 50のペース計算テスト"""
        result = calculate_training_paces(df_pace, 50.0)
        
        assert result["success"] is True
        assert "E" in result["paces"]
        assert "M" in result["paces"]
        assert "T" in result["paces"]
        assert "I" in result["paces"]
        assert "R" in result["paces"]
    
    def test_vdot_interpolation(self, df_pace):
        """VDOT補間のテスト（小数点）"""
        result = calculate_training_paces(df_pace, 50.5)
        
        assert result["success"] is True
        # 50.5は50と51の間なので、両方のペースの中間値になるはず
        assert result["paces"]["M"]["seconds"] is not None
    
    def test_invalid_vdot(self, df_pace):
        """無効なVDOTのテスト"""
        result = calculate_training_paces(df_pace, 10.0)  # 範囲外
        
        assert result["success"] is False
        assert "エラー" in result["calculation_log"]
    
    def test_pace_structure(self, df_pace):
        """ペースデータ構造のテスト"""
        result = calculate_training_paces(df_pace, 55.0)
        
        # Mペースの構造確認
        m_pace = result["paces"]["M"]
        assert "seconds" in m_pace
        assert "display" in m_pace
        assert isinstance(m_pace["seconds"], int)
        assert isinstance(m_pace["display"], str)


class TestCalculatePhaseVdots:
    """calculate_phase_vdots関数のテスト"""
    
    def test_basic_calculation(self):
        """基本的な計算テスト"""
        result = calculate_phase_vdots(50.0, 53.0, 4)
        
        assert len(result) == 4
        assert result[0] == 50.0  # フェーズ1は現在VDOT
        assert result[3] == 53.0  # フェーズ4は目標VDOT
    
    def test_linear_progression(self):
        """線形進行のテスト"""
        result = calculate_phase_vdots(50.0, 53.0, 4)
        
        # 差が3.0で4フェーズなので、各ステップは1.0
        assert result[0] == 50.0
        assert result[1] == 51.0
        assert result[2] == 52.0
        assert result[3] == 53.0
    
    def test_same_vdot(self):
        """現在と目標が同じ場合"""
        result = calculate_phase_vdots(50.0, 50.0, 4)
        
        assert len(result) == 4
        assert all(v == 50.0 for v in result)
    
    def test_single_phase(self):
        """1フェーズの場合"""
        result = calculate_phase_vdots(50.0, 53.0, 1)
        
        assert len(result) == 1
        assert result[0] == 50.0
    
    def test_decimal_vdot(self):
        """小数点VDOTのテスト"""
        result = calculate_phase_vdots(50.5, 53.5, 4)
        
        assert result[0] == 50.5
        assert result[3] == 53.5
