import json
from src.ai.gemini_client import convert_json_to_markdown

mock_json = """
{
    "plan": {
        "introduction": "This is a test plan.",
        "basic_info": {
            "target_race": "Tokyo Marathon",
            "target_time": "3:00:00",
            "weekly_mileage": "60km",
            "current_vdot": 50.0,
            "target_vdot": 53.0
        },
        "vdot_paces": {
            "phase_1": {
                "E": "5:00",
                "M": "4:15/km",
                "T": "4:00/km",
                "I": "3:40",
                "R": "3:20"
            },
            "phase_2": {
                "E": "4:55",
                "M": "4:10/km",
                "T": "3:55/km",
                "I": "3:35",
                "R": "3:15"
            }
        },
        "phase_overview": "Overview of phases.",
        "weekly_schedules": [
            {
                "week": 1,
                "dates": "10/01 - 10/07",
                "days": [
                    {
                        "date": "10/01 (Mon)",
                        "menu": "Rest",
                        "distance": "0km",
                        "pace": "N/A",
                        "advice": "Rest well."
                    }
                ],
                "total_distance": "0km"
            }
        ],
        "precautions": ["P1", "P2"],
        "coach_message": "Good luck!",
        "footer": "Test footer"
    }
}
"""

md = convert_json_to_markdown(mock_json)
print(md)
