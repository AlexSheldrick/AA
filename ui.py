"""
This is a simple UI for the IT Helpdesk Ticket Resolution System.
"""

import streamlit as st
import requests
import pandas as pd

# FastAPI server URL
FASTAPI_URL = "http://127.0.0.1:8000"
TIMEOUT = 180

# Initialize session state
SESSION_KEYS = {
    "resolved_tickets_df": "resolved_tickets_df",
    "current_ticket": "current_ticket",
    "ai_suggestion": "ai_suggestion",
    "similar_tickets_df": "similar_tickets_df",
    "all_tickets_df": "all_tickets_df",
    "current_index": "current_index",
}

for key, default_value in {
    SESSION_KEYS["resolved_tickets_df"]: pd.DataFrame(
        columns=[
            "ticket_id",
            "issue",
            "description",
            "resolution",
            "resolved",
            "agent_name",
            "ai_suggestion_helpful",
            "feedback",
        ]
    ),
    SESSION_KEYS["current_ticket"]: None,
    SESSION_KEYS["ai_suggestion"]: None,
    SESSION_KEYS["similar_tickets_df"]: pd.DataFrame(),
    SESSION_KEYS["all_tickets_df"]: pd.DataFrame(),
    SESSION_KEYS["current_index"]: 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


def fetch_data_from_api(endpoint: str, params: dict = None):
    """Fetch data from the specified API endpoint."""
    try:
        api_response = requests.get(
            f"{FASTAPI_URL}/{endpoint}", params=params, timeout=30
        )
        api_response.raise_for_status()
        return api_response.json()
    except requests.HTTPError as http_err:
        st.error(
            f"HTTP error occurred while fetching data from "
            f"{endpoint}: {http_err}"
        )
    except requests.RequestException as req_err:
        st.error(
            f"Failed to fetch data from {endpoint}. Please try again later: "
            f"{req_err}"
        )
    return None


def fetch_all_tickets():
    """Fetch all tickets and update the session state."""
    tickets = fetch_data_from_api("all-tickets")
    if tickets is not None:
        st.session_state["all_tickets_df"] = pd.DataFrame(tickets)


def fetch_resolved_tickets():
    """Fetch resolved tickets and update the session state."""
    resolved_tickets = fetch_data_from_api("resolved-tickets")
    if resolved_tickets is not None:
        st.session_state["resolved_tickets_df"] = pd.DataFrame(
            resolved_tickets
        )  # type: ignore


def fetch_ticket_by_idx(idx: int):
    """Fetch a specific ticket by index and update the session state."""
    ticket = fetch_data_from_api(f"ticket/{idx}")
    if ticket is not None:
        st.session_state["current_ticket"] = ticket


# Fetch all tickets and resolved tickets at the start of the session
fetch_all_tickets()
fetch_resolved_tickets()

# Fetch the first ticket by its ID if it hasn't been fetched yet
if (
    st.session_state["current_ticket"] is None
    and len(st.session_state["all_tickets_df"]) > 0
):
    fetch_ticket_by_idx(st.session_state["current_index"])

st.title("IT Helpdesk Ticket Resolution System")

# Navigation arrows and current ticket display
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    if st.button("←") and st.session_state["current_index"] > 0:
        st.session_state["current_index"] -= 1
        fetch_ticket_by_idx(st.session_state["current_index"])

with col3:
    if (
        st.button("→")
        and st.session_state["current_index"]
        < len(st.session_state["all_tickets_df"]) - 1
    ):
        st.session_state["current_index"] += 1
        fetch_ticket_by_idx(st.session_state["current_index"])

with col2:
    st.write(
        f"Ticket {st.session_state['current_index'] + 1} of "
        f"{len(st.session_state['all_tickets_df'])}"
        if not st.session_state["all_tickets_df"].empty
        else "All done for Today!"
    )

# Display current ticket as a Pandas DataFrame
if not st.session_state["all_tickets_df"].empty:
    st.header("Current Ticket")
    current_ticket_df = st.session_state["all_tickets_df"].iloc[
        [st.session_state["current_index"]]
    ]
    st.dataframe(current_ticket_df, use_container_width=True)

    # AI Suggestion
    def create_resolution_form():
        """Create a resolution form. It clears on submit."""
        with st.form("resolution_form", clear_on_submit=True):
            if st.form_submit_button("Get AI Suggestion"):
                with st.spinner("Fetching AI Suggestion..."):
                    try:
                        response = requests.post(
                            f"{FASTAPI_URL}/ai-suggestion",
                            json=st.session_state["current_ticket"],
                            timeout=TIMEOUT,
                        )
                        if response.status_code == 200:
                            suggestion_data = response.json()
                            st.session_state["ai_suggestion"] = suggestion_data[
                                "suggestion"
                            ]
                            st.session_state["similar_tickets_df"] = (
                                pd.DataFrame(suggestion_data["similar_tickets"])
                            )
                        else:
                            st.error(
                                f"Failed to get AI suggestion: {response.text}"
                            )
                    except requests.RequestException as e:
                        st.error(f"Error getting AI suggestion: {str(e)}")
                st.rerun()

            if st.session_state["ai_suggestion"]:
                st.subheader("AI Suggestion")
                st.write(st.session_state["ai_suggestion"])

            if not st.session_state["similar_tickets_df"].empty:
                st.subheader("Similar Tickets")
                st.dataframe(
                    st.session_state["similar_tickets_df"],
                    use_container_width=True,
                )

            resolution = st.text_area("Resolution")
            ai_helpful = st.checkbox("Was the AI suggestion helpful?")
            feedback = st.text_area("Feedback on AI suggestion")
            submit_resolution = st.form_submit_button("Resolve Ticket")

            if submit_resolution:
                with st.spinner("Resolving ticket..."):
                    resolve_data = {
                        "resolution": resolution,
                        "ai_suggestion_helpful": ai_helpful,
                        "feedback": feedback,
                    }
                    try:
                        response = requests.post(
                            f"{FASTAPI_URL}/resolve-ticket",
                            params={
                                "ticket_idx": st.session_state["current_index"]
                            },
                            json=resolve_data,
                            timeout=TIMEOUT,
                        )
                        if response.status_code == 200:
                            st.success("Ticket resolved successfully!")
                            fetch_resolved_tickets()
                            fetch_all_tickets()  # Refresh the all_tickets_df
                            # Decrement the current index if it's not the first ticket
                            if st.session_state["current_index"] > 0:
                                st.session_state["current_index"] -= 1
                            # Fetch the new current ticket
                            fetch_ticket_by_idx(
                                st.session_state["current_index"]
                            )
                            # Reset AI suggestion and similar tickets
                            st.session_state["ai_suggestion"] = None
                            st.session_state["similar_tickets_df"] = (
                                pd.DataFrame()
                            )
                            return True
                        else:
                            st.error(
                                f"Failed to resolve ticket: {response.text}"
                            )
                    except requests.RequestException as e:
                        st.error(f"Error resolving ticket: {str(e)}")
        return False

    if create_resolution_form():
        st.rerun()


# Display resolved tickets
st.header("Resolved Tickets")
st.dataframe(st.session_state["resolved_tickets_df"], use_container_width=True)
