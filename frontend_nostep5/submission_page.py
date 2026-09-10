import streamlit as st
from api_client import api_request, show_result_message


def require_login():
    if st.session_state.get("user") is None:
        st.warning("Please login first.")
        return False
    return True


def render_submission(data):
    if not data:
        return

    st.write("Submission ID:", data.get("submission_id", ""))

    status = data.get("status", "")
    if status == "pending":
        st.write("Evaluation status: Pending")
    elif status == "success":
        st.write("Evaluation status: Finished")
    elif status == "error":
        st.write("Evaluation status: System Error")
    else:
        st.write("Evaluation status:", status)

    compile_info = data.get("compile_info")
    run_info = data.get("run_info")

    judge_result = None

    if compile_info and compile_info.get("result") in {"CE", "UNK"}:
        judge_result = compile_info.get("result")
    elif run_info:
        judge_result = run_info.get("result")

    if judge_result:
        st.markdown(f"### Judge Result: `{judge_result}`")

    if data.get("score") is not None:
        st.metric("Score", f"{data.get('score')} / {data.get('counts')}")

    if compile_info is not None:
        st.markdown("#### Compile information")
        st.json(compile_info)

    if run_info is not None:
        st.markdown("#### Run information")
        st.json(run_info)

    error_info = data.get("error_info")
    if error_info:
        st.error(str(error_info))

    if data.get("status") == "pending":
        st.info("The submission is still pending. Click Check result again later.")


def show_submission_page():
    st.header("Submissions")
    if not require_login():
        return

    submit_tab, result_tab, history_tab, rejudge_tab = st.tabs(
        ["Submit", "Result", "History", "Rejudge"]
    )

    with submit_tab:
        lang_result = api_request("GET", "/api/languages/")
        languages = []
        if lang_result["ok"]:
            languages = (lang_result["data"] or {}).get("name", [])

        with st.form("submission_form"):
            problem_id = st.text_input("Problem ID")
            if languages:
                language = st.selectbox("Language", languages)
            else:
                language = st.text_input("Language")
            code = st.text_area("Code", height=350)
            submitted = st.form_submit_button("Submit code")

        if submitted:
            if not problem_id.strip() or not language.strip() or not code.strip():
                st.error("Problem ID, language and code are required.")
            else:
                result = api_request(
                    "POST",
                    "/api/submissions/",
                    json={
                        "problem_id": problem_id.strip(),
                        "language": language.strip(),
                        "code": code,
                    },
                )
                if result["ok"]:
                    st.session_state.last_submission_id = result["data"]["submission_id"]
                    show_result_message(result, "Submission created")
                    render_submission(result["data"])
                else:
                    show_result_message(result)

    with result_tab:
        submission_id = st.text_input(
            "Submission ID",
            value=st.session_state.get("last_submission_id", ""),
            key="result_submission_id",
        )
        if st.button("Check result"):
            result = api_request("GET", f"/api/submissions/{submission_id}")
            if result["ok"]:
                render_submission(result["data"])
            else:
                show_result_message(result)

        st.caption(
            "This Step 6 version intentionally does not use the Step 5 testcase-log API. "
            "It displays the overall compile/run/error information returned by Steps 2-3."
        )

    with history_tab:
        user = st.session_state.user
        st.caption("At least user_id or problem_id must be supplied.")

        default_user = "" if user.get("role") == "admin" else user.get("user_id", "")
        user_id = st.text_input("User ID", value=default_user, key="history_user_id")
        problem_id = st.text_input("Problem ID", key="history_problem_id")
        status = st.text_input("Status (optional)", key="history_status")

        c1, c2 = st.columns(2)
        with c1:
            page = st.number_input("Page", min_value=1, value=1, step=1, key="history_page")
        with c2:
            page_size = st.number_input(
                "Page size",
                min_value=1,
                value=20,
                step=1,
                key="history_page_size",
            )

        if st.button("Load submissions"):
            if not user_id.strip() and not problem_id.strip():
                st.error("Provide user_id or problem_id.")
            else:
                params = {
                    "page": int(page),
                    "page_size": int(page_size),
                }
                if user_id.strip():
                    params["user_id"] = user_id.strip()
                if problem_id.strip():
                    params["problem_id"] = problem_id.strip()
                if status.strip():
                    params["status"] = status.strip()

                result = api_request("GET", "/api/submissions/", params=params)
                if result["ok"]:
                    data = result["data"] or {}
                    st.write("Total:", data.get("total", 0))
                    st.dataframe(data.get("submissions", []), use_container_width=True)
                else:
                    show_result_message(result)

    with rejudge_tab:
        if st.session_state.user.get("role") != "admin":
            st.warning("Only administrators can rejudge submissions.")
        else:
            submission_id = st.text_input("Submission ID to rejudge")
            if st.button("Rejudge"):
                result = api_request(
                    "PUT",
                    f"/api/submissions/{submission_id}/rejudge",
                )
                if result["ok"] and result["data"]:
                    st.session_state.last_submission_id = result["data"].get(
                        "submission_id", submission_id
                    )
                show_result_message(result)
