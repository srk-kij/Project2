from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse# error
from fastapi.exceptions import RequestValidationError #error

from pydantic import BaseModel, Field

import json
import os

#
# step2
#
import asyncio
import uuid
from step2_models import Submission, LanguageConfig
from judge import judge_submission
from language_manager import languages, validate_language_config, DEFAULT_TIME_LIMIT, DEFAULT_MEMORY_LIMIT
from submission_store import submissions
from step4_models import UserCredentials, RoleUpdate
from user_store import users, username_to_id, create_user, verify_password, initialize_admin
#
# end - step2
#

app = FastAPI()

#
# Step 4 - Session cookie
#
app.add_middleware(
    SessionMiddleware, # SessionMiddleware enables FastAPI to use `request.session`
    # Example: After a successful login, we might store:
    # request.session["user_id"] = user["user_id"]
    # Therefore, for future requests, the browser sends the session back to the server, 
    # allowing the server to recognize that "this person has already logged in."
    secret_key="oj-step4-secret-key"
    # Used to sign session cookies to prevent unauthorized tampering with session data.
)

# System must create the initial administrator automatically.
initialize_admin() # calls a function from `user_store.py`

#helper function
def error_response(status_code: int, message: str):
    return JSONResponse(
        status_code=status_code,
        content={
            "code": status_code,
            "msg": message,
            "data": None
        }
    )
# return JSONResponse(
#     status_code=401,
#     content={
#         "code": 401,
#         "msg": "not logged in",     --->
#         "data": None
#     }
# )                             
# return error_response(401, "not logged in")

def current_user(request: Request):
    user_id = request.session.get("user_id")

    if user_id is None or user_id not in users:
        return None

    return users[user_id]


def require_login(request: Request):
    user = current_user(request)

    if user is None:
        return None, error_response(401, "not logged in")

    # A user who became banned must also lose access through an old session.
    if user["role"] == "banned":
        return None, error_response(403, "user banned")

    return user, None


def require_admin(request: Request):
    user, error = require_login(request)

    if error is not None:
        return None, error

    if user["role"] != "admin":
        return None, error_response(403, "permission denied")

    return user, None


def get_user_statistics(user_id: str):
    submit_count = 0
    resolved_problems = set() # want to count the number of unique problems solved

    for submission in submissions.values():
        if submission.get("user_id") != user_id: # Check if the submission belongs to this user
            continue

        submit_count += 1

        if ( # This condition means the submission must be fully evaluated and receive the maximum score.
            submission.get("status") == "success"
            and submission.get("score") is not None
            and submission.get("counts") is not None
            and submission.get("score") == submission.get("counts")
        ):
            resolved_problems.add(submission["problem_id"])

    return submit_count, len(resolved_problems)


def public_user_data(user): # create "secure user data for API export"
    submit_count, resolve_count = get_user_statistics(user["user_id"])

    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "join_time": user["join_time"],
        "role": user["role"],
        "submit_count": submit_count,
        "resolve_count": resolve_count
    }
#
# end - step4
#

#
# step1
#

# Convert FastAPI/Pydantic validation error from 422 to 400
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "msg": "invalid request parameters",
            "data": None
        }
    )


# Handle unknown server errors
@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "msg": "internal server error",
            "data": None
        }
    )


class Sample(BaseModel):
    input: str
    output: str


class Problem(BaseModel):
    id: str
    title: str
    description: str
    input_description: str
    output_description: str
    samples: list[Sample]
    constraints: str
    testcases: list[Sample]

    hint: str = ""
    source: str = ""
    tags: list[str] = Field(default_factory=list)
    time_limit: float = 3
    memory_limit: int = 128
    author: str = ""
    difficulty: str = ""


@app.get("/")
async def root():
    return {
        "message": "OJ server is running"
    }


@app.get("/api/problems/")
async def get_problems(request: Request):
    user, error = require_login(request)
    if error is not None:
        return error

    problems = []

    for filename in os.listdir("problems"):
        if filename.endswith(".json"):
            path = os.path.join(
                "problems",
                filename
            )

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as f:
                problem = json.load(f)

            problems.append({
                "id": problem["id"],
                "title": problem["title"]
            })

    return {
        "code": 200,
        "msg": "success",
        "data": problems
    }


@app.get("/api/problems/{problem_id}")
async def get_problem(problem_id: str, request: Request):
    user, error = require_login(request)
    if error is not None:
        return error

    path = os.path.join(
        "problems",
        f"{problem_id}.json"
    )

    if not os.path.exists(path):
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "msg": "problem not found",
                "data": None
            }
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:
        raw_problem = json.load(f)

    problem = Problem(**raw_problem)

    return {
        "code": 200,
        "msg": "success",
        "data": problem.model_dump()
    }


