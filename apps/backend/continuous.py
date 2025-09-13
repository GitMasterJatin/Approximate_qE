import pandas as pd
import time
import numpy as np
from collections import deque


class StreamingQueryEngine:
    def __init__(self, csv_file: str = None):
        """
        Initialize engine. Optionally load CSV.
        """
        self.data = deque()  # stores (timestamp, row_dict)
        self.columns = None

        if csv_file:
            self.load_csv(csv_file)

    def load_csv(self, csv_file: str):
        """
        Load initial CSV and store rows with timestamp = now.
        """
        df = pd.read_csv(csv_file)
        self.columns = list(df.columns)
        now = time.time()

        for _, row in df.iterrows():
            self.data.append((now, row.to_dict()))

    def ingest(self, row: dict):
        """
        Ingest a new data point dynamically.
        Ensures columns match initial CSV.
        """
        if self.columns is None:
            self.columns = list(row.keys())

        missing_cols = [c for c in self.columns if c not in row]
        extra_cols = [c for c in row if c not in self.columns]

        if missing_cols or extra_cols:
            raise ValueError(
                f"Column mismatch.\nExpected columns: {self.columns}\n"
                f"Missing: {missing_cols}\nExtra: {extra_cols}"
            )

        self.data.append((time.time(), row))

    # -------------------------
    # Sliding Window Aggregates
    # -------------------------
    def sliding_window(self, window_size_sec: float, query: str, column: str):
        """
        Aggregate over last `window_size_sec` seconds.
        query: "COUNT", "SUM", "AVG"
        """
        now = time.time()

        # Remove old rows
        while self.data and now - self.data[0][0] > window_size_sec:
            self.data.popleft()

        values = [row[column] for ts, row in self.data if column in row]

        if not values:
            return 0

        if query.upper() == "COUNT":
            return len(values)
        elif query.upper() == "SUM":
            return sum(values)
        elif query.upper() == "AVG":
            return np.mean(values)
        else:
            raise ValueError("Supported queries: COUNT, SUM, AVG")

    # -------------------------
    # Exponential Decay Aggregates
    # -------------------------
    def exponential_decay(self, query: str, column: str, lambda_: float = 0.1):
        """
        Aggregate with exponential decay weighting: recent rows matter more.
        query: "COUNT", "SUM", "AVG"
        lambda_: decay factor
        """
        now = time.time()
        weighted_values = []
        weights = []

        for ts, row in self.data:
            age = now - ts
            w = np.exp(-lambda_ * age)
            weighted_values.append(row[column] * w)
            weights.append(w)

        if not weights:
            return 0

        if query.upper() == "COUNT":
            return sum(weights)
        elif query.upper() == "SUM":
            return sum(weighted_values)
        elif query.upper() == "AVG":
            return sum(weighted_values) / sum(weights)
        else:
            raise ValueError("Supported queries: COUNT, SUM, AVG")


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    # Initialize engine with CSV
    engine = StreamingQueryEngine("data.csv")

    # Ingest new row dynamically
    engine.ingest({"user_id": 6, "amount": 150, "category": "food", "value": 18})

    # Sliding Window: last 10 seconds SUM of 'amount'
    print("Sliding Window SUM:", engine.sliding_window(10, "SUM", "amount"))

    # Exponential Decay AVG of 'amount' (lambda=0.5)
    print("Exponential Decay AVG:", engine.exponential_decay("AVG", "amount", lambda_=0.5))
