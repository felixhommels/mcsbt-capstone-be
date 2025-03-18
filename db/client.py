from google.cloud import bigquery
from core.config import project_id

client = bigquery.Client(project=project_id)