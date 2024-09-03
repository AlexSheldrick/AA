"""
This module provides a DataLoader class to load data from various file formats
into a pandas DataFrame.
"""

import json
import os

import pandas as pd


class DataLoader:
    """
    DataLoader class to handle loading of ticket data from CSV, XLSX, and JSON
    files.
    """

    def __init__(self, file_paths: list[str]):
        """
        Initializes the DataLoader with a list of file paths.

        :param file_paths: List of file paths to load data from.
        """
        self.file_paths = file_paths
        self.data_frames: list[pd.DataFrame] = []

    def load_data(self) -> pd.DataFrame:
        """
        Loads data from the specified file paths and concatenates them into a
        single DataFrame.

        :return: A pandas DataFrame containing all the loaded data.
        """
        for file_path in self.file_paths:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".csv":
                df = self._load_csv(file_path)
            elif ext == ".xlsx":
                df = self._load_xlsx(file_path)
            elif ext == ".json":
                df = self._load_json(file_path)
            else:
                raise ValueError(f"Unsupported file format: {ext}")

            df = self.normalize_names(df)
            self.data_frames.append(df)

        combined_df = pd.concat(self.data_frames, ignore_index=True)
        combined_df = self._set_types(combined_df)
        return combined_df

    def _set_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Set the types of the columns to the correct data type.
        """
        # Set the correct data types for each column
        if "ticket_id" in df.columns:
            df["ticket_id"] = df["ticket_id"].astype(str)
        if "issue" in df.columns:
            df["issue"] = df["issue"].astype(str)
        if "category" in df.columns:
            df["category"] = df["category"].astype(str)
        if "resolution" in df.columns:
            df["resolution"] = df["resolution"].astype(str)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format="mixed")
        if "agent_name" in df.columns:
            df["agent_name"] = df["agent_name"].astype(str)
        if "resolved" in df.columns:
            df["resolved"] = df["resolved"].astype(bool)
        if "description" in df.columns:
            df["description"] = df["description"].astype(str)
        if "ai_suggestion_helpful" in df.columns:
            df["ai_suggestion_helpful"] = df["ai_suggestion_helpful"].astype(
                bool
            )
        if "feedback" in df.columns:
            df["feedback"] = df["feedback"].astype(str)

        return df

    def _load_csv(self, file_path: str) -> pd.DataFrame:
        """
        Loads data from a CSV file.

        :param file_path: The path to the CSV file.
        :return: A pandas DataFrame containing the data.
        """
        return pd.read_csv(file_path)

    def _load_xlsx(self, file_path: str) -> pd.DataFrame:
        """
        Loads data from an XLSX file.

        :param file_path: The path to the XLSX file.
        :return: A pandas DataFrame containing the data.
        """
        # Read all sheets and concatenate them
        return pd.concat(
            pd.read_excel(file_path, sheet_name=None), ignore_index=True
        )

    def _load_json(self, file_path: str) -> pd.DataFrame:
        """
        Loads data from a JSON file.

        :param file_path: The path to the JSON file.
        :return: A pandas DataFrame containing the data.
        """
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        df = pd.DataFrame.from_dict(data)
        return df

    def normalize_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the names of the columns.
        """
        df.columns = df.columns.str.lower()
        df.columns = df.columns.str.replace(" ", "_")
        return df


if __name__ == "__main__":
    paths = [
        "data/old_tickets/ticket_dump_1.csv",
        "data/old_tickets/ticket_dump_2.xlsx",
        "data/old_tickets/ticket_dump_3.json",
    ]

    data_loader = DataLoader(paths)
    tickets_df = data_loader.load_data()

    print(tickets_df)
