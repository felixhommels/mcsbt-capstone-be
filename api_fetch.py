import requests
import os
import dotenv
import pytz
from datetime import datetime, timedelta
from models import APIFlightData

dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")

headers = {
    "Accept": "application/json",
    "Accept-Version": "v1",
    "Authorization": f"Bearer {API_KEY}"
}

def convert_to_utc_timestamp(time_str, timezone_str, date_str):
    local_tz = pytz.timezone(timezone_str)
    local_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    local_time = local_tz.localize(local_time)
    utc_time = local_time.astimezone(pytz.utc)
    return int(utc_time.timestamp())


def get_flight_data(flight_number: str, date: str, departure_time: str, timezone: str):
    # Date validation
    requested_date = datetime.strptime(date, "%Y-%m-%d").date()
    current_date = datetime.now().date()
    days_difference = (current_date - requested_date).days
    
    if days_difference > 30:
        return {
            "error": "Date too far in the past",
            "message": "Flight data is only available for the last 30 days"
        }

    url = "https://fr24api.flightradar24.com/api/historic/flight-positions/full"
    
    attempts = 0
    time_increment = [30, 60, 90, 120]
    max_attempts = len(time_increment)

    while attempts < max_attempts:
        api_call_time = datetime.strptime(f"{date} {departure_time}", "%Y-%m-%d %H:%M") + timedelta(minutes=time_increment[attempts])
        
        params = {
            "timestamp": f"{convert_to_utc_timestamp(api_call_time.strftime('%H:%M'), timezone, date)}",
            "flights": flight_number
        } 

        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
            flight_data = data["data"][0]
            return APIFlightData.model_validate(flight_data)
        
        attempts += 1  

    return {}


# print(get_flight_data("LX14", "2025-02-18", "13:00", "Europe/Zurich"))