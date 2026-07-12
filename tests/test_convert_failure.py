"""convert_json_to_markdown の失敗パスのテスト

途中切断されたJSON（max_output_tokens到達等）で (None, 0, None) が返り、
例外を投げないことを確認する。診断ログの出力内容も検証する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.gemini_client import convert_json_to_markdown


TRUNCATED_JSON = '{"plan": {"weekly_schedules": [{"week": 1, "days": [{"menu": "Eジョグ'


class TestConvertFailure:
    """変換失敗パスのテスト"""

    def test_truncated_json_returns_none_tuple(self):
        assert convert_json_to_markdown(TRUNCATED_JSON) == (None, 0, None)

    def test_truncated_json_logs_diagnostics(self, capsys):
        convert_json_to_markdown(TRUNCATED_JSON)
        out = capsys.readouterr().out
        assert "JSON修復失敗" in out
        assert "応答長=" in out
        assert "末尾200字=" in out

    def test_empty_and_garbage_input(self):
        assert convert_json_to_markdown("") == (None, 0, None)
        assert convert_json_to_markdown("これはJSONではありません") == (None, 0, None)
