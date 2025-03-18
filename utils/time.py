import pytz
from datetime import datetime

def format_duration_as_time(hours: float) -> str:
    whole_hours = int(hours)
    minutes = int((hours - whole_hours) * 60)
    return f"{whole_hours:02d}:{minutes:02d}"

def estimate_flight_duration(distance: float) -> float:
    average_speed = 850  # km/h
    return distance / average_speed

def convert_time(time_input):
    if isinstance(time_input, str):
        # Convert from HH:MM to int
        hours, minutes = map(int, time_input.split(':'))
        return hours + minutes / 60
    elif isinstance(time_input, (int, float)):
        # Convert to HH:MM
        hours = int(time_input)
        minutes = int((time_input - hours) * 60)
        return f"{hours:02}:{minutes:02}"
    else:
        raise ValueError("Input must be a string in 'HH:MM' format or a number representing hours.")
    
def convert_to_utc_timestamp(time_str, timezone_str, date_str):
    local_tz = pytz.timezone(timezone_str)
    local_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    local_time = local_tz.localize(local_time)
    utc_time = local_time.astimezone(pytz.utc)
    return int(utc_time.timestamp())