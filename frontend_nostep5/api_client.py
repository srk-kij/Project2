import requests
import streamlit as st


DEFAULT_BASE_URL = "http://127.0.0.1:8000"

# Our FastAPI application runs using: `uvicorn main:app --reload`
# By default, it is located at: `http://127.0.0.1:8000`
# However, this URL does not yet have an endpoint. Suppose we want: `GET /api/problems/`
# The program combines the two parts:
# `http://127.0.0.1:8000` + `/api/problems/`  -->  `http://127.0.0.1:8000/api/problems/`


def init_api_state(): # prepare the state required by the frontend.
    # If a session for communicating with FastAPI does not yet exist, create one.
    if "api_session" not in st.session_state:
        st.session_state.api_session = requests.Session()
    # If `st.session_state.backend_url` does not yet exist, set the default value to `http://127.0.0.1:8000`.
    if "backend_url" not in st.session_state:
        st.session_state.backend_url = DEFAULT_BASE_URL


def api_request(method: str, path: str, json=None, params=None):
    init_api_state()

    # method   = GET / POST / PUT / DELETE
    # path     = endpoint
    # json     = request body
    # params   = query parameters

    # Example:
    #     api_request(
    #         "POST",
    #         "/api/auth/login",
    #         json={
    #             "username": "alice",
    #             "password": "1234"
    #         }
    #     )

    base_url = st.session_state.backend_url.rstrip("/")  # create url, by deleting `/` from the right
    # Because our path already contains a `/`: path = "/api/problems/"
    # url = base_url + path --> http://127.0.0.1:8000/api/problems/
    url = base_url + path

    try:
        response = st.session_state.api_session.request(
            method=method,
            url=url,
            json=json,
            params=params,
            # api_request(
            #     "GET",
            #     "/api/submissions/",
            #     params={
            #         "page": 1,
            #         "page_size": 20
            #     }
            # )
            # --> GET /api/submissions/?page=1&page_size=20
            timeout=15,
        )
    except requests.RequestException as e: # cannot connect to FastAPI.
        return {
            "http_status": None,
            "ok": False,
            "code": 500,
            "msg": f"cannot connect to backend: {e}",
            "data": None,
        }

    try:
        body = response.json() # convert JSON into Python dict
    except ValueError:
        return {
            "http_status": response.status_code,
            "ok": False,
            "code": response.status_code,
            "msg": "backend did not return JSON",
            "data": None,
        }

    code = body.get("code", response.status_code)
    ok = response.status_code == 200 and code == 200

    return {
        "http_status": response.status_code,
        "ok": ok,
        "code": code,
        "msg": body.get("msg", ""),
        "data": body.get("data"),
    }


def show_result_message(result, success_text=None):
    if result["ok"]:
        st.success(success_text or result["msg"] or "success")
    else:
        http_status = result.get("http_status")
        prefix = f"HTTP {http_status} / code {result['code']}" if http_status is not None else f"code {result['code']}"
        st.error(f"{prefix}: {result['msg']}")
