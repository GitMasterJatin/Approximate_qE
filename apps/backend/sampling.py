import pandas as pd
import numpy as np
import random
from collections import defaultdict


class SamplingQueryEngine:
    def __init__(self, file_path: str):
        # Load CSV
        self.df = pd.read_csv(file_path)
        self.columns = list(self.df.columns)

    def run_query(self, query: str, error_tolerance: float = 0.05, method: str = None):
        """
        Run approximate queries using sampling techniques.

        Supported queries:
            COUNT
            SUM <col>
            AVG <col>
            GROUPBY <col>
        """
        parts = query.strip().split()
        if len(parts) == 0:
            raise ValueError("Empty query")

        qtype = parts[0].upper()  # Only uppercase the query type

        col = parts[1] if len(parts) > 1 else None
        if col:
            self._check_column_exists(col)
            if qtype in ["SUM", "AVG"]:
                self._check_numeric_column(col)

        # Choose sampling technique
        technique = method.lower() if method else self._choose_sampling(qtype, error_tolerance)

        if technique == "random":
            return self._random_sampling(qtype, col, error_tolerance)
        elif technique == "stratified":
            return self._stratified_sampling(qtype, col, error_tolerance)
        elif technique == "reservoir":
            return self._reservoir_sampling(qtype, col, error_tolerance)
        elif technique == "adaptive":
            return self._adaptive_sampling(qtype, col, error_tolerance)
        else:
            raise ValueError(f"Unsupported technique: {technique}")

    # -------------------------
    # Auto chooser
    # -------------------------
    def _choose_sampling(self, qtype, error_tolerance):
        if qtype == "GROUPBY":
            return "stratified"
        elif error_tolerance <= 0.02:
            return "adaptive"
        elif qtype in ["SUM", "AVG"]:
            return "random"
        else:
            return "reservoir"

    # -------------------------
    # Validation helpers
    # -------------------------
    def _check_column_exists(self, col):
        if col not in self.columns:
            raise ValueError(f"Column '{col}' not found. Available columns: {self.columns}")

    def _check_numeric_column(self, col):
        if not pd.api.types.is_numeric_dtype(self.df[col]):
            raise ValueError(f"Column '{col}' must be numeric for SUM/AVG queries")

    # -------------------------
    # Sampling Methods
    # -------------------------
    def _random_sampling(self, qtype, col, error_tolerance):
        frac = max(0.01, min(1.0, 1 - error_tolerance))
        sample = self.df.sample(frac=frac, random_state=42)
        return self._execute_on_sample(qtype, col, sample, frac, "Random Sampling")

    def _stratified_sampling(self, qtype, col, error_tolerance):
        if qtype != "GROUPBY" or not col:
            return self._random_sampling(qtype, col, error_tolerance)
        groups = self.df.groupby(col)
        frac = max(0.01, min(1.0, 1 - error_tolerance))
        sample = groups.apply(lambda x: x.sample(frac=frac, random_state=42)).reset_index(drop=True)
        return self._execute_on_sample(qtype, col, sample, frac, "Stratified Sampling")

    def _reservoir_sampling(self, qtype, col, error_tolerance):
        k = max(100, int(len(self.df) * (1 - error_tolerance)))
        reservoir = []
        for i, row in enumerate(self.df.itertuples(index=False)):
            if i < k:
                reservoir.append(row)
            else:
                j = random.randint(0, i)
                if j < k:
                    reservoir[j] = row
        sample = pd.DataFrame(reservoir, columns=self.df.columns)
        frac = k / len(self.df)
        return self._execute_on_sample(qtype, col, sample, frac, "Reservoir Sampling")

    def _adaptive_sampling(self, qtype, col, error_tolerance):
        frac1 = 0.1
        result1 = self._execute_on_sample(qtype, col, self.df.sample(frac=frac1, random_state=42), frac1, "Adaptive Sampling")
        frac2 = min(1.0, frac1 * 2)
        result2 = self._execute_on_sample(qtype, col, self.df.sample(frac=frac2, random_state=43), frac2, "Adaptive Sampling")
        estimated_error = abs(result1["result"] - result2["result"]) / (abs(result2["result"]) + 1e-6)
        result1["estimated_error"] = estimated_error
        return result1

    # -------------------------
    # Execute query on sample
    # -------------------------
    def _execute_on_sample(self, qtype, col, sample, frac, method):
        if qtype == "COUNT":
            result = len(sample) / frac
        elif qtype == "SUM":
            result = sample[col].sum() / frac
        elif qtype == "AVG":
            result = sample[col].mean()
        elif qtype == "GROUPBY":
            counts = sample[col].value_counts() / frac
            result = counts.to_dict()
        else:
            raise ValueError(f"Unsupported query type: {qtype}")

        est_error = 1 / np.sqrt(max(1, len(sample)))
        return {"method": method, "result": result, "estimated_error": est_error}


# -------------------------
# Example Usage
# -------------------------
if __name__ == "__main__":
    engine = SamplingQueryEngine("merged_data.csv")

    try:
        print(engine.run_query("COUNT", error_tolerance=0.1))
        print(engine.run_query("SUM amount", error_tolerance=0.05))
        print(engine.run_query("AVG value", error_tolerance=0.05))
        print(engine.run_query("GROUPBY category", error_tolerance=0.1))
    except ValueError as e:
        print("Error:", e)
