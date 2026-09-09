from fastapi import FastAPI, Request
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
#
# end - step2
#

app = FastAPI()


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
async def get_problems():
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
async def get_problem(problem_id: str):
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
async def add_problem(problem: Problem):

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
    problem: Problem
):
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
async def delete_problem(problem_id: str):

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
    submission: Submission
):

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
    submission_id: str
):

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
    submission_id: str
):

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
async def get_languages(): # see all language

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "name": list(languages.keys())
        }
    }
    # Example: in `language_manager.py`:
    #     @app.get("/api/languages/")
    #     async def get_languages(): # see all language
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
    language: LanguageConfig # class LanguageConfig(BaseModel): in `step2_models.py`
): # The 'language' parameter will become an object with a structure based on LanguageConfig.
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
    
    