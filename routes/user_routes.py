from fastapi import APIRouter, Depends
from core.security import verify_token
from core.config import dataset_id, user_table, flights_table
from db.client import client
from db.queries import get_user
from models import User, UserLogin, UserUpdatePassword, UserUpdateEmail, UserID
from core.security import create_access_token, verify_password
from google.cloud import bigquery
import uuid
import bcrypt
from datetime import datetime
import fastapi

router = APIRouter()

@router.post("/new-user", summary="Create a new user", description="Create a new user with a name, surname, email, and password.")
def new_user(user: User):
    if get_user(user.email):
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": "User already exists"})

    user_id = str(uuid.uuid4())
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    user_data = {
        "user_id": user_id,
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "password_hash": hashed_password,
        "created_at": datetime.utcnow().isoformat()
    }

    table_id = f"{client.project}.{dataset_id}.{user_table}"
    errors = client.insert_rows_json(table_id, [user_data])

    if errors:
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": errors})

    return fastapi.responses.JSONResponse(status_code=201, content={"message": "User created successfully!"})

@router.delete("/delete-user", summary="Delete a user", description="Delete a user and all associated flights.")
def delete_user(user: UserID, token: str = Depends(verify_token)):
    flights_table_id = f"{client.project}.{dataset_id}.{flights_table}"
    
    flights_query = f"DELETE FROM `{flights_table_id}` WHERE user_id = @user_id"
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("user_id", "STRING", user.user_id)
        ]
    )

    try:
        flights_query_job = client.query(flights_query, job_config=job_config)
        flights_query_job.result()
    except Exception as e:
        return fastapi.responses.JSONResponse(
            status_code=500, 
            content={"message": f"Error deleting associated flights: {str(e)}"}
        )

    user_table_id = f"{client.project}.{dataset_id}.{user_table}"
    
    user_query = f"DELETE FROM `{user_table_id}` WHERE user_id = @user_id"
    
    try:
        user_query_job = client.query(user_query, job_config=job_config)
        user_query_job.result()
    except Exception as e:
        return fastapi.responses.JSONResponse(
            status_code=500, 
            content={"message": f"Error deleting user: {str(e)}"}
        )

    return fastapi.responses.JSONResponse(
        status_code=200, 
        content={"message": "User and associated flights deleted successfully!"}
    )

@router.post("/login", summary="Login a user", description="Login a user with an email and password.")
def login(user: UserLogin):
    user_fetched = get_user(user.email)
    if user_fetched is None or verify_password(user.password, user_fetched["password_hash"]) is False:
        return fastapi.responses.JSONResponse(status_code=400, content={"errors": "User not found or invalid credentials"})
    else:
        jwt_data = {
            "user_id": user_fetched["user_id"],
            "email": user_fetched["email"],
            "name": user_fetched["name"],
            "surname": user_fetched["surname"]
        }
        access_token = create_access_token(jwt_data)
        return fastapi.responses.JSONResponse(status_code=200, content={"access_token": access_token})
    
@router.post("/update-password", summary="Update a user's password", description="Update a user's password with a new password.")
def update_password(user: UserUpdatePassword, token: str = Depends(verify_token)):
    if user.user_id:
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        table_id = f"{client.project}.{dataset_id}.{user_table}"

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user.user_id)
            ]
        )

        query = f"UPDATE `{table_id}` SET password_hash = '{hashed_password}' WHERE user_id = @user_id"
        
        try:
            query_job = client.query(query, job_config=job_config)
            query_job.result()
            return fastapi.responses.JSONResponse(status_code=200, content={"message": "Password updated successfully!"})
        except Exception as e:
            return fastapi.responses.JSONResponse(status_code=500, content={"message": f"Error updating password: {str(e)}"})
    else:
        return fastapi.responses.JSONResponse(status_code=400, content={"message": "User ID is required"})
    
@router.post("/update-email", summary="Update a user's email", description="Update a user's email with a new email.")
def update_email(user: UserUpdateEmail, token: str = Depends(verify_token)):
    if user.user_id:
        table_id = f"{client.project}.{dataset_id}.{user_table}"

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user.user_id)
            ]
        )
        query = f"UPDATE `{table_id}` SET email = '{user.email}' WHERE user_id = @user_id"
        
        try:
            query_job = client.query(query, job_config=job_config)
            query_job.result()
            return fastapi.responses.JSONResponse(status_code=200, content={"message": "Email updated successfully!"})
        except Exception as e:
            return fastapi.responses.JSONResponse(status_code=500, content={"message": f"Error updating email: {str(e)}"})
    else:
        return fastapi.responses.JSONResponse(status_code=400, content={"message": "User ID is required"})