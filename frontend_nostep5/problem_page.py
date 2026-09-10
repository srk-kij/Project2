import json
import streamlit as st
from api_client import api_request, show_result_message


def require_login():
    if st.session_state.get("user") is None:
        st.warning("Please login first.")
        return False
    return True


def problem_form(prefix: str, initial=None):
    initial = initial or {}

    problem_id = st.text_input(
        "Problem ID",
        value=initial.get("id", ""),
        key=f"{prefix}_id",
    )
    title = st.text_input(
        "Title",
        value=initial.get("title", ""),
        key=f"{prefix}_title",
    )
    description = st.text_area(
        "Description",
        value=initial.get("description", ""),
        key=f"{prefix}_description",
    )
    input_description = st.text_area(
        "Input description",
        value=initial.get("input_description", ""),
        key=f"{prefix}_input_description",
    )
    output_description = st.text_area(
        "Output description",
        value=initial.get("output_description", ""),
        key=f"{prefix}_output_description",
    )
    constraints = st.text_area(
        "Constraints",
        value=initial.get("constraints", ""),
        key=f"{prefix}_constraints",
    )

    samples_text = st.text_area(
        'Samples (JSON list, e.g. [{"input":"1 2","output":"3"}])',
        value=json.dumps(initial.get("samples", []), ensure_ascii=False, indent=2),
        key=f"{prefix}_samples",
        height=130,
    )
    testcases_text = st.text_area(
        'Testcases (JSON list, e.g. [{"input":"1 2","output":"3"}])',
        value=json.dumps(initial.get("testcases", []), ensure_ascii=False, indent=2),
        key=f"{prefix}_testcases",
        height=130,
    )

    hint = st.text_input("Hint", value=initial.get("hint", ""), key=f"{prefix}_hint")
    source = st.text_input("Source", value=initial.get("source", ""), key=f"{prefix}_source")
    tags_text = st.text_input(
        "Tags (comma separated)",
        value=", ".join(initial.get("tags", [])),
        key=f"{prefix}_tags",
    )
    time_limit = st.number_input(
        "Time limit (s)",
        min_value=0.01,
        value=float(initial.get("time_limit", 3.0)),
        key=f"{prefix}_time_limit",
    )
    memory_limit = st.number_input(
        "Memory limit (MB)",
        min_value=1,
        value=int(initial.get("memory_limit", 128)),
        step=1,
        key=f"{prefix}_memory_limit",
    )
    author = st.text_input("Author", value=initial.get("author", ""), key=f"{prefix}_author")
    difficulty = st.text_input(
        "Difficulty",
        value=initial.get("difficulty", ""),
        key=f"{prefix}_difficulty",
    )

    try:
        samples = json.loads(samples_text)
        testcases = json.loads(testcases_text)
    except json.JSONDecodeError:
        return None, "Samples and testcases must be valid JSON."

    if not isinstance(samples, list) or not isinstance(testcases, list):
        return None, "Samples and testcases must be JSON lists."

    for item in samples + testcases:
        if not isinstance(item, dict) or "input" not in item or "output" not in item:
            return None, 'Every sample/testcase must contain "input" and "output".'

    required = {
        "id": problem_id.strip(),
        "title": title.strip(),
        "description": description,
        "input_description": input_description,
        "output_description": output_description,
        "constraints": constraints,
    }
    if any(value == "" for value in required.values()):
        return None, "Please fill all required text fields."

    problem = {
        **required,
        "samples": samples,
        "testcases": testcases,
        "hint": hint,
        "source": source,
        "tags": [x.strip() for x in tags_text.split(",") if x.strip()],
        "time_limit": float(time_limit),
        "memory_limit": int(memory_limit),
        "author": author,
        "difficulty": difficulty,
    }
    return problem, None


def show_problem_detail(problem):
    st.subheader(f"{problem.get('id', '')} - {problem.get('title', '')}")
    st.write(problem.get("description", ""))

    st.markdown("**Input**")
    st.write(problem.get("input_description", ""))

    st.markdown("**Output**")
    st.write(problem.get("output_description", ""))

    st.markdown("**Constraints**")
    st.write(problem.get("constraints", ""))

    st.markdown("**Samples**")
    for i, sample in enumerate(problem.get("samples", []), start=1):
        st.write(f"Sample {i}")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Input")
            st.code(sample.get("input", ""))
        with c2:
            st.caption("Output")
            st.code(sample.get("output", ""))

    st.caption(
        f"Time: {problem.get('time_limit', 3)} s | "
        f"Memory: {problem.get('memory_limit', 128)} MB | "
        f"Difficulty: {problem.get('difficulty', '')}"
    )


def show_problem_page():
    st.header("Problems")
    if not require_login():
        return

    list_tab, detail_tab, add_tab, edit_tab, delete_tab = st.tabs(
        ["List", "Detail", "Add", "Edit", "Delete"]
    )

    with list_tab:
        if st.button("Load problem list"):
            result = api_request("GET", "/api/problems/")
            if result["ok"]:
                st.dataframe(result["data"] or [], use_container_width=True)
            else:
                show_result_message(result)

    with detail_tab:
        problem_id = st.text_input("Problem ID", key="detail_problem_id")
        if st.button("Load problem", key="load_problem_detail"):
            result = api_request("GET", f"/api/problems/{problem_id}")
            if result["ok"]:
                show_problem_detail(result["data"] or {})
            else:
                show_result_message(result)

    with add_tab:
        with st.form("add_problem_form"):
            problem, error = problem_form("add")
            submitted = st.form_submit_button("Add problem")

        if submitted:
            if error:
                st.error(error)
            else:
                result = api_request("POST", "/api/problems/", json=problem)
                show_result_message(result)

    with edit_tab:
        st.caption("Load an existing problem first, then edit it.")
        edit_id = st.text_input("Problem ID to edit", key="edit_lookup_id")

        if st.button("Load for editing"):
            result = api_request("GET", f"/api/problems/{edit_id}")
            if result["ok"]:
                st.session_state.edit_problem = result["data"]
                st.rerun()
            else:
                show_result_message(result)

        initial = st.session_state.get("edit_problem")
        if initial:
            st.info(f"Editing {initial.get('id', '')}")
            with st.form("edit_problem_form"):
                problem, error = problem_form("edit", initial)
                submitted = st.form_submit_button("Save changes")

            if submitted:
                if error:
                    st.error(error)
                elif problem["id"] != initial.get("id"):
                    st.error("The request body ID must match the problem ID being edited.")
                else:
                    result = api_request(
                        "PUT",
                        f"/api/problems/{initial['id']}",
                        json=problem,
                    )
                    show_result_message(result)
                    if result["ok"]:
                        st.session_state.edit_problem = problem

    with delete_tab:
        if st.session_state.user.get("role") != "admin":
            st.warning("Only administrators can delete problems.")
        else:
            delete_id = st.text_input("Problem ID to delete")
            confirm = st.checkbox("I confirm that I want to delete this problem.")
            if st.button("Delete problem", disabled=not confirm):
                result = api_request("DELETE", f"/api/problems/{delete_id}")
                show_result_message(result)
