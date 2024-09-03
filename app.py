"""
This module provides an API for fetching and resolving tickets, as well as
generating AI suggestions.
"""

from typing import Optional, List
import os
import logging

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, BackgroundTasks, HTTPException
import pydantic
import pandas as pd

import ticket_manager
import llm_integration
import data_loader
import similarity


# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = fastapi.FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Constants for column names
COLUMN_TICKET_ID = "ticket_id"
COLUMN_RESOLVED = "resolved"
COLUMN_TEXT = "text"


# Dependency for ticket services and loading resolved tickets
class TicketService:
    """Manages ticket services and resolved ticket data."""

    def __init__(self):
        """Initialize TicketService with resolved tickets data."""
        try:
            if os.path.exists("ai_resolved.csv"):
                self.resolved_tickets_df = pd.read_csv("ai_resolved.csv")
            else:
                self.resolved_tickets_df = pd.DataFrame(
                    columns=[
                        COLUMN_TICKET_ID,
                        "issue",
                        "description",
                        "resolution",
                        COLUMN_RESOLVED,
                        "agent_name",
                        "ai_suggestion_helpful",
                        "feedback",
                    ]
                )
            # Ensure the resolved field is always boolean
            self.resolved_tickets_df[COLUMN_RESOLVED] = (
                self.resolved_tickets_df[COLUMN_RESOLVED]
                .fillna(False)
                .astype(bool)
            )
        except Exception as init_err:
            logger.error("Error initializing TicketService: %s", init_err)
            raise HTTPException(
                status_code=500, detail="Failed to initialize ticket service"
            ) from init_err

    def save_to_csv(self):
        """Save resolved tickets to CSV file."""
        try:
            self.resolved_tickets_df.to_csv("ai_resolved.csv", index=False)
        except Exception as save_err:
            logger.error("Error saving resolved tickets to CSV: %s", save_err)
            raise HTTPException(
                status_code=500, detail="Failed to save resolved tickets"
            ) from save_err


def get_ticket_service() -> TicketService:
    """Dependency injection for TicketService."""
    return TicketService()


# Initialize the DataLoader and other components
NEW_TICKET_PATH = os.path.join("data", "new_tickets.csv")
OLD_TICKETS_PATHS = [
    os.path.join("data", "old_tickets", "ticket_dump_1.csv"),
    os.path.join("data", "old_tickets", "ticket_dump_2.xlsx"),
    os.path.join("data", "old_tickets", "ticket_dump_3.json"),
]

new_ticket_loader = data_loader.DataLoader([NEW_TICKET_PATH])
old_ticket_loader = data_loader.DataLoader(OLD_TICKETS_PATHS)

NewTicketManager = ticket_manager.TicketManager(new_ticket_loader.load_data())
OldTicketsManager = ticket_manager.TicketManager(old_ticket_loader.load_data())

similarity_engine = similarity.SimilarityEngine(OldTicketsManager.tickets_df)
ai_suggestion_engine = llm_integration.AISuggestionEngine()


class ResolveTicketInput(pydantic.BaseModel):
    """
    Input for resolving a ticket.
    """

    resolution: str
    ai_suggestion_helpful: bool
    feedback: Optional[str] = None


@app.get("/")
def read_root():
    """
    Root endpoint for the API.
    """
    return {"message": "Welcome to the IT Helpdesk Ticket Resolution System"}


@app.get("/all-tickets", response_model=List[ticket_manager.Ticket])
def get_all_tickets():
    """Fetch all tickets."""
    try:
        return NewTicketManager.get_all_tickets()
    except Exception as all_tickets_err:
        logger.error("Error fetching all tickets: %s", all_tickets_err)
        raise HTTPException(
            status_code=500, detail="Failed to fetch all tickets"
        ) from all_tickets_err


@app.get("/ticket/{ticket_id}", response_model=ticket_manager.Ticket)
def get_ticket(ticket_id: str):
    """Fetch a specific ticket by ID."""
    try:
        ticket = NewTicketManager.get_ticket_by_id(ticket_id)
        if ticket:
            return ticket
        else:
            raise HTTPException(status_code=404, detail="Ticket not found")
    except Exception as ticket_err:
        logger.error("Error fetching ticket %s: %s", ticket_id, ticket_err)
        raise HTTPException(
            status_code=500, detail="Failed to fetch ticket"
        ) from ticket_err