@app.post("/api/problems/")
async def add_problem(problem: Problem, request: Request):
    user, error = require_login(request)
    if error is not None:
        return error


    path = os.path.join(
        "problems",
        f"{problem.id}.json"
    )

    if os.path.exists(path):
        return JSONResponse(
            status_code=409,
            content={
                "code": 409,
                "msg": "problem id already exists",
                "data": None
            }
        )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump( # select Python Object (dict) and write as JSON into `f` file
            problem.model_dump(), # Pydantic object -> .model_dump() -> Python dict
            f,
            ensure_ascii=False, # Make Unicode characters such as Chinese are written directly
            indent=4
            # change from {"id": "P1001", "title": "A + B", "description": "Calculate A + B"}
            # into
            # {
            #     "id": "P1001",
            #     "title": "A + B",
            #     "description": "Calculate A + B"
            # }
        )

    return {
        "code": 200,
        "msg": "add success",
        "data": {
            "id": problem.id
        }
    }


@app.put("/api/problems/{problem_id}")
async def update_problem(
    problem_id: str,
    problem: Problem,
    request: Request
):
    user, error = require_login(request)
    if error is not None:
        return error

    if problem_id != problem.id: # ID in URL ,ust ,atch ID in JSON body
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "msg": "problem id mismatch",
                "data": None
            }
        )

    path = os.path.join(
        "problems",
        f"{problem_id}.json"
    )

    if not os.path.exists(path): # The problem must exist
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "msg": "problem not found",
                "data": None
            }
        )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            problem.model_dump(),
            f,
            ensure_ascii=False,
            indent=4
        )

    return {
        "code": 200,
        "msg": "update success",
        "data": {
            "id": problem_id
        }
    }


@app.delete("/api/problems/{problem_id}")
async def delete_problem(problem_id: str, request: Request):
    user, error = require_admin(request)
    if error is not None:
        return error


    path = os.path.join(
        "problems",
        f"{problem_id}.json"
    )

    if not os.path.exists(path):
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "msg": "problem not found",
                "data": None
            }
        )

    os.remove(path)

    return {
        "code": 200,
        "msg": "delete success",
        "data": {
            "id": problem_id
        }
    }

#
# end - step1
#
    
# 
# step2 - submission
# 

@app.post("/api/submissions/")
async def create_submission(
    submission: Submission,
    request: Request
):
    user, error = require_login(request)
    if error is not None:
        return error


    problem_path = os.path.join(
        "problems",
        f"{submission.problem_id}.json"
    )

    # Problem does not exist
    if not os.path.exists(problem_path):

        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "msg": "problem not found",
                "data": None
            }
        )

    # Language does not exist
    if (submission.language not in languages): ########################

        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "msg": "language not found",
                "data": None
            }
        )

    submission_id = str(uuid.uuid4())
    # Create a unique ID for each submission.
    # UUID is a Python module for generating UUIDs (Universally Unique Identifiers). -->  import uuid
    # uuid.uuid4() --> 550e8400-e29b-41d4-a716-446655440000 
    # str(...) --> "550e8400-e29b-41d4-a716-446655440000"
    # Why does OJ require a submission_id?
        # Because multiple users can submit their code multiple times, for example:
        # Submission 1:
        # submission_id = "abc..."
        # Submission 2:
        # submission_id = "xyz..."
        # Submission 3:
        # submission_id = "def..."

    submissions[submission_id] = {
        "submission_id": submission_id,
        "user_id": user["user_id"],
        "status": "pending",
        "problem_id": submission.problem_id,
        "language": submission.language,
        "code": submission.code,

        "score": None,
        "counts": None,
        "compile_info": None,
        "run_info": None,
        "error_info": ""
    }

    # Judge in background
    asyncio.create_task(
        judge_submission(submission_id, submission)
        # This coroutine will judge this submission by passing two pieces of information:
        # 1. submission_id → The ID of this submission
        # 2. submission → Problem_id, language, and code submitted by the user
    )
    # asyncio.create_task(...) = Take that coroutine, create it into a task, and then use an event loop to run it.

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "submission_id": submission_id,
            "status": "pending"
        }
    }

#
# step3 - submission list
#

@app.get("/api/submissions/")
async def get_submissions( # 5 query parameters
    request: Request,
    user_id: str | None = None, # None = dafault value
    problem_id: str | None = None,
    status: str | None = None,
    page: int | None = None,
    page_size: int | None = None
):
    
