from utils.time import convert_to_utc_timestamp
from models.flight import APIFlightData
from datetime import datetime, timedelta
import requests
from core.config import API_KEY

headers = {
    "Accept": "application/json",
    "Accept-Version": "v1",
    "Authorization": f"Bearer {API_KEY}"
}

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