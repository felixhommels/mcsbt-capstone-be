from pydantic import BaseModel

class AirportInfo(BaseModel):
    iata_code: str
    name: str
    lat: float
    long: float

class AirlineInfo(BaseModel):
    airline_name: str

class CO2Emissions(BaseModel):
    co2_emission_for_flight: float

class RouteInfo(BaseModel):
    dep_iata: str
    arr_iata:str