# 5 query parameters:
# example: /api/submissions/?problem_id=P1001&status=success&page=1&page_size=10
# user_id = None
# problem_id = "P1001"
# status = "success"
# page = 1
# page_size = 10

    user, error = require_login(request)
    if error is not None:
        return error

    # A normal user can only query their own submissions.
    # If user_id is omitted and problem_id is given, normal users see only
    # their own records for that problem; admins may see everybody's.
    if user["role"] != "admin":
        if user_id is not None and user_id != user["user_id"]:
            return error_response(403, "permission denied")

        if user_id is None:
            user_id = user["user_id"]

    # user_id and problem_id are primary conditions.
    # At least one of them must be given.
    if (user_id is None and problem_id is None):
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "msg": "user_id or problem_id required",
                "data": None
            }
        )

    # page cannot exist without page_size
    if (page is not None and page_size is None):
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "msg": "page_size is required when page is provided",
                "data": None
            }
        )

    # page must be positive
    if (page is not None and page <= 0):
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "msg": "page must be greater than 0",
                "data": None
            }
        )

    # page_size must be positive
    if (page_size is not None and page_size <= 0):
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "msg": "page_size must be greater than 0",
                "data": None
            }
        )

    # Submission task status
    if (status is not None
        and status not in ["pending", "success", "error"]
    ):
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "msg": "invalid status",
                "data": None
            }
        )

    result = []
    # Create a list to store the results; initially, it is empty. 
    # Then, iterate through all submissions and select only those that match the filter.
    
# Example:
# submissions = {
#     "s1": {
#         "problem_id": "P1001",
#         "status": "success"
#     },

#     "s2": {
#         "problem_id": "P1002",
#         "status": "pending"
#     }
# }
#
# .items() first time ->
# submission_id = "s1"
# submission = {
#     "problem_id": "P1001",
#     "status": "success"
# }
# .items() second time ->
# submission_id = "s2"
# submission = {
#     "problem_id": "P1002",
#     "status": "pending"
# }
    
    for submission_id, submission in submissions.items(): # from submission_store.py
    # The `for` loop iterates through each submission in the system to check 
    # if it meets the conditions requested by the user.
    
    # If the submission_id are s1, s2, s3, and s4 
    # s1 → problem=P1001, status=success
    # s2 → problem=P1001, status=pending
    # s3 → problem=P1002, status=success
    # s4 → problem=P1001, status=success

    #                 problem=P1001?    status=success?    result
    # s1                       ✅                 ✅          MATCH
    # s2                       ✅                 ❌          skip (continue)
    # s3                       ❌                              skip (continue)
    # s4                       ✅                 ✅          MATCH

        # Filter by user
        #
        # Step 4 will add the real user system.
        # We prepare this field here first.
        if (user_id is not None and submission.get("user_id") != user_id):
            continue
        # If request: user_id = 1, then user_id = "u1"
        # If the current submission: "user_id": "u2"
        # u1 != u2 -> continue: Finish this round, then jump straight to the next submission
        # Therefore, u2 was not included in the result

        # Filter by problem
        if (problem_id is not None and submission["problem_id"] != problem_id):
            continue

        # Filter by status
        if (status is not None and submission["status"] != status):
            continue

        # pending / error only need
        # submission_id and status
        if submission["status"] in ["pending", "error"]:
            result.append({
                "submission_id": submission_id,
                "status": submission["status"]
            })

        # successful judging task
        else:
            result.append({
                "submission_id": submission_id,
                "status": submission["status"],
                "score": submission["score"],
                "counts": submission["counts"] # fullscore
            })

    # total = number of all matched submissions
    # BEFORE pagination
    total = len(result)

    #
    # Pagination
    #

    # page_size exists but page does not exist
    # means first page ***
    if (page is None and page_size is not None):
        page = 1
    if (page is not None and page_size is not None):
        start = (page - 1) * page_size
        end = start + page_size
        result = result[start:end]

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "total": total,
            "submissions": result
        }
    }

