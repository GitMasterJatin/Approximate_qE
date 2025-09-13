import pandas as pd
from datasketch import HyperLogLog
from collections import defaultdict
import math
import numpy as np
import random


class UnifiedQueryEngine:
    def __init__(self, file_path: str):
        self.df = pd.read_csv(file_path)
        self.columns = list(self.df.columns)

    def run_query(self, query: str, error_tolerance: float = 0.05, method: str = None):
        parts = query.strip().split()
        if len(parts) == 0:
            raise ValueError("Empty query")

        qtype = parts[0].upper()  # Only uppercase the query type
        col = parts[1] if len(parts) > 1 else None

        if col:
            self._check_column_exists(col)
            if qtype in ["SUM", "AVG"]:
                self._check_numeric_column(col)

        # Decide technique
        technique = method.lower() if method else self._choose_method(qtype, col, error_tolerance)

        # Execute the query
        if technique == "hyperloglog":
            result_dict = self._hyperloglog(col, error_tolerance)
        elif technique == "countmin":
            result_dict = self._countmin(col, error_tolerance)
        else:  # sampling methods
            result_dict = self._sampling_execute(qtype, col, technique, error_tolerance)

        # Add explanation
        explanation = self._generate_explanation(qtype, col, technique, result_dict, error_tolerance)
        result_dict["explanation"] = explanation
        result_dict["query"] = query

        return result_dict

    # -------------------------
    # Method chooser
    # -------------------------
    def _choose_method(self, qtype, col, error_tolerance):
        if qtype == "COUNT" and col:  # COUNT DISTINCT
            return "hyperloglog"
        elif qtype == "GROUPBY" and col:
            return "countmin"
        elif qtype in ["SUM", "AVG"] or qtype == "COUNT":
            return "random"  # default sampling
        else:
            return "random"

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
    # Sketching methods
    # -------------------------
    def _hyperloglog(self, col, error_tolerance):
        p = max(4, int(math.log2((1.04 / error_tolerance) ** 2)))
        hll = HyperLogLog(p=p)
        for v in self.df[col]:
            hll.update(str(v).encode("utf8"))
        return {
            "method": f"HyperLogLog (p={p})",
            "result": len(hll),
            "estimated_error": round(1.04 / math.sqrt(2**p), 4),
        }

    def _countmin(self, col, error_tolerance):
        w = max(10, int(2 / error_tolerance))
        d = max(5, int(math.log2(1 / error_tolerance)))
        sketch = [defaultdict(int) for _ in range(d)]
        hash_funcs = [lambda x, seed=s: hash((x, seed)) % w for s in range(d)]
        for v in self.df[col]:
            for i, h in enumerate(hash_funcs):
                sketch[i][h(v)] += 1
        estimates = defaultdict(int)
        for v in self.df[col].unique():
            estimates[v] = min(sketch[i][h(v)] for i, h in enumerate(hash_funcs))
        return {
            "method": f"Count-Min Sketch (w={w}, d={d})",
            "result": dict(estimates),
            "estimated_error": round(2 / w, 4),
        }

    # -------------------------
    # Sampling methods
    # -------------------------
    def _sampling_execute(self, qtype, col, technique, error_tolerance):
        frac = max(0.01, min(1.0, 1 - error_tolerance))
        sample = self.df.sample(frac=frac, random_state=42)

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

        return {
            "method": f"{technique.capitalize()} Sampling (frac={frac})",
            "result": result,
            "estimated_error": 1 / np.sqrt(max(1, len(sample))),
            "sample_preview": sample.head(5).to_dict(orient="records"),
        }

    # -------------------------
    # Explanation generator
    # -------------------------
    def _generate_explanation(self, qtype, col, technique, result_dict, error_tolerance):
        explanation = ""
        if technique in ["hyperloglog", "countmin"]:
            explanation += f"This result uses the {technique} sketching method.\n"
            explanation += f"Sketching is chosen because {qtype} queries can be approximated efficiently without scanning all data.\n"
            explanation += f"Estimated error is based on sketch parameters (error_tolerance={error_tolerance})."
        else:
            explanation += f"This result uses {technique} sampling.\n"
            explanation += f"A random subset of the data is used to estimate the {qtype} result.\n"
            explanation += f"Sample fraction: {result_dict.get('parameters', {}).get('sample_fraction', 'N/A') or 'N/A'}\n"
            explanation += f"Estimated error is based on sample size: {round(result_dict['estimated_error'], 6)}"
        return explanation


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    engine = UnifiedQueryEngine("merged_data.csv")

    try:

        print(engine.run_query("SUM amount", error_tolerance=0.05))
        print(engine.run_query("AVG value", error_tolerance=0.05))
        
    except ValueError as e:
        print("Error:", e)
