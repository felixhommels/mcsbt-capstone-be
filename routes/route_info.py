from fastapi import APIRouter, Depends
from utility import verify_token, AS_API_KEY, AS_API_URL
import requests
from datetime import datetime

router = APIRouter()

@router.get("/route-info", summary="Get route information", description="Retrieve route information based on departure and arrival IATA codes. Used for the add flight based on route feature.")
def get_route_info(dep_iata: str, arr_iata: str, token: str = Depends(verify_token)):
    url = f"{AS_API_URL}?access_key={AS_API_KEY}&dep_iata={dep_iata}&arr_iata={arr_iata}"
    response = requests.get(url)
    data = response.json()

    route_data = {}

    if "data" in data:
        for flight in data["data"]:
            flight_key = (
                flight["flight"]["iata"],  
                flight["airline"]["name"],  
                flight["departure"]["iata"],  
                flight["arrival"]["iata"]
            )
            if flight_key not in route_data:
                route_data[flight_key] = flight["departure"]

    route_data_list = [
        {
            "flightNumber": key[0],
            "airline": key[1],
            "timezone": route_data[key]["timezone"],
            "scheduledDepartureTime": datetime.fromisoformat(route_data[key]["scheduled"]).strftime("%H:%M"),
            "origin": key[2],
            "destination": key[3]
        }
        for key in route_data
    ]

    return route_data_list