"""
AI Marathon Coach - VDOT Package
VDOTの計算とペース管理
"""
from .calculator import (
    time_to_seconds,
    seconds_to_time,
    calculate_vdot_from_time,
    calculate_marathon_time_from_vdot,
)
from .paces import (
    calculate_training_paces,
    calculate_phase_vdots,
)
from .training import get_training_start_date
