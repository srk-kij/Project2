from pydantic import BaseModel, Field


class UserCredentials(BaseModel):
    username: str = Field(min_length=3, max_length=40) # username must be a string and between 3 and 40 characters long.
    password: str = Field(min_length=6) 


class RoleUpdate(BaseModel):
    role: str
    # {
    #     "role": "admin"
    # }
    # or
    # {
    #     "role": "user"
    # }
    # or
    # {
    #     "role": "banned"
    # }
    # example: role_update.role  -->  "admin"
