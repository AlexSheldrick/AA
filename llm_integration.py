"""
This module integrates with an LLM API to generate AI-enhanced suggestions
based on similar tickets.
"""

import os
import pandas as pd
import openai

import aleph_alpha_client


class AISuggestionEngine:
    """
    Integrates with an LLM API to generate AI-enhanced suggestions based on
    similar tickets.
    """

    def __init__(self, provider: str = "aleph-alpha_luminous"):
        """
        Initializes the AISuggestionEngine with the necessary API key.
        """
        self.provider = provider
        if provider == "openai":
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif provider == "aleph-alpha":
            self.client = openai.OpenAI(
                api_key=os.getenv("AA_TOKEN"),
                base_url="https://api.aleph-alpha.com",
            )
        elif provider == "aleph-alpha_luminous":
            self.client = aleph_alpha_client.Client(token=os.getenv("AA_KEY"))
        else:
            raise ValueError(f"Invalid provider: {provider}")

    def generate_suggestion(
        self, similar_tickets: pd.DataFrame, new_ticket: dict[str, str]
    ) -> str:
        """
        Generates an AI-enhanced suggestion based on similar tickets.
        """
        if self.provider == "aleph-alpha_luminous":
            return self.generate_suggestion_aleph_alpha_luminous(
                similar_tickets, new_ticket
            )
        else:
            return self.generate_suggestion_openai(similar_tickets, new_ticket)

    def generate_suggestion_openai(
        self, similar_tickets: pd.DataFrame, new_ticket: dict[str, str]
    ) -> str:
        """
        Generates an AI-enhanced suggestion based on similar tickets.

        :param similar_tickets: DataFrame containing the top K similar tickets.
        :param new_ticket: Dictionary containing the details of the new ticket.
        :return: A string containing the AI-generated suggestion.
        """
        # Prepare the prompt for the LLM
        user_prompt = self._build_user_prompt_openai(
            similar_tickets, new_ticket
        )

        # Call the LLM API
        response = self.client.chat.completions.create(
            model=(
                "gpt-4o-mini"
                if self.provider == "openai"
                else "llama-3.1-70b-instruct"
            ),
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_prompt},
            ],
            # max_tokens=350,
            n=1,
            stop=None,
            temperature=0.7,
        )
        suggestion = self._parse_answer(response.choices[0].message.content)
        return suggestion

    def generate_suggestion_aleph_alpha_luminous(
        self, similar_tickets: pd.DataFrame, new_ticket: dict[str, str]
    ) -> str:
        """
        Generates an AI-enhanced suggestion based on similar tickets.
        """
        build_user_prompt = self._build_user_prompt_aleph_alpha_luminous
        user_prompt = build_user_prompt(similar_tickets, new_ticket)
        request = aleph_alpha_client.CompletionRequest(
            prompt=aleph_alpha_client.Prompt.from_text(
                f"You are a helpful IT-assistant. \n\n{user_prompt}"
            ),
            # maximum_tokens=350,
            temperature=0.7,
        )
        response = self.client.complete(
            request, model="luminous-supreme-control-20240215"
        )
        suggestion = response.completions[0].completion
        return suggestion

    def _build_user_prompt_aleph_alpha_luminous(
        self, similar_tickets: pd.DataFrame, new_ticket: dict[str, str]
    ) -> str:
        """
        Builds a prompt for the LLM based on similar tickets and the new
        ticket.
        """
        prompt = "### Instruction:\n Find a solution to this IT issue\n"
        prompt += f"Issue: {new_ticket['issue']}\n"
        prompt += f"Description: {new_ticket['description']}\n\n"
        prompt += "### Input: The following are similar tickets and their "
        prompt += "resolutions:\n Use them to inform your response.\n\n"

        for _, row in similar_tickets.iterrows():
            prompt += f"<Ticket ID: {row['ticket_id']}>\n"
            prompt += f"<Issue: {row['issue']}>\n"
            prompt += f"<Description: {row['description']}>\n"
            prompt += f"Resolution: {row['resolution']}\n\n"

        prompt += "### Response:"
        return prompt

    def _build_user_prompt_openai(
        self, similar_tickets: pd.DataFrame, new_ticket: dict[str, str]
    ) -> str:
        """
        Builds a prompt for the LLM based on similar tickets and the new
        ticket.

        :param similar_tickets: DataFrame containing similar tickets.
        :param new_ticket: Dictionary containing the details of the new ticket.
        :return: A string containing the prompt to be sent to the LLM.
        """
        prompt = f"Here is a new ticket:\nIssue: {new_ticket['issue']}"
        prompt += f"\nDescription: {new_ticket['description']}\n"
        prompt += "The following are similar tickets and their resolutions:\n"

        for idx, row in similar_tickets.iterrows():
            prompt += f"<Similar Ticket {idx+1}>\n"
            prompt += f"Ticket ID: {row['ticket_id']}\n"
            prompt += f"Issue: {row['issue']}\n"
            prompt += f"Description: {row['description']}\n"
            prompt += f"Resolution: {row['resolution']}\n\n"
            prompt += f"</Similar Ticket {idx+1}>\n"

        prompt += (
            "Think step by step. Evaluate the similar tickets and the new "
            "ticket. Reason whether the similar tickets are relevant and then,"
            " based on these similar tickets and their resolutions, please "
            "suggest a potential solution or next steps for the new ticket.\n"
            "\nYour response should be concise and in the following format:\n"
            "<Suggested Solution>\n"
            "... your response ...\n"
            "</Suggested Solution>\n"
            "When referring to the similar tickets, use the Ticket ID."
        )
        return prompt

    def _parse_answer(self, answer: str) -> str:
        """
        Parses the answer from the LLM to extract the suggested solution.

        :param answer: A string containing the LLM's response.
        :return: A string containing the suggested solution.
        """
        return answer.split("<Suggested Solution>")[1].split(
            "</Suggested Solution>"
        )[0]


if __name__ == "__main__":
    import data_loader
    import ticket_manager
    import similarity

    NEW_TICKET_PATH = os.path.join("data", "new_tickets.csv")
    OLD_TICKETS_PATHS = [
        os.path.join("data", "old_tickets", "ticket_dump_1.csv"),
        os.path.join("data", "old_tickets", "ticket_dump_2.xlsx"),
        os.path.join("data", "old_tickets", "ticket_dump_3.json"),
    ]

    new_ticket_loader = data_loader.DataLoader([NEW_TICKET_PATH])
    old_ticket_loader = data_loader.DataLoader(OLD_TICKETS_PATHS)

    NewTicketManager = ticket_manager.TicketManager(
        new_ticket_loader.load_data()
    )
    OldTicketsManager = ticket_manager.TicketManager(
        old_ticket_loader.load_data()
    )

    similarity_engine = similarity.SimilarityEngine(
        OldTicketsManager.tickets_df
    )
    ticket = NewTicketManager.fetch_next_ticket()
    Similar_tickets = similarity_engine.find_similar_tickets(
        f"{ticket.issue} {ticket.description}"
    )

    ai_suggestion_engine = AISuggestionEngine()
    ai_suggestion = ai_suggestion_engine.generate_suggestion(
        Similar_tickets, ticket
    )
    print(ai_suggestion)
