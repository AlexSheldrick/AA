""" Ticket Manager for managing tickets and pydantic models for tickets."""

from typing import Optional
import pydantic
import pandas as pd

from data_loader import DataLoader


class Ticket(pydantic.BaseModel):
    """
    Representation of a ticket.
    """

    ticket_id: str
    issue: str
    description: str
    resolved: bool = False

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class TicketManager:
    """
    Manages the fetching of new tickets and keeps track of the current ticket.
    """

    def __init__(self, tickets_df: pd.DataFrame):
        """
        Initializes the TicketManager with a DataFrame of tickets.

        :param tickets_df: DataFrame containing the ticket data.
        """
        self.tickets_df = tickets_df
        self.current_index = 0

    def fetch_current_ticket(self) -> Optional[Ticket]:
        """
        Fetches the current ticket.

        :return: A Ticket object if found, otherwise None.
        """
        if 0 <= self.current_index < len(self.tickets_df):
            ticket_data = self.tickets_df.iloc[self.current_index].to_dict()
            return Ticket(**ticket_data)
        return None

    def drop_current_ticket(self):
        """
        Drops the current ticket from the DataFrame.
        """
        if 0 <= self.current_index < len(self.tickets_df):
            self.tickets_df = self.tickets_df.drop(self.current_index)
            self.tickets_df = self.tickets_df.reset_index(drop=True)
            self.current_index -= 1

    def drop_ticket_by_id(self, ticket_id: str):
        """
        Drops a ticket by its ID.

        :param ticket_id: The ID of the ticket to drop.
        """
        self.tickets_df = self.tickets_df[
            self.tickets_df["ticket_id"] != ticket_id
        ]
        self.tickets_df = self.tickets_df.reset_index(drop=True)

    def get_ticket_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """
        Retrieves a ticket by its ID.

        :param ticket_id: The ID of the ticket to retrieve.
        :return: A Ticket object if found, otherwise None.
        """
        ticket_data = self.tickets_df[
            self.tickets_df["ticket_id"] == ticket_id  # str
        ]
        if not ticket_data.empty:
            return Ticket(**ticket_data.iloc[0].to_dict())
        else:
            return None

    def add_ticket(self, ticket: Ticket):
        """
        Adds a new ticket to the DataFrame.

        :param ticket: The Ticket object to be added.
        """
        new_ticket_df = pd.DataFrame([ticket.model_dump()])
        self.tickets_df = pd.concat(
            [self.tickets_df, new_ticket_df], ignore_index=True
        )

    def fetch_ticket_by_idx(self, idx: int) -> Optional[Ticket]:
        """
        Retrieves a ticket by its index.

        :param idx: The index of the ticket to retrieve.
        :return: A Ticket object if found, otherwise None.
        """
        if 0 <= idx < len(self.tickets_df):
            ticket_data = self.tickets_df.iloc[idx].to_dict()
            return Ticket(**ticket_data)
        return None

    def drop_ticket_by_idx(self, idx: int):
        """
        Drops a ticket by its index.

        :param idx: The index of the ticket to drop.
        """
        if 0 <= idx < len(self.tickets_df):
            self.tickets_df = self.tickets_df.drop(idx)
            self.tickets_df = self.tickets_df.reset_index(drop=True)

    def resolve_ticket(
        self,
        idx: int,
        resolution: str,
        agent_name: str,
        ai_suggestion_helpful: bool,
        feedback: Optional[str] = None,
    ) -> Optional[Ticket]:
        """
        Marks a ticket as resolved and updates the resolution details.

        :param idx: The index of the ticket to resolve.
        :param resolution: The resolution details.
        :param agent_name: The name of the agent resolving the ticket.
        :param ai_suggestion_helpful: Whether the AI suggestion was helpful.
        :param feedback: Optional feedback from the agent.
        :return: The resolved Ticket object if successful, otherwise None.
        """
        if 0 <= idx < len(self.tickets_df):
            self.tickets_df.at[idx, "resolution"] = resolution
            self.tickets_df.at[idx, "resolved"] = True
            self.tickets_df.at[idx, "agent_name"] = agent_name
            self.tickets_df.at[idx, "ai_suggestion_helpful"] = (
                ai_suggestion_helpful
            )
            self.tickets_df.at[idx, "feedback"] = (
                feedback if feedback else "N/A"
            )

            return Ticket(**self.tickets_df.iloc[idx].to_dict())
        return None

    def get_all_tickets(self) -> list[Ticket]:
        """
        Retrieves all tickets in the DataFrame.

        :return: A list of Ticket objects.
        """
        return [
            Ticket(**{str(k): v for k, v in ticket.items()})
            for ticket in self.tickets_df.to_dict(orient="records")
        ]


if __name__ == "__main__":
    paths = [
        "data/old_tickets/ticket_dump_1.csv",
        "data/old_tickets/ticket_dump_2.xlsx",
        "data/old_tickets/ticket_dump_3.json",
    ]
    data_loader = DataLoader(paths)
    Tickets_Df = data_loader.load_data()

    ticket_manager = TicketManager(Tickets_Df)
    new_ticket = ticket_manager.fetch_current_ticket()
    print(new_ticket)
    ticket_manager.current_index = 1
    print(ticket_manager.fetch_current_ticket())
