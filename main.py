from fastapi import FastAPI
from fastapi.responses import JSONResponse

import json
import os


app = FastAPI()


@app.get("/")
async def root():
    return {
        "message": "OJ server is running"
    }


@app.get("/test-problem")
async def test_problem():
    with open(
        "problems/P1001.json",
        "r",
        encoding="utf-8"
    ) as f:
        problem = json.load(f)

    return problem


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
        problem = json.load(f)

    return {
        "code": 200,
        "msg": "success",
        "data": problem
    }