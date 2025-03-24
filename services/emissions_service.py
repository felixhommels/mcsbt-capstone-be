from google.cloud import bigquery
from models.common import CO2Emissions

def calculate_flight_emissions(
    client: bigquery.Client, 
    dataset_id: str, 
    co2_table: str, 
    aircraft_code: str, 
    flight_duration_hours: float
) -> CO2Emissions:
    
    try:
        table_id = f"{client.project}.{dataset_id}.{co2_table}"
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("aircraft_code", "STRING", aircraft_code)
            ]
        )
        
        query = f"""
        SELECT co2_per_hour_per_passenger 
        FROM `{table_id}` 
        WHERE aircraft_code = @aircraft_code
        """
        
        result = client.query(query, job_config=job_config).result()
        
        results_list = list(result)
        
        if not results_list:
            return CO2Emissions(co2_emission_for_flight=0)
        
        first_row = results_list[0]
        
        emissions_per_hour = first_row[0]
        return CO2Emissions(co2_emission_for_flight=round(emissions_per_hour * flight_duration_hours, 2))
    except Exception as e:
        print(f"Error calculating emissions: {str(e)}")
        return CO2Emissions(co2_emission_for_flight=0)