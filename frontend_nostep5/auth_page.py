import streamlit as st
from api_client import api_request, show_result_message


def _save_login(data):
    st.session_state.user = data


def show_auth_page():
    st.header("User")

    user = st.session_state.get("user")

    if user is None:
        login_tab, register_tab = st.tabs(["Login", "Register"])

        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")

            if submitted:
                result = api_request(
                    "POST",
                    "/api/auth/login",
                    json={"username": username, "password": password},
                )
                if result["ok"]:
                    _save_login(result["data"])
                    st.success("Login success")
                    st.rerun()
                else:
                    show_result_message(result)

        with register_tab:
            with st.form("register_form"):
                username = st.text_input("Username", key="register_username")
                password = st.text_input("Password", type="password", key="register_password")
                submitted = st.form_submit_button("Register")

            if submitted:
                result = api_request(
                    "POST",
                    "/api/users/",
                    json={"username": username, "password": password},
                )
                if result["ok"]:
                    show_result_message(result, "Register success")
                    st.json(result["data"])
                else:
                    show_result_message(result)
        return

    st.success(f"Logged in as {user.get('username', '')}")
    st.write("User ID:", user.get("user_id", ""))
    st.write("Role:", user.get("role", ""))

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Refresh my information"):
            result = api_request("GET", f"/api/users/{user['user_id']}")
            if result["ok"]:
                st.session_state.user = {
                    **user,
                    **(result["data"] or {}),
                }
                st.json(result["data"])
            else:
                show_result_message(result)

    with col2:
        if st.button("Logout"):
            result = api_request("POST", "/api/auth/logout")
            if result["ok"]:
                st.session_state.user = None
                st.success("Logout success")
                st.rerun()
            else:
                show_result_message(result)

    if user.get("role") == "admin":
        st.divider()
        show_admin_management()


def show_admin_management():
    st.markdown("## Admin management")

    # --------------------------------
    # User list
    # --------------------------------

    st.markdown("#### User list")

    col1, col2 = st.columns(2)

    with col1:
        page = st.number_input(
            "Page",
            min_value=1,
            value=1,
            step=1
        )

    with col2:
        page_size = st.number_input(
            "Page size",
            min_value=1,
            value=10,
            step=1
        )

    if st.button("Load users"):

        result = api_request(
            "GET",
            "/api/users/",
            params={
                "page": int(page),
                "page_size": int(page_size)
            },
        )

        if result["ok"]:

            data = result["data"] or {}

            users = data.get(
                "users",
                []
            )

            # Save users in session_state
            # so Change user role can use them later.
            st.session_state.admin_users = users

            st.write(
                "Total:",
                data.get("total", 0)
            )

            st.dataframe(
                users,
                use_container_width=True
            )

        else:
            show_result_message(result)


    # --------------------------------
    # Change user role
    # --------------------------------

    st.markdown("#### Change user role")

    # Get the users loaded above.
    users = st.session_state.get(
        "admin_users",
        []
    )

    if not users:

        st.info(
            "Load users first."
        )

    else:

        # Convert:
        #
        # username -> user_id
        #
        # Example:
        # {
        #     "qingqing": "abc-123",
        #     "testuser": "def-456"
        # }
        user_options = {
            user["username"]: user["user_id"]
            for user in users
        }

        # users = [
        #     {
        #         "username": "admin",
        #         "user_id": "abc-123",
        #         "role": "admin"
        #     },
        #     {
        #         "username": "qingqing",
        #         "user_id": "def-456",
        #         "role": "user"
        #     }
        # ]
        # user = {
        #     "username": "admin",
        #     "user_id": "abc-123",
        #     "role": "admin"
        # }

        with st.form("role_form"): # a group of `form`

            selected_username = st.selectbox(
                "Username",
                list(user_options.keys())
            )

            role = st.selectbox(
                "New role",
                [
                    "user",
                    "admin",
                    "banned"
                ]
            )

            submitted = (
                st.form_submit_button(
                    "Update role"
                )
            )

        if submitted:

            # The admin selects a username,
            # but the backend API requires user_id.
            user_id = user_options[
                selected_username
            ]

            # Send a request from the frontend to FastAPI to change the user's role.
            result = api_request(
                "PUT",
                f"/api/users/{user_id}/role", # @app.put("/api/users/{user_id}/role")
                json={
                    "role": role 
                },
            )
            # PUT /api/users/def-456/role

            # {
            #     "role": "admin"
            # }

            show_result_message(
                result,
                "Role updated."
            )


    # --------------------------------
    # Create administrator
    # --------------------------------

    st.markdown("#### Create administrator")

    with st.form("create_admin_form"):

        admin_username = st.text_input(
            "Admin username"
        )

        admin_password = st.text_input(
            "Admin password",
            type="password"
        )

        create_admin_submitted = (
            st.form_submit_button(
                "Create administrator"
            )
        )

    if create_admin_submitted:

        result = api_request(
            "POST",
            "/api/users/admin",
            json={
                "username": admin_username,
                "password": admin_password
            },
        )

        show_result_message(
            result,
            "Administrator created."
        )