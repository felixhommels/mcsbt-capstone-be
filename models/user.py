from pydantic import BaseModel

class User(BaseModel):
    name: str
    surname: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserID(BaseModel):
    user_id: str

class UserUpdatePassword(BaseModel):
    user_id: str
    password: str

class UserUpdateEmail(BaseModel):
    user_id: str
    email: str