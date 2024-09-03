""" Similarity Engine for finding similar tickets."""

import pandas as pd
from sklearn import feature_extraction  # type ignore
from sklearn import metrics


class SimilarityEngine:
    """
    Engine to find similar tickets based on text similarity.
    """

    def __init__(self, resolved_tickets_df: pd.DataFrame):
        """
        Initializes the SimilarityEngine with resolved tickets.

        :param resolved_tickets_df: DataFrame containing resolved tickets.
        """
        self.resolved_tickets_df = resolved_tickets_df
        self.vectorizer = feature_extraction.text.TfidfVectorizer(
            stop_words="english"
        )
        self._fit()

    def _fit(self):
        """
        Fits the TF-IDF vectorizer on the ticket text data.
        """
        self.resolved_tickets_df["text"] = (
            self.resolved_tickets_df["issue"]
            + " "
            + self.resolved_tickets_df["description"]
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(
            self.resolved_tickets_df["text"]
        )

    def find_similar_tickets(
        self, ticket_text: str, top_k: int = 3
    ) -> pd.DataFrame:
        """
        Finds the top K similar tickets.

        :param ticket_text: Text of the new ticket to find similarities with.
        :param top_k: Number of similar tickets to return.
        :return: DataFrame containing the top K similar tickets.
        """
        ticket_vector = self.vectorizer.transform([ticket_text])
        similarity_scores = metrics.pairwise.cosine_similarity(
            ticket_vector, self.tfidf_matrix
        )
        similar_indices = similarity_scores.argsort()[0, -top_k:][::-1]
        return self.resolved_tickets_df.iloc[similar_indices][
            ["ticket_id", "issue", "resolution", "description"]
        ]


if __name__ == "__main__":
    from data_loader import DataLoader
    from ticket_manager import TicketManager

    paths = [
        "data/old_tickets/ticket_dump_1.csv",
        "data/old_tickets/ticket_dump_2.xlsx",
        "data/old_tickets/ticket_dump_3.json",
    ]
    data_loader = DataLoader(paths)
    Tickets_Df = data_loader.load_data()

    ticket_manager = TicketManager(Tickets_Df)
    new_ticket = ticket_manager.fetch_next_ticket()

    Resolved_tickets_df = Tickets_Df[Tickets_Df["resolved"]]
    similarity_engine = SimilarityEngine(Resolved_tickets_df)

    if new_ticket:
        Similar_Tickets = similarity_engine.find_similar_tickets(
            new_ticket.issue + " " + new_ticket.description
        )
    print(Similar_Tickets)