# View details of a single submission.
@app.get("/api/submissions/{submission_id}")
async def get_submission(
    submission_id: str,
    request: Request
):
    user, error = require_login(request)
    if error is not None:
        return error


    if (submission_id not in submissions):
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "msg": "submission not found",
                "data": None
            }
        )

    submission = submissions[submission_id]

    if (
        user["role"] != "admin"
        and submission.get("user_id") != user["user_id"]
    ):
        return error_response(403, "permission denied")

    # Pending only needs id + status
    if (submission["status"] == "pending"):
        return {
            "code": 200,
            "msg": "success",
            "data": {"submission_id": submission_id,
                "status": "pending"}
        }

    return {
        "code": 200,
        "msg": "success",

        "data": {
            "submission_id": submission_id,
            "status": submission["status"],
            "score": submission.get("score"),
            "counts": submission.get("counts"),
            "compile_info": submission.get("compile_info"),
            "run_info": submission.get("run_info"),
            "error_info":submission.get("error_info", "")
        }
    }

#
# step3 - rejudge
#

# Suppose the fault lies with us—such as an incorrect test case or a problem with the judging system. 
# Once we have fixed the system, we should not force users to resubmit their original code, 
# as the issue did not originate with them.
@app.put(
    "/api/submissions/{submission_id}/rejudge"
)
async def rejudge_submission(
    submission_id: str,
    request: Request
):
    user, error = require_admin(request)
    if error is not None:
        return error


    # Submission does not exist
    if submission_id not in submissions:

        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "msg": "submission not found",
                "data": None
            }
        )

    old_submission = submissions[submission_id]

    # Rebuild the Submission object because
    # judge_submission() receives a Submission object,
    # not a dictionary.
    submission = Submission(
        problem_id=old_submission["problem_id"],
        language=old_submission["language"],
        code=old_submission["code"]
    )

    # Clear old judging result
    submissions[submission_id].update({
        "status": "pending",
        "score": None,
        "counts": None,
        "compile_info": None,
        "run_info": None,
        "error_info": ""
    })

    # Judge the same submission again.
    # Do NOT create a new submission_id.
    asyncio.create_task(
        judge_submission(
            submission_id,
            submission
        )
    )

    return {
        "code": 200,
        "msg": "rejudge started",
        "data": {
            "submission_id": submission_id,
            "status": "pending"
        }
    }

# --------------------------------
# step1 - Languages
# --------------------------------

@app.get("/api/languages/")
async def get_languages(request: Request): # see all language
    user, error = require_login(request)
    if error is not None:
        return error


    return {
        "code": 200,
        "msg": "success",
        "data": {
            "name": list(languages.keys())
        }
    }
    # Example: in `language_manager.py`:
    #     @app.get("/api/languages/")
    #     async def get_languages(request: Request): # see all language
    #       user, error = require_login(request)
    #       if error is not None:
    #       return error

    #         return {
    #             "code": 200,
    #             "msg": "success",
    #             "data": {
    #                 "name": list(languages.keys())
    #             }
    #         }
    # languages.keys() -> dict(["python", "cpp"]) --> convert into list
    # Therefore, API:
            # {
            #     "code": 200,
            #     "msg": "success",
            #     "data": {
            #         "name": ["python", "cpp"]
            #     }
            # }


@app.post("/api/languages/")
async def register_language( # Add a new language
    language: LanguageConfig, # class LanguageConfig(BaseModel): in `step2_models.py`
    request: Request
):
    user, error = require_login(request)
    if error is not None:
        return error
 # The 'language' parameter will become an object with a structure based on LanguageConfig.
   # now we can use language.name, language.file_ext, ...

    valid, message = validate_language_config(language)
    # return valide = True, message = ""
    # If it does not pass: return False, "invalid language name"
    # Therefore, valid = False, message = "invalid language name"
    if not valid: # valide = False

        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "msg": message,
                "data": None
            }
        )

    if (language.name in languages): # Check if this language already exists.
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "msg":
                    "language already exists",
                "data": None
            }
        )

    if language.time_limit is not None:
        time_limit = language.time_limit
    else:
        time_limit = DEFAULT_TIME_LIMIT

    if language.memory_limit is not None:
        memory_limit = language.memory_limit
    else:
        memory_limit = DEFAULT_MEMORY_LIMIT

    languages[language.name] = {
        "file_ext": language.file_ext,
        "compile_cmd": language.compile_cmd,
        "run_cmd": language.run_cmd,
        "time_limit": time_limit,
        "memory_limit": memory_limit
    }

    return {
        "code": 200,
        "msg": "language registered",
        "data": {
            "name": language.name
        }
    }
# end - Languages
    

# --------------------------------
# step4 - Users and authentication
# --------------------------------

@app.post("/api/auth/login")
async def login(
    credentials: UserCredentials, # from step4_models
    request: Request
):
    
