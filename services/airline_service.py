from models.common import AirlineInfo
from google.cloud import bigquery

def get_airline_info(client: bigquery.Client, dataset_id:str, airline_table: str, icao_code: str) -> AirlineInfo:
    table_id = f"{client.project}.{dataset_id}.{airline_table}"
    query = f"""
    SELECT airline_name
    FROM `{table_id}`
    WHERE airline_icao = '{icao_code}'
    """

    result = client.query(query).result()
    return AirlineInfo(airline_name=next(result).airline_name)