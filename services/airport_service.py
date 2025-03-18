from google.cloud import bigquery
from models.common import AirportInfo
from typing import Dict

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