from datetime import datetime
import uuid # It was previously used in Step 3 to generate virtually unique IDs, 
            # such as: 550e8400-e29b-41d4-a716-446655440000.

import bcrypt #  hash password, for example, 123456 -> $2b$12$QhS7Yj....


# In-memory user storage for Step 4.
# The structure is similar to submission_store.py so it stays easy to understand.
users = {} # Used to store user data, using `user_id` as the key.
# For example, 
# users = {
#     "abc-123": {
#         "user_id": "abc-123",
#         "username": "qingqing",
#         "password_hash": "...",
#         "join_time": "2026-09-09",
#         "role": "user"
#     }
# }
# If we know `user_id`:
#     users["abc-123"]
# get the information for that user immediately

username_to_id = {} 
# users use user_id as a key: users[user_id]
# cannot search with "qingqing", so we create another dictionary
# username_to_id = {
#   "qingqing": "abc-123"
# }

# now we have:
#   user_id = username_to_id["qingqing"]
#   user = users[user_id]


# input real password, then convert into hashed password
def hash_password(password: str) -> str:
    return bcrypt.hashpw( # hash password
        password.encode("utf-8"), # Because bcrypt requires data in bytes,
                                  # the string "123456" becomes b"123456".
        bcrypt.gensalt() # A "salt" is random data combined with a password before hashing, 
                         # ensuring that the same password does not necessarily result in the same hash.
                         # hash_password("123456") and hash_password("123456") 
                         # They might result in different values.
        # ***
    ).decode("utf-8") # convert byte into string
    
def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )


def create_user(username: str, password: str, role: str = "user"): # default value of 'role' is 'user', create_user("qingqing", "123456") = create_user("qingqing", "123456", "user")
    # admin -> create_user("qingqing", "123456", "admin")
    user_id = str(uuid.uuid4())

    user = {
        "user_id": user_id,
        "username": username,
        "password_hash": hash_password(password),
        "join_time": datetime.now().strftime("%Y-%m-%d"),
        "role": role
    }

    users[user_id] = user
    # user_id = "abc-123"  -->
    # users = {
    #     "abc-123": {
    #         ...
    #     }
    # }
    username_to_id[username] = user_id
    # username_to_id = {
    #     "qingqing": "abc-123"
    # }
    return user


def initialize_admin(): # create the initial OJ admin account
    if "admin" not in username_to_id:
        create_user(
            username="admin",
            password="admintestpassword",
            role="admin"
        )
