from google.cloud import bigquery
from models.common import CO2Emissions

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