@app.post("/ai-suggestion")
def get_ai_suggestion(ticket: ticket_manager.Ticket):
    """
    Provides an AI-generated suggestion for the given ticket.
    """
    try:
        similar_tickets = similarity_engine.find_similar_tickets(
            f"{ticket.issue} {ticket.description}"
        )
        suggestion = ai_suggestion_engine.generate_suggestion(
            similar_tickets, ticket.dict()
        )
        return {
            "suggestion": suggestion,
            "similar_tickets": similar_tickets.to_dict(orient="records"),
        }
    except Exception as ai_suggestion_err:
        logger.error("Error generating AI suggestion: %s", ai_suggestion_err)
        raise HTTPException(
            status_code=500, detail="AI suggestion failed"
        ) from ai_suggestion_err


@app.post("/resolve-ticket")
def resolve_ticket(
    ticket_id: str,
    resolve_input: ResolveTicketInput,
    background_tasks: BackgroundTasks,
    service: TicketService = Depends(get_ticket_service),
):
    """Resolve a ticket and update the resolved tickets list."""
    try:
        resolved_ticket = NewTicketManager.resolve_ticket(
            ticket_id,
            resolution=resolve_input.resolution,
            agent_name="Alex Sheldrick",
            ai_suggestion_helpful=resolve_input.ai_suggestion_helpful,
            feedback=resolve_input.feedback,
        )

        if resolved_ticket:
            resolved_ticket_dict = resolved_ticket.dict()

            resolved_ticket_dict[COLUMN_RESOLVED] = True
            resolved_ticket_dict["ai_suggestion_helpful"] = bool(
                resolve_input.ai_suggestion_helpful
            )
            resolved_ticket_dict["resolution"] = (
                resolve_input.resolution or "N/A"
            )
            resolved_ticket_dict["agent_name"] = "Alex Sheldrick"
            resolved_ticket_dict["feedback"] = resolve_input.feedback or "N/A"

            resolved_ticket_df = pd.DataFrame([resolved_ticket_dict])
            service.resolved_tickets_df = pd.concat(
                [service.resolved_tickets_df, resolved_ticket_df],
                ignore_index=True,
            )

            background_tasks.add_task(service.save_to_csv)

            NewTicketManager.tickets_df = NewTicketManager.tickets_df[
                NewTicketManager.tickets_df[COLUMN_TICKET_ID] != ticket_id
            ]

            NewTicketManager.tickets_df[COLUMN_RESOLVED] = (
                NewTicketManager.tickets_df[COLUMN_RESOLVED]
                .fillna(False)
                .astype(bool)
            )

            return {
                "message": "Ticket resolved successfully",
                "resolved_ticket": resolved_ticket_dict,
            }
        else:
            raise HTTPException(status_code=404, detail="Ticket not found")

    except Exception as resolve_err:
        logger.error("Error resolving ticket %s: %s", ticket_id, resolve_err)
        raise HTTPException(
            status_code=500, detail="Failed to resolve ticket"
        ) from resolve_err


@app.get("/resolved-tickets")
def get_resolved_tickets(service: TicketService = Depends(get_ticket_service)):
    """Fetch all resolved tickets."""
    try:
        if service.resolved_tickets_df.empty:
            return []

        sanitized_df = service.resolved_tickets_df.replace(
            [float("inf"), float("-inf"), float("nan")], None
        ).fillna("N/A")

        tickets = sanitized_df.drop(
            columns=[COLUMN_TEXT], errors="ignore"
        ).to_dict(orient="records")

        return tickets
    except Exception as resolved_tickets_err:
        logger.error("Error in get_resolved_tickets: %s", resolved_tickets_err)
        raise HTTPException(
            status_code=500, detail="Failed to fetch resolved tickets"
        ) from resolved_tickets_err


@app.post("/remove-resolved-ticket")
def remove_resolved_ticket(
    ticket_id: str, service: TicketService = Depends(get_ticket_service)
):
    """Remove a ticket from the resolved tickets list."""
    try:
        service.resolved_tickets_df = service.resolved_tickets_df[
            service.resolved_tickets_df[COLUMN_TICKET_ID] != ticket_id
        ]
        service.save_to_csv()
        return {"message": f"Ticket {ticket_id} removed from resolved tickets"}
    except Exception as remove_err:
        logger.error(
            "Error removing resolved ticket %s: %s", ticket_id, remove_err
        )
        raise HTTPException(
            status_code=500, detail="Failed to remove resolved ticket"
        ) from remove_err


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
