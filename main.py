import fastapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends
from google.cloud import bigquery
from datetime import datetime
import bcrypt
import uvicorn
import uuid
from api_fetch import get_flight_data
from models import User, ManualFlight, RetrieveFlight, UserID, FlightID, UserLogin, UserUpdatePassword, UserUpdateEmail
import os
import dotenv
from utility import get_airport_info, get_airline_info, calculate_flight_emissions, compute_distance, format_duration_as_time, estimate_flight_duration, verify_token, create_access_token, get_user, verify_password, convert_time
import requests

dotenv.load_dotenv()

app = FastAPI()
client = bigquery.Client(project="capstone-felixh")
dataset_id = "capstone"

app.add_middleware(
       CORSMiddleware,
       allow_origins=["*", "http://localhost:5173"],  # Allow all origins
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )

user_table = os.getenv("USERS_TABLE")
flights_table = os.getenv("FLIGHTS_TABLE")
airport_table = os.getenv("AIRPORTS_TABLE")
airline_table = os.getenv("AIRLINES_TABLE")
co2_table = os.getenv("CO2_TABLE")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

AS_API_KEY = os.getenv("AS_API_KEY")
AS_API_URL = os.getenv("AS_API_URL")

@app.post("/new-user")
def new_user(user: User):
    if get_user(user.email):
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": "User already exists"})

    user_id = str(uuid.uuid4())
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    user_data = {
        "user_id": user_id,
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "password_hash": hashed_password,
        "created_at": datetime.utcnow().isoformat()
    }

    table_id = f"{client.project}.{dataset_id}.{user_table}"
    errors = client.insert_rows_json(table_id, [user_data])

    if errors:
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": errors})

    return fastapi.responses.JSONResponse(status_code=201, content={"message": "User created successfully!"})

@app.delete("/delete-user")
def delete_user(user: UserID, token: str = Depends(verify_token)):
    flights_table_id = f"{client.project}.{dataset_id}.{flights_table}"
    
    flights_query = f"DELETE FROM `{flights_table_id}` WHERE user_id = @user_id"
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("user_id", "STRING", user.user_id)
        ]
    )

    try:
        flights_query_job = client.query(flights_query, job_config=job_config)
        flights_query_job.result()
    except Exception as e:
        return fastapi.responses.JSONResponse(
            status_code=500, 
            content={"message": f"Error deleting associated flights: {str(e)}"}
        )

    user_table_id = f"{client.project}.{dataset_id}.{user_table}"
    
    user_query = f"DELETE FROM `{user_table_id}` WHERE user_id = @user_id"
    
    try:
        user_query_job = client.query(user_query, job_config=job_config)
        user_query_job.result()
    except Exception as e:
        return fastapi.responses.JSONResponse(
            status_code=500, 
            content={"message": f"Error deleting user: {str(e)}"}
        )

    return fastapi.responses.JSONResponse(
        status_code=200, 
        content={"message": "User and associated flights deleted successfully!"}
    )

@app.post("/login")
def login(user: UserLogin):
    user_fetched = get_user(user.email)
    if user_fetched is None or verify_password(user.password, user_fetched["password_hash"]) is False:
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": "User not found or invalid credentials"})
    else:
        jwt_data = {
            "user_id": user_fetched["user_id"],
            "email": user_fetched["email"],
            "name": user_fetched["name"],
            "surname": user_fetched["surname"]
        }
        access_token = create_access_token(jwt_data)
        return fastapi.responses.JSONResponse(status_code=200, content={"access_token": access_token})


#Get flights for a specific user - used for the flights page
@app.get("/flights")
def get_flights(user_id: str, token: str = Depends(verify_token)):
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
        flights_list = [dict(row) for row in flights]
        return flights_list
    else:
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": "User ID is required"})
    
#Get Overall statistics for a specific user - used for the dashboard
@app.get("/statistics")
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
    
@app.post("/add-flight-manual")
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

@app.post("/add-flight-api")
def add_flight_api(flight: RetrieveFlight, token: str = Depends(verify_token)):
    user_id = flight.user_id
    flight_number = flight.flight_number
    date = flight.date
    departure_time = flight.departure_time
    timezone = flight.timezone
    flight_id = str(uuid.uuid4())

    #This is returning a APIFlightData object
    api_flight_data = get_flight_data(flight.flight_number, flight.date, flight.departure_time, flight.timezone)

    #This is returning a dictionary of AirportInfo objects
    airport_info = get_airport_info(client, dataset_id, airport_table, [api_flight_data.orig_iata, api_flight_data.dest_iata])

    #Compute distance between origin and destination
    origin = airport_info[api_flight_data.orig_iata]
    destination = airport_info[api_flight_data.dest_iata]

    estimated_distance = compute_distance(origin.lat, origin.long, destination.lat, destination.long)

    #Estimated times
    computational_time = estimate_flight_duration(estimated_distance)
    db_estimated_time = format_duration_as_time(computational_time)

    #This is returning a AirlineInfo object
    airline_info = get_airline_info(client, dataset_id, airline_table, api_flight_data.operating_as)

    #This is returning a CO2Emissions object
    estimated_emissions = calculate_flight_emissions(client, dataset_id, co2_table, api_flight_data.type, computational_time)


    #Add flight to database
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

@app.delete("/delete-flight")
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
    
@app.post("/update-password")
def update_password(user: UserUpdatePassword, token: str = Depends(verify_token)):
    if user.user_id:
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        table_id = f"{client.project}.{dataset_id}.{user_table}"

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user.user_id)
            ]
        )

        query = f"UPDATE `{table_id}` SET password_hash = '{hashed_password}' WHERE user_id = @user_id"
        
        try:
            query_job = client.query(query, job_config=job_config)
            query_job.result()
            return fastapi.responses.JSONResponse(status_code=200, content={"message": "Password updated successfully!"})
        except Exception as e:
            return fastapi.responses.JSONResponse(status_code=500, content={"message": f"Error updating password: {str(e)}"})
    else:
        return fastapi.responses.JSONResponse(status_code=400, content={"message": "User ID is required"})
    
@app.post("/update-email")
def update_email(user: UserUpdateEmail, token: str = Depends(verify_token)):
    if user.user_id:

        table_id = f"{client.project}.{dataset_id}.{user_table}"

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user.user_id)
            ]
        )
        query = f"UPDATE `{table_id}` SET email = '{user.email}' WHERE user_id = @user_id"
        
        try:
            query_job = client.query(query, job_config=job_config)
            query_job.result()
            return fastapi.responses.JSONResponse(status_code=200, content={"message": "Email updated successfully!"})
        except Exception as e:
            return fastapi.responses.JSONResponse(status_code=500, content={"message": f"Error updating email: {str(e)}"})
    else:
        return fastapi.responses.JSONResponse(status_code=400, content={"message": "User ID is required"})
    
@app.get("/route-info")
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

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
    # uvicorn.run("main:app", reload=True)