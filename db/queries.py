from db.client import client
from core.config import dataset_id, user_table
from google.cloud import bigquery

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