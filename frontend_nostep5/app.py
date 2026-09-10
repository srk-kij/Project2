import streamlit as st

from api_client import init_api_state
from auth_page import show_auth_page
from problem_page import show_problem_page
from submission_page import show_submission_page


st.set_page_config(
    page_title="Online Judge",
    page_icon="💻",
    layout="wide",
)

init_api_state()

if "user" not in st.session_state:
    st.session_state.user = None

st.sidebar.title("Online Judge")

st.sidebar.text_input(
    "Backend URL",
    key="backend_url", # st.session_state["backend_url"] or st.session_state.backend_url
    # Suppose the user enters http://127.0.0.1:8000; subsequently, 
    # print(st.session_state["backend_url"]) will output http://127.0.0.1:8000.
    help="FastAPI backend, normally http://127.0.0.1:8000",
)

user = st.session_state.user
if user:
    st.sidebar.success(f"{user.get('username', '')} ({user.get('role', '')})")
else:
    st.sidebar.info("Not logged in")

page = st.sidebar.radio(
    "Page",
    ["User", "Problems", "Submissions"],
)

if page == "User":
    show_auth_page()
elif page == "Problems":
    show_problem_page()
else:
    show_submission_page()
