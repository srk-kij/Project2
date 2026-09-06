from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse# error
from fastapi.exceptions import RequestValidationError #error

from pydantic import BaseModel, Field

import json
import os


app = FastAPI()


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