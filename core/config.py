import os
import dotenv

dotenv.load_dotenv()

# Project details
project_id = "capstone-felixh"
dataset_id = "capstone"

# Tables
user_table = os.getenv("USERS_TABLE")
flights_table = os.getenv("FLIGHTS_TABLE")
airport_table = os.getenv("AIRPORTS_TABLE")
airline_table = os.getenv("AIRLINES_TABLE")
co2_table = os.getenv("CO2_TABLE")

# Authentication
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# External APIs
AS_API_KEY = os.getenv("AS_API_KEY")
AS_API_URL = os.getenv("AS_API_URL")
API_KEY = os.getenv("API_KEY")