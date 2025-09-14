import pandas as pd
from datasketch import HyperLogLog
from collections import defaultdict
import math
import numpy as np
import random


class SketchingQueryEngine:
    def __init__(self, file_path: str):
        # Load CSV
        self.df = pd.read_csv(file_path)
        self.columns = list(self.df.columns)

    def run_query(self, query: str, error_tolerance: float = 0.05, method: str = None):
        """
        Run approximate queries using sketching or sampling techniques.

        Supported queries:
            COUNT DISTINCT <col>
            GROUPBY <col>
            SUM <col>
            AVG <col>
        """
        parts = query.strip().split()
        if len(parts) == 0:
            raise ValueError("Empty query")

        qtype = parts[0].upper()  # Only uppercase the query type

        if qtype == "COUNT":
            if len(parts) > 1 and parts[1].upper() == "DISTINCT":
                if len(parts) < 3:
                    raise ValueError("Usage: COUNT DISTINCT <col>")
                col = parts[2]
                self._check_column_exists(col)
                return self._hyperloglog(col, error_tolerance)
            else:
                raise ValueError("Sketching engine only supports COUNT DISTINCT")

        elif qtype == "GROUPBY":
            if len(parts) < 2:
                raise ValueError("Usage: GROUPBY <col>")
            col = parts[1]
            self._check_column_exists(col)
            return self._countmin(col, error_tolerance)

        elif qtype in ["SUM", "AVG"]:
            if len(parts) < 2:
                raise ValueError(f"Usage: {qtype} <col>")
            col = parts[1]
            self._check_column_exists(col)
            self._check_numeric_column(col)
            return self._numeric_aggregate(qtype, col, error_tolerance)

        else:
            raise ValueError(f"Unsupported query type: {qtype}")

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
    # HyperLogLog (COUNT DISTINCT)
    # -------------------------
    def _hyperloglog(self, col, error_tolerance):
        p = max(4, int(math.log2((1.04 / error_tolerance) ** 2)))
        hll = HyperLogLog(p=p)
        for v in self.df[col]:
            hll.update(str(v).encode("utf8"))
        return {
            "method": f"HyperLogLog (p={p})",
            "result": len(hll),
            "estimated_error": round(1.04 / math.sqrt(2**p), 4)
        }

    # -------------------------
    # Count-Min Sketch (GROUPBY)
    # -------------------------
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
            "estimated_error": round(2 / w, 4)
        }

    # -------------------------
    # Numeric aggregates using sampling
    # -------------------------
    def _numeric_aggregate(self, qtype, col, error_tolerance):
        frac = max(0.01, min(1.0, 1 - error_tolerance))
        sample = self.df.sample(frac=frac, random_state=42)
        if qtype == "SUM":
            result = sample[col].sum() / frac
        else:  # AVG
            result = sample[col].mean()
        est_error = 1 / np.sqrt(max(1, len(sample)))
        return {
            "method": f"Sampling (frac={frac})",
            "result": result,
            "estimated_error": est_error
        }


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    engine = SketchingQueryEngine("merged_data.csv")

    try:
    
        print(engine.run_query("SUM amount", error_tolerance=0.1))
        print(engine.run_query("AVG value", error_tolerance=0.1))
    except ValueError as e:
        print("Error:", e)
