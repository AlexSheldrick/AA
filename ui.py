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


def fetch_ticket_by_id(ticket_id):
    """Fetch a specific ticket by ID and update the session state."""
    ticket = fetch_data_from_api(f"ticket/{ticket_id}")
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
    first_ticket_id = st.session_state["all_tickets_df"].iloc[0]["ticket_id"]
    fetch_ticket_by_id(first_ticket_id)

st.title("IT Helpdesk Ticket Resolution System")

# Navigation arrows and current ticket display
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    if st.button("←") and st.session_state["current_index"] > 0:
        st.session_state["current_index"] -= 1
        current_ticket_id = st.session_state["all_tickets_df"].iloc[
            st.session_state["current_index"]
        ]["ticket_id"]
        fetch_ticket_by_id(current_ticket_id)

with col3:
    if (
        st.button("→")
        and st.session_state["current_index"]
        < len(st.session_state["all_tickets_df"]) - 1
    ):
        st.session_state["current_index"] += 1
        current_ticket_id = st.session_state["all_tickets_df"].iloc[
            st.session_state["current_index"]
        ]["ticket_id"]
        fetch_ticket_by_id(current_ticket_id)

with col2:
    st.write(
        f"Ticket {st.session_state['current_index'] + 1} of "
        f"{len(st.session_state['all_tickets_df'])}"
    )

# Display current ticket as a Pandas DataFrame
if st.session_state["current_ticket"]:
    st.header("Current Ticket")
    st.dataframe(pd.DataFrame([st.session_state["current_ticket"]]))

    # AI Suggestion
    if st.button("Get AI Suggestion"):
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
                    st.session_state["similar_tickets_df"] = pd.DataFrame(
                        suggestion_data["similar_tickets"]
                    )
                else:
                    st.error(f"Failed to get AI suggestion: {response.text}")
            except requests.RequestException as e:
                st.error(f"Error getting AI suggestion: {str(e)}")

    if st.session_state["ai_suggestion"]:
        st.subheader("AI Suggestion")
        st.write(st.session_state["ai_suggestion"])

    if not st.session_state["similar_tickets_df"].empty:
        st.subheader("Similar Tickets")
        st.dataframe(st.session_state["similar_tickets_df"])

    # Ticket Resolution
    st.subheader("Resolve Ticket")
    resolution = st.text_area("Resolution")
    ai_helpful = st.checkbox("Was the AI suggestion helpful?")
    feedback = st.text_area("Feedback on AI suggestion")

    if st.button("Resolve Ticket"):
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
                        "ticket_id": st.session_state["current_ticket"][
                            "ticket_id"
                        ]
                    },
                    json=resolve_data,
                    timeout=TIMEOUT,
                )
                if response.status_code == 200:
                    st.success("Ticket resolved successfully!")
                    fetch_resolved_tickets()
                else:
                    st.error(f"Failed to resolve ticket: {response.text}")
            except requests.RequestException as e:
                st.error(f"Error resolving ticket: {str(e)}")


# Display resolved tickets
st.header("Resolved Tickets")
st.dataframe(st.session_state["resolved_tickets_df"])
