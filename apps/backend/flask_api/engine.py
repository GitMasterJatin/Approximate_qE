import pandas as pd
import numpy as np
from datasketches import kll_floats_sketch, hll_sketch
from collections import defaultdict
import time
import math
import random

def calculate_accuracy(approx, exact):
    """Helper function to calculate the accuracy of an approximate result."""
    try:
        if isinstance(exact, dict):
            # Logic for GROUP BY
            total_relative_error = 0
            count = 0
            if not exact: return "N/A (empty exact result)"
            for key, exact_val in exact.items():
                if exact_val == 0: continue
                approx_val = approx.get(key, 0)
                total_relative_error += abs(approx_val - exact_val) / abs(exact_val)
                count += 1
            if count == 0: return "N/A (no valid groups to compare)"
            avg_relative_error = total_relative_error / count
            return f"(Avg. Relative Error: {avg_relative_error * 100:.4f}%)"
        elif isinstance(exact, (int, float)):
            # Logic for single numbers
            if exact == 0: return "100.0000%" if approx == 0 else "N/A"
            error_frac = abs(approx - exact) / abs(exact)
            accuracy_pct = 100.0 * (1.0 - error_frac)
            return f"{accuracy_pct:.4f}% (Error: {error_frac * 100:.4f}%)"
    except Exception as e:
        return f"(Calculation Failed: {e})"
    return "(Unsupported data type)"

