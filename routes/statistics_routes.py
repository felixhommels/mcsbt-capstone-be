from fastapi import APIRouter, Depends
from core.security import verify_token
from core.config import dataset_id, flights_table
from db.client import client
from utils.time import convert_time
from google.cloud import bigquery
import fastapi

router = APIRouter()

@router.get("/statistics", summary="Get statistics", description="Get statistics for a user based on their flights. Used for dashboard.")
def get_statistics(user_id: str, token: str = Depends(verify_token)):
    if user_id:
        table_id = f"{client.project}.{dataset_id}.{flights_table}"

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
            ]
        )

        query = f"SELECT * FROM `{table_id}` WHERE user_id = @user_id"
        query_job = client.query(query, job_config=job_config)
        flights = query_job.result()
        flights_dict = [dict(row) for row in flights]

        total_distance = sum(flight["estimated_distance"] if flight["estimated_distance"] is not None else 0 for flight in flights_dict)
        total_flights = len(flights_dict)
        total_carbon = sum(flight["estimated_co2"] if flight["estimated_co2"] is not None else 0 for flight in flights_dict)
        total_time = sum(convert_time(flight["estimated_time"]) if flight["estimated_time"] is not None else 0 for flight in flights_dict)

        top_airports = {}
        top_airlines = {}
        top_aircraft = {}
        top_routes = {}

        for flight in flights_dict:
            origin = flight.get('origin_iata')
            destination = flight.get('destination_iata')
            airline = flight.get('airline_name')
            aircraft = flight.get('aircraft')
            route = flight.get('route')

            if origin is not None:
                top_airports[origin] = top_airports.get(origin, 0) + 1
            if destination is not None:
                top_airports[destination] = top_airports.get(destination, 0) + 1
            if airline is not None:
                top_airlines[airline] = top_airlines.get(airline, 0) + 1
            if aircraft is not None:
                top_aircraft[aircraft] = top_aircraft.get(aircraft, 0) + 1
            if route is not None:
                top_routes[route] = top_routes.get(route, 0) + 1

        return {
            "total_distance": total_distance,
            "total_flights": total_flights,
            "total_carbon": round(total_carbon, 2),
            "total_time": convert_time(total_time),
            "top_airports": top_airports,
            "top_airlines": top_airlines,
            "top_aircraft": top_aircraft,
            "top_routes": top_routes
        }
    else:
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": "User ID is required"})