# The client must send a POST request to `/api/auth/login` with JSON in this format:
# {
# "username": "qingqing",
# "password": "123456"
# }
# FastAPI automatically converts this JSON into a `UserCredentials` object for us, so we can use:
# credentials.username
# credentials.password

    # (1)
    user_id = username_to_id.get(credentials.username) # use the entered username to look up the user_id.

    # (2)
    if user_id is None:
        return error_response(401, "invalid username or password")
    # (1) and (2)
    # Here, the provided username is used to look up the `user_id`.
    # For example:
    # `username_to_id = { "qingqing": "abc-123" }`
    # If logging in with "qingqing":
    # `user_id = "abc-123"`
    # But if the username does not exist:
    # `user_id = None`
    # Then:
    # `if user_id is None: return error_response(401, "invalid username or password")`
    # If the username is not found, the login fails.
    # 401 indicates that authentication failed.

    user = users[user_id]

    if not verify_password( # check whether the entered password matches the stored hash
        credentials.password,
        user["password_hash"]
    ):
        return error_response(401, "invalid username or password")

    if user["role"] == "banned":
        return error_response(403, "user banned")

    request.session["user_id"] = user_id # Used to remember who is logged in

    return {
        "code": 200,
        "msg": "login success",
        "data": {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"]
        }
    }


@app.post("/api/auth/logout")
async def logout(request: Request): # FastAPI sends the request to us, allowing us to access `request.session`.
    
    user, error = require_login(request)
    # If logged in:
    # user = {...}
    # error = None

    # If not logged in:
    # user = None
    # error = JSONResponse(...)
    # return error
    if error is not None:
        return error

    request.session.clear() # This clears all data in the session.
    # {
    #     "user_id": "abc-123"  --->  { }
    # }

    # So, the next time the API calls 
    #     `current_user(request)`:
    # `user_id = request.session.get("user_id")` will return:
    # `None`
    # And the system will know that this user is not logged in


    return {
        "code": 200,
        "msg": "logout success",
        "data": None
    }


@app.post("/api/users/admin")
async def create_admin(
    credentials: UserCredentials, # from step4_models
    request: Request
):
    admin, error = require_admin(request)
    if error is not None:
        return error

    if credentials.username in username_to_id:
        return error_response(400, "username already exists")

    user = create_user(
        credentials.username,
        credentials.password,
        role="admin"
    )

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "user_id": user["user_id"],
            "username": user["username"]
        }
    }


@app.post("/api/users/")
async def register_user(credentials: UserCredentials): # from step4_models
    if credentials.username in username_to_id:
        return error_response(400, "username already exists")

    user = create_user(
        credentials.username,
        credentials.password,
        role="user"
    )

    return {
        "code": 200,
        "msg": "register success",
        "data": public_user_data(user)
    }


@app.get("/api/users/{user_id}")
async def get_user_info(
    user_id: str,
    request: Request
):
    current, error = require_login(request)
    if error is not None:
        return error

    if user_id not in users:
        return error_response(404, "user not found")

    if (
        current["role"] != "admin"
        and current["user_id"] != user_id
    ):
        return error_response(403, "permission denied")

    return {
        "code": 200,
        "msg": "success",
        "data": public_user_data(users[user_id])
    }


@app.put("/api/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_update: RoleUpdate,
    request: Request
):
    admin, error = require_admin(request)
    if error is not None:
        return error

    if role_update.role not in ["user", "admin", "banned"]:
        return error_response(400, "invalid role")

    if user_id not in users:
        return error_response(404, "user not found")

    users[user_id]["role"] = role_update.role

    return {
        "code": 200,
        "msg": "role updated",
        "data": {
            "user_id": user_id,
            "role": role_update.role
        }
    }


@app.get("/api/users/")
async def get_users(
    request: Request,
    page: int | None = None,
    page_size: int | None = None
):
    admin, error = require_admin(request)
    if error is not None:
        return error

    if page is not None and page_size is None:
        return error_response(400, "page_size is required when page is provided")

    if page is not None and page <= 0:
        return error_response(400, "page must be greater than 0")

    if page_size is not None and page_size <= 0:
        return error_response(400, "page_size must be greater than 0")

    result = []

    for user in users.values():
        result.append(
            public_user_data(user) # For every user in `users`, 
                                   # pass that user through `public_user_data()` 
                                   # and collect all the results into a list -> `result`
        )

    total = len(result)

    if page is None and page_size is not None:
        page = 1

    if page is not None and page_size is not None:
        start = (page - 1) * page_size
        end = start + page_size
        result = result[start:end]

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "total": total,
            "users": result
        }
    }
    
#
# end - step4
#