class FastAQE:
    """An Approximate Query Engine driven by a user-defined error tolerance."""
    
    # --- CHANGED: __init__ now takes a high-level error tolerance ---
    def __init__(self, error_tolerance_percent: float = 1.0):
        if not (0.1 <= error_tolerance_percent <= 10.0):
            raise ValueError("Error tolerance must be between 0.1% and 10.0%")
        self.error_tolerance = error_tolerance_percent / 100.0
        
        # Internal parameters will be CALCULATED in the fit() method
        self.sample_frac = None
        self.hll_p = None
        
        # Data Stores
        self.sample_df = pd.DataFrame()
        self.total_rows = 0
        self.hll_sketches = defaultdict(lambda: hll_sketch(self.hll_p))
        self.kll_k = 256
        self.kll_sketches = defaultdict(lambda: kll_floats_sketch(k=self.kll_k))

    def fit(self, df: pd.DataFrame, dim_cols: list, numeric_cols: list, distinct_cols: list):
        """The OFFLINE ingestion step. It now CALCULATES its own internal parameters."""
        print("Starting offline ingestion (fit)... This is the one-time preprocessing cost.")
        self.total_rows = len(df)
        if self.total_rows == 0:
            raise ValueError("Input DataFrame is empty")

        # --- NEW: Calculate internal parameters based on error tolerance ---
        # 1. Calculate HLL precision 'p'
        # Formula: p = log2((1.04 / error)^2)
        self.hll_p = math.ceil(math.log2((1.04 / self.error_tolerance)**2))
        self.hll_p = max(4, min(18, self.hll_p)) # Clamp to a reasonable range
        print(f"  Target Error: {self.error_tolerance*100:.2f}% -> Calculated HLL Precision (p): {self.hll_p}")
        
        # 2. Calculate Sample Fraction
        # Formula: sample_size = 1 / error^2
        # We add a buffer by making it a bit larger
        required_sample_size = 1.5 / (self.error_tolerance**2)
        self.sample_frac = required_sample_size / self.total_rows
        self.sample_frac = max(0.001, min(1.0, self.sample_frac)) # Clamp to a reasonable range
        print(f"  Target Error: {self.error_tolerance*100:.2f}% -> Calculated Sample Fraction: {self.sample_frac:.4f}")

        # --- Build Stratified Sample ---
        print(f"  Building {self.sample_frac*100:.2f}% stratified sample for SUM/AVG queries...")
        if dim_cols:
            self.sample_df = df.groupby(dim_cols).sample(frac=self.sample_frac, replace=True)
        else:
            self.sample_df = df.sample(frac=self.sample_frac, replace=True)

        # --- Build HLL Sketches (now uses calculated precision) ---
        print("  Building HLL sketches for COUNT DISTINCT queries...")
        # We need to re-initialize the defaultdict factory with the new hll_p
        self.hll_sketches = defaultdict(lambda: hll_sketch(self.hll_p))
        for col in distinct_cols:
            sketch = self.hll_sketches[col] 
            for val in df[col].dropna():
                sketch.update(str(val))

        # --- Build KLL Sketches ---
        print("  Building KLL sketches for Quantile queries...")
        for col in numeric_cols:
             sketch = self.kll_sketches[col]
             for val in df[col].dropna():
                 sketch.update(val)
        
        print(f"Fit complete. Engine is ready. Summary size: {len(self.sample_df)} sample rows.")

    def query(self, q_str: str):
        """The ONLINE query step. Reads only the small summaries."""
        # This method does not need to be changed, only the explanation text.
        start_time = time.perf_counter()
        parts = q_str.strip().upper().split()
        q_type = parts[0]
        
        result, error_bound, explanation = None, None, "Query not supported."
        
        try:
            if q_type == 'COUNT' and len(parts) > 1 and parts[1] == 'DISTINCT':
                col = parts[2].lower()
                if col not in self.hll_sketches: raise ValueError(f"No HLL sketch for column: {col}")
                sketch = self.hll_sketches[col]
                result = sketch.get_estimate()
                error_bound = sketch.get_upper_bound(1) - result 
                explanation = (
                    f"Query Parsed: COUNT DISTINCT on column '{col}'.\n"
                    f"Routing Decision: Routed to the HLL sketch (precision p={self.hll_p}) which was built to meet the {self.error_tolerance*100:.2f}% error target."
                )
            elif q_type == 'SUM' and 'GROUP' in parts and 'BY' in parts:
                col_to_sum, group_col = parts[1].lower(), parts[4].lower()
                sample_agg = self.sample_df.groupby(group_col)[col_to_sum].sum()
                result = (sample_agg / self.sample_frac).to_dict()
                error_bound = "Error proportional to 1/sqrt(sample_size)"
                explanation = (
                    f"Query Parsed: SUM({col_to_sum}) GROUP BY {group_col}.\n"
                    f"Routing Decision: Routed to the Stratified Sample Table (fraction={self.sample_frac:.4f}, n={len(self.sample_df)}) built to meet the {self.error_tolerance*100:.2f}% error target."
                )
            elif q_type == 'MEDIAN' or q_type == 'QUANTILE':
                is_median = q_type == 'MEDIAN'
                col = parts[1].lower()
                quantile = 0.5 if is_median else float(parts[2]) if len(parts) > 2 else -1
                if quantile < 0: raise ValueError("QUANTILE query missing value.")
                if col not in self.kll_sketches: raise ValueError(f"No KLL sketch for column: {col}")
                sketch = self.kll_sketches[col]
                result = sketch.get_quantile(quantile)
                error_bound = f"Approx. {kll_floats_sketch.get_normalized_rank_error(self.kll_k, False)*100:.2f}% rank error"
                explanation = (
                    f"Query Parsed: {q_type} on column '{col}'.\n"
                    f"Routing Decision: Routed to the KLL (Quantile) sketch. Note: KLL sketch accuracy is fixed by its 'k' parameter, not the global error tolerance."
                )
            else:
                 raise ValueError(f"Unsupported query type: {q_type}")
            end_time = time.perf_counter()
            return {"query": q_str, "approx_result": result, "estimated_error": error_bound, "query_time_sec": (end_time - start_time), "explanation": explanation}
        except Exception as e:
            return {"error": str(e), "explanation": f"Query Failed: {e}"}

    def exact_query(self, df: pd.DataFrame, q_str: str):
        """Helper to run the equivalent EXACT query for speed comparison."""
        # This method is unchanged
        start_time = time.perf_counter()
        parts = q_str.strip().upper().split()
        q_type = parts[0]
        result = None
        if q_type == 'COUNT' and parts[1] == 'DISTINCT':
            result = df[parts[2].lower()].nunique()
        elif q_type == 'SUM' and 'GROUP' in parts:
            result = df.groupby(parts[4].lower())[parts[1].lower()].sum().to_dict()
        elif q_type == 'QUANTILE':
            result = df[parts[1].lower()].quantile(float(parts[2]))
        elif q_type == 'MEDIAN':
            result = df[parts[1].lower()].median()
        else:
            raise ValueError(f"Unsupported exact query type: {q_type}")
        end_time = time.perf_counter()
        return {"query": q_str, "exact_result": result, "query_time_sec": (end_time - start_time)}

