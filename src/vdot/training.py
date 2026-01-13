"""
AI Marathon Coach - Training Schedule
トレーニング期間の計算
"""
from datetime import datetime, timedelta

from ..config import MIN_TRAINING_WEEKS


def get_training_start_date(race_date: datetime, min_weeks: int = None) -> datetime:
    """トレーニング開始日を計算（最低12週確保、月曜始まり）
    
    Args:
        race_date: レース日
        min_weeks: 最低週数（デフォルトはMIN_TRAINING_WEEKS）
        
    Returns:
        トレーニング開始日（月曜日）
    """
    if min_weeks is None:
        min_weeks = MIN_TRAINING_WEEKS
    
    today = datetime.now()
    
    # レースまでの週数を計算
    days_until_race = (race_date - today).days
    weeks_until_race = days_until_race // 7
    
    # 12週未満の場合は過去に遡る
    if weeks_until_race < min_weeks:
        # レース日から12週前の月曜日を計算
        start_date = race_date - timedelta(weeks=min_weeks)
    else:
        # 今日から始める
        start_date = today
    
    # 月曜日に調整（次の月曜日）
    days_until_monday = (7 - start_date.weekday()) % 7
    if days_until_monday == 0 and start_date.weekday() != 0:
        days_until_monday = 7
    start_date = start_date + timedelta(days=days_until_monday)
    
    # もし開始日が月曜でない場合、前の月曜に調整
    if start_date.weekday() != 0:
        start_date = start_date - timedelta(days=start_date.weekday())
    
    return start_date
