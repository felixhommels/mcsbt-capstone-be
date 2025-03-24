from models.common import AirlineInfo
from google.cloud import bigquery

def get_airline_info(client: bigquery.Client, dataset_id:str, airline_table: str, icao_code: str) -> AirlineInfo:
    try:
        table_id = f"{client.project}.{dataset_id}.{airline_table}"
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("icao_code", "STRING", icao_code)
            ]
        )
        
        query = f"""
        SELECT airline_name
        FROM `{table_id}`
        WHERE airline_icao = @icao_code
        """

        result = client.query(query, job_config=job_config).result()
        
        results_list = list(result)
        
        if not results_list:
            return AirlineInfo(airline_name="Unknown")
        
        first_row = results_list[0]
        
        return AirlineInfo(airline_name=first_row.airline_name)
    except Exception as e:
        print(f"Error getting airline info: {str(e)}")
        return AirlineInfo(airline_name="Unknown")