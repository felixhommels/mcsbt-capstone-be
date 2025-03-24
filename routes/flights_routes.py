from fastapi import APIRouter, Depends
import fastapi
from db.client import client
from core.config import dataset_id, airport_table, flights_table, airline_table, co2_table
from api.get_flight import get_flight_data
from services.emissions_service import calculate_flight_emissions
from services.airport_service import get_airport_info
from services.airline_service import get_airline_info
from utils.geo import compute_distance
from utils.time import format_duration_as_time, estimate_flight_duration
from core.security import verify_token
from models.flight import ManualFlight, RetrieveFlight, FlightID
from google.cloud import bigquery
import uuid

router = APIRouter()

@router.get("/flights", summary="Get flights", description="Get all flights for a user.")
def get_flights(user_id: str, token: str = Depends(verify_token)):
    if user_id:
        table_id = f"{client.project}.{dataset_id}.{flights_table}"

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
            ]
        )

        query = f"""
        SELECT * FROM `{table_id}` 
        WHERE user_id = @user_id 
        AND (deleted = FALSE OR deleted IS NULL)
        AND flight_id NOT IN (
            SELECT flight_id 
            FROM `{table_id}` 
            WHERE user_id = @user_id 
            AND deleted = TRUE
        )
        """
        
        query_job = client.query(query, job_config=job_config)
        flights = query_job.result()
        flights_list = [dict(row) for row in flights]
        return flights_list
    else:
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": "User ID is required"})
    
@router.post("/add-flight-manual", summary="Add a flight manually", description="Add a flight manually with a flight number, date, estimated co2, airline, aircraft, registration, estimated time, estimated distance, origin, destination, route, departure time, and timezone.")
def add_flight(flight: ManualFlight, token: str = Depends(verify_token)):
    flight_id = str(uuid.uuid4())

    airport_info = get_airport_info(client, dataset_id, airport_table, [flight.origin_iata, flight.destination_iata])

    flight_data = {
        "flight_id": flight_id,
        "user_id": flight.user_id,
        "flight_number": flight.flight_number,
        "date": flight.date,
        "estimated_co2": flight.estimated_co2,
        "airline_icao": flight.airline_icao,
        "airline_name": flight.airline_name,
        "aircraft": flight.aircraft,
        "registration": flight.registration,
        "estimated_time": flight.estimated_time,
        "estimated_distance": flight.estimated_distance,
        "origin_iata": flight.origin_iata,
        "origin_name": flight.origin_name,
        "destination_iata": flight.destination_iata,
        "destination_name": flight.destination_name,
        "route": flight.route,
        "departure_time": flight.departure_time,
        "timezone": flight.timezone,
        "dep_lat": airport_info[flight.origin_iata].lat,
        "dep_long": airport_info[flight.origin_iata].long,
        "arr_lat": airport_info[flight.destination_iata].lat,
        "arr_long": airport_info[flight.destination_iata].long
    }

    table_id = f"{client.project}.{dataset_id}.{flights_table}"
    errors = client.insert_rows_json(table_id, [flight_data])

    if errors:
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": errors})

    return fastapi.responses.JSONResponse(status_code=201, content={"message": "Flight added successfully!"})

@router.post("/add-flight-api", summary="Add a flight from API", description="Add a flight from API with a flight number, date, departure time, and timezone.")
def add_flight_api(flight: RetrieveFlight, token: str = Depends(verify_token)):
    user_id = flight.user_id
    flight_number = flight.flight_number
    date = flight.date
    departure_time = flight.departure_time
    timezone = flight.timezone
    flight_id = str(uuid.uuid4())

    # This is returning a APIFlightData object
    api_flight_data = get_flight_data(flight.flight_number, flight.date, flight.departure_time, flight.timezone)

    # This is returning a dictionary of AirportInfo objects
    airport_info = get_airport_info(client, dataset_id, airport_table, [api_flight_data.orig_iata, api_flight_data.dest_iata])

    # Compute distance between origin and destination
    origin = airport_info[api_flight_data.orig_iata]
    destination = airport_info[api_flight_data.dest_iata]

    estimated_distance = compute_distance(origin.lat, origin.long, destination.lat, destination.long)

    # Estimated times
    computational_time = estimate_flight_duration(estimated_distance)
    db_estimated_time = format_duration_as_time(computational_time)

    # This is returning a AirlineInfo object
    airline_info = get_airline_info(client, dataset_id, airline_table, api_flight_data.operating_as)

    # This is returning a CO2Emissions object
    estimated_emissions = calculate_flight_emissions(client, dataset_id, co2_table, api_flight_data.type, computational_time)

    # Add flight to database
    insert_flight_data = {
        "user_id": user_id,
        "flight_id": flight_id,
        "flight_number": flight_number,
        "date": date,
        "departure_time": departure_time,
        "timezone": timezone,
        "estimated_co2": estimated_emissions.co2_emission_for_flight,
        "airline_icao": api_flight_data.operating_as,
        "airline_name": airline_info.airline_name,
        "aircraft": api_flight_data.type,
        "registration": api_flight_data.reg,
        "estimated_time": db_estimated_time,
        "estimated_distance": int(estimated_distance),
        "origin_iata": api_flight_data.orig_iata,
        "origin_name": origin.name,
        "destination_iata": api_flight_data.dest_iata,
        "destination_name": destination.name,
        "route": f"{api_flight_data.orig_iata} - {api_flight_data.dest_iata}",
        "dep_lat": origin.lat,
        "dep_long": origin.long,
        "arr_lat": destination.lat,
        "arr_long": destination.long 
    }

    table_id = f"{client.project}.{dataset_id}.{flights_table}"
    errors = client.insert_rows_json(table_id, [insert_flight_data])

    if errors:
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": errors})

    return fastapi.responses.JSONResponse(status_code=201, content={"message": "Flight added successfully!"})

@router.delete("/delete-flight", summary="Delete a flight", description="Delete a flight with a flight ID.")
def delete_flight(flight_id: FlightID, token: str = Depends(verify_token)):
    if flight_id:
        try:
            table_id = f"{client.project}.{dataset_id}.{flights_table}"

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("flight_id", "STRING", flight_id.flight_id)
                ]
            )

            query = f"DELETE FROM `{table_id}` WHERE flight_id = @flight_id"
            query_job = client.query(query, job_config=job_config)
            query_job.result()
        except Exception as e:
            return fastapi.responses.JSONResponse(status_code=500, content={"message": f"Error deleting flight: {str(e)}"})

        return fastapi.responses.JSONResponse(status_code=200, content={"message": "Flight deleted successfully!"})
    else:
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": "Flight ID is required"})
    
@router.post("/soft-delete-flight", summary="Soft delete a flight", description="Soft delete a flight with a flight ID.")
def soft_delete_flight(flight_id: FlightID, token: str = Depends(verify_token)):
    if flight_id:
        try:
            table_id = f"{client.project}.{dataset_id}.{flights_table}"
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("flight_id", "STRING", flight_id.flight_id)
                ]
            )
            
            query = f"SELECT * FROM `{table_id}` WHERE flight_id = @flight_id"
            query_job = client.query(query, job_config=job_config)
            results = list(query_job.result())
            
            if not results:
                return fastapi.responses.JSONResponse(
                    status_code=404, 
                    content={"error": f"Flight with ID {flight_id.flight_id} not found"}
                )
            
            flight_dict = dict(results[0])
            
            for key, value in flight_dict.items():
                if hasattr(value, 'isoformat') and callable(getattr(value, 'isoformat')):
                    flight_dict[key] = value.isoformat()
                elif isinstance(value, (complex, set, frozenset)):
                    flight_dict[key] = str(value)
            
            flight_dict["deleted"] = True
            
            rows_to_insert = [flight_dict]
            
            errors = client.insert_rows_json(table_id, rows_to_insert)
            
            if errors:
                return fastapi.responses.JSONResponse(
                    status_code=500, 
                    content={"error": f"Error inserting data: {errors}"}
                )
            
            return {"message": f"Flight with ID {flight_id.flight_id} has been soft-deleted successfully"}
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in soft-delete: {str(e)}")
            print(f"Traceback: {error_trace}")
            
            return fastapi.responses.JSONResponse(
                status_code=500, 
                content={"error": f"An error occurred: {str(e)}"}
            )
    else:
        return fastapi.responses.JSONResponse(
            status_code=400, 
            content={"error": "Flight ID is required"}
        )
    