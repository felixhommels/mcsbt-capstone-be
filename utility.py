from models import APIFlightData, ProcessedFlightData, AirportInfo, AirlineInfo, CO2Emissions
from math import radians, sin, cos, sqrt, atan2
from google.cloud import bigquery
from typing import Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt as pyjwt
from datetime import datetime, timedelta
import os
import bcrypt
import dotenv

dotenv.load_dotenv()

client = bigquery.Client(project="capstone-felixh")
dataset_id = "capstone"
security = HTTPBearer()

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


def compute_distance(start_latitude: float, start_longitude: float, end_latitude: float, end_longitude: float) -> float:
    # Using haversine formula
    R = 6371.0  # radius earth in km

    start_latitude, start_longitude, end_latitude, end_longitude = map(radians, [start_latitude, start_longitude, end_latitude, end_longitude])

    delta_longitude = end_longitude - start_longitude
    delta_latitude = end_latitude - start_latitude

    haversine_a = sin(delta_latitude / 2)**2 + cos(start_latitude) * cos(end_latitude) * sin(delta_longitude / 2)**2
    haversine_c = 2 * atan2(sqrt(haversine_a), sqrt(1 - haversine_a))

    distance = round(R * haversine_c, 2)

    return distance

def format_duration_as_time(hours: float) -> str:
    whole_hours = int(hours)
    minutes = int((hours - whole_hours) * 60)
    return f"{whole_hours:02d}:{minutes:02d}"

def estimate_flight_duration(distance: float) -> float:
    average_speed = 850  # km/h
    return distance / average_speed

def get_airport_info(client: bigquery.Client, dataset_id: str, airport_table: str, iata_codes: list[str]) -> Dict[str, AirportInfo]:
    table_id = f"{client.project}.{dataset_id}.{airport_table}"
    # Convert list of codes to comma-separated string of quoted values
    iata_codes_str = "', '".join(iata_codes)
    query = f"""
    SELECT iata_code, name, lat, long 
    FROM `{table_id}` 
    WHERE iata_code IN ('{iata_codes_str}')
    """
    results = client.query(query).result()
    return {row.iata_code: AirportInfo(**dict(row)) for row in results}

def get_airline_info(client: bigquery.Client, dataset_id:str, airline_table: str, icao_code: str) -> AirlineInfo:
    table_id = f"{client.project}.{dataset_id}.{airline_table}"
    query = f"""
    SELECT airline_name
    FROM `{table_id}`
    WHERE airline_icao = '{icao_code}'
    """

    result = client.query(query).result()
    return AirlineInfo(airline_name=next(result).airline_name)

def calculate_flight_emissions(
    client: bigquery.Client, 
    dataset_id: str, 
    co2_table: str, 
    aircraft_code: str, 
    flight_duration_hours: float
) -> CO2Emissions:
    
    table_id = f"{client.project}.{dataset_id}.{co2_table}"
    query = f"""
    SELECT co2_per_hour_per_passenger 
    FROM `{table_id}` 
    WHERE aircraft_code = '{aircraft_code}'
    """
    result = client.query(query).result()
    first_row = next(result)
    
    emissions_per_hour = first_row[0]
    return CO2Emissions(co2_emission_for_flight=round(emissions_per_hour * flight_duration_hours, 2))
    
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

def get_user(email: str):
    table_id = f"{client.project}.{dataset_id}.{user_table}"
    query = f"SELECT * FROM `{table_id}` WHERE email = @email"

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("email", "STRING", email)
        ]
    )

    query_job = client.query(query, job_config=job_config)
    user_data = query_job.result()
    user_data_dict = [dict(row) for row in user_data]
    if len(user_data_dict) == 0:
        return None
    else:
        return user_data_dict[0]

def verify_password(plain_password: str, hashed_password: str):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except pyjwt.exceptions.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired"
        )
    except pyjwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Could not validate credentials"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Authentication error: {str(e)}"
        )

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(to_encode, os.getenv("SECRET_KEY"), algorithm=os.getenv("ALGORITHM"))
    return encoded_jwt
