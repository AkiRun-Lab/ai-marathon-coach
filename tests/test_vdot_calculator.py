"""
AI Marathon Coach - VDOT Calculator Tests
"""
import pytest
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vdot.calculator import (
    time_to_seconds,
    seconds_to_time,
)


class TestTimeToSeconds:
    """time_to_seconds関数のテスト"""
    
    def test_hms_format(self):
        """H:MM:SS形式のテスト"""
        assert time_to_seconds("3:30:00") == 12600  # 3時間30分
        assert time_to_seconds("2:59:59") == 10799
        assert time_to_seconds("4:00:00") == 14400
    
    def test_ms_format(self):
        """M:SS形式のテスト"""
        assert time_to_seconds("5:30") == 330  # 5分30秒
        assert time_to_seconds("25:00") == 1500  # 25分
        assert time_to_seconds("4:15") == 255
    
    def test_mmss_format(self):
        """MM:SS形式のテスト"""
        assert time_to_seconds("30:00") == 1800  # 30分
        assert time_to_seconds("45:30") == 2730
    
    def test_invalid_input(self):
        """無効な入力のテスト"""
        assert time_to_seconds(None) is None
        assert time_to_seconds("") is None
        assert time_to_seconds("invalid") is None
    
    def test_japanese_colon(self):
        """全角コロンのテスト"""
        assert time_to_seconds("3：30：00") == 12600


class TestSecondsToTime:
    """seconds_to_time関数のテスト"""
    
    def test_basic_conversion(self):
        """基本的な変換テスト"""
        assert seconds_to_time(330) == "5:30"  # 5分30秒
        assert seconds_to_time(1800) == "30:00"  # 30分
    
    def test_with_hours(self):
        """時間を含む変換テスト"""
        assert seconds_to_time(12600, include_hours=True) == "3:30:00"
        assert seconds_to_time(3661, include_hours=True) == "1:01:01"
    
    def test_auto_hours(self):
        """時間が1以上の場合の自動変換"""
        assert seconds_to_time(3600) == "1:00:00"  # 1時間
        assert seconds_to_time(7200) == "2:00:00"  # 2時間
    
    def test_none_input(self):
        """None入力のテスト"""
        assert seconds_to_time(None) == "N/A"
    
    def test_zero(self):
        """0秒のテスト"""
        assert seconds_to_time(0) == "0:00"


class TestVdotCalculation:
    """VDOT計算の統合テスト（CSVデータを使用）"""
    
    @pytest.fixture
    def df_vdot(self):
        """テスト用VDOTデータフレーム"""
        import pandas as pd
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "vdot_list.csv"
        )
        return pd.read_csv(data_path)
    
    def test_vdot_calculation_sub3(self, df_vdot):
        """サブ3（VDOT 54付近）のテスト"""
        from src.vdot.calculator import calculate_vdot_from_time
        
        # 3時間 = 10800秒
        result = calculate_vdot_from_time(df_vdot, "フルマラソン", 10800)
        
        assert result["vdot"] is not None
        # サブ3はVDOT 54前後
        assert 53 <= result["vdot"] <= 55
    
    def test_vdot_calculation_sub4(self, df_vdot):
        """サブ4（VDOT 40付近）のテスト"""
        from src.vdot.calculator import calculate_vdot_from_time
        
        # 4時間 = 14400秒
        result = calculate_vdot_from_time(df_vdot, "フルマラソン", 14400)
        
        assert result["vdot"] is not None
        # サブ4はVDOT 37-38付近（実際のデータより）
        assert 37 <= result["vdot"] <= 39
    
    def test_invalid_distance(self, df_vdot):
        """無効な距離のテスト"""
        from src.vdot.calculator import calculate_vdot_from_time
        
        result = calculate_vdot_from_time(df_vdot, "100km", 36000)
        
        assert result["vdot"] is None
        assert "エラー" in result["calculation_log"]
