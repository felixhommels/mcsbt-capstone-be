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

        # Initialize statistics
        total_distance = sum(flight["estimated_distance"] if flight["estimated_distance"] is not None else 0 for flight in flights_dict)
        total_flights = len(flights_dict)
        total_carbon = sum(flight["estimated_co2"] if flight["estimated_co2"] is not None else 0 for flight in flights_dict)
        total_time = sum(convert_time(flight["estimated_time"]) if flight["estimated_time"] is not None else 0 for flight in flights_dict)

        # Initialize yearly statistics
        yearly_stats = {}
        
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
            
            # Extract year from flight date
            date = flight.get('date')
            year = None
            if date is not None:
                # Assuming flight_date is in a format that can be sliced for year
                # If it's a datetime object, you would use flight_date.year instead
                year = str(date)[:4]  # Adjust based on your date format
            
            # Update yearly statistics
            if year is not None:
                if year not in yearly_stats:
                    yearly_stats[year] = {
                        "total_distance": 0,
                        "total_flights": 0,
                        "total_carbon": 0,
                        "total_time": 0,
                        "top_airports": {},
                        "top_airlines": {},
                        "top_aircraft": {},
                        "top_routes": {}
                    }
                
                # Update yearly totals
                yearly_stats[year]["total_flights"] += 1
                yearly_stats[year]["total_distance"] += flight.get("estimated_distance", 0) or 0
                yearly_stats[year]["total_carbon"] += flight.get("estimated_co2", 0) or 0
                yearly_stats[year]["total_time"] += convert_time(flight.get("estimated_time", 0)) if flight.get("estimated_time") is not None else 0
                
                # Update yearly top items
                if origin is not None:
                    yearly_stats[year]["top_airports"][origin] = yearly_stats[year]["top_airports"].get(origin, 0) + 1
                if destination is not None:
                    yearly_stats[year]["top_airports"][destination] = yearly_stats[year]["top_airports"].get(destination, 0) + 1
                if airline is not None:
                    yearly_stats[year]["top_airlines"][airline] = yearly_stats[year]["top_airlines"].get(airline, 0) + 1
                if aircraft is not None:
                    yearly_stats[year]["top_aircraft"][aircraft] = yearly_stats[year]["top_aircraft"].get(aircraft, 0) + 1
                if route is not None:
                    yearly_stats[year]["top_routes"][route] = yearly_stats[year]["top_routes"].get(route, 0) + 1

            # Update overall top items
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
        
        # Round carbon values in yearly stats
        for year in yearly_stats:
            yearly_stats[year]["total_carbon"] = round(yearly_stats[year]["total_carbon"], 2)
            yearly_stats[year]["total_time"] = convert_time(yearly_stats[year]["total_time"])

        return {
            "total_distance": total_distance,
            "total_flights": total_flights,
            "total_carbon": round(total_carbon, 2),
            "total_time": convert_time(total_time),
            "top_airports": top_airports,
            "top_airlines": top_airlines,
            "top_aircraft": top_aircraft,
            "top_routes": top_routes,
            "yearly_statistics": yearly_stats
        }
    else:
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": "User ID is required"})