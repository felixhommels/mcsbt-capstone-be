from pydantic import BaseModel
from typing import Optional

class ManualFlight(BaseModel):
    user_id: str
    flight_number: Optional[str] = None
    date: str
    estimated_co2: Optional[float] = None
    airline_icao: Optional[str] = None
    airline_name: str = None
    aircraft: Optional[str] = None
    registration: Optional[str] = None
    estimated_time: Optional[str] = None
    estimated_distance: Optional[float] = None
    origin_iata: Optional[str] = None
    origin_name: str = None
    destination_iata: Optional[str] = None
    destination_name: str = None
    route: Optional[str] = None
    departure_time: Optional[str] = None
    timezone: Optional[str] = None

class RetrieveFlight(BaseModel):
    user_id: Optional[str] = None
    date: str
    flight_number: str
    departure_time: Optional[str] = None
    timezone: Optional[str] = None

class APIFlightData(BaseModel):
    fr24_id: str
    flight: str
    callsign: str
    lat: float
    lon: float
    track: int
    alt: int
    gspeed: int
    vspeed: int
    squawk: str
    timestamp: str
    source: str
    hex: str
    type: str
    reg: str
    painted_as: str
    operating_as: str
    orig_iata: str
    orig_icao: str
    dest_iata: str
    dest_icao: str
    eta: Optional[str] = None

class ProcessedFlightData(BaseModel):
    user_id: Optional[str] = None
    flight_number: str
    date: Optional[str] = None
    estimated_co2: float
    airline_icao: str
    airline_name: str
    aircraft: str
    registration: str
    estimated_time: str
    estimated_distance: float
    origin_iata: str
    origin_name: str
    destination_iata: str
    destination_name: str
    route: str
    departure_time: str
    timezone: Optional[str] = None
    dep_lat: float
    dep_lon: float
    arr_lat: float
    arr_lon: float

class FlightID(BaseModel):
    flight_id: str