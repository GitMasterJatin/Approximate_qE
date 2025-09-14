import pandas as pd
import numpy as np
from datasketches import kll_floats_sketch, hll_sketch
from collections import defaultdict
import time
import math
import random

def calculate_accuracy(approx, exact):
    """
    Helper function to calculate and print the accuracy of an approximate result.
    Handles both single numbers (for COUNT DISTINCT/QUANTILE) and dicts (for GROUP BY).
    """
    try:
        if isinstance(exact, dict):
            # --- Logic for GROUP BY (dict comparison) ---
            total_relative_error = 0
            count = 0
            if not exact: 
                return "N/A (empty exact result)"
            
            for key, exact_val in exact.items():
                if exact_val == 0: 
                    continue # Skip division by zero
                
                approx_val = approx.get(key, 0) # Get approx value, default to 0 if key is missing
                total_relative_error += abs(approx_val - exact_val) / abs(exact_val)
                count += 1
                
            if count == 0: 
                return "N/A (no valid groups to compare)"
            
            avg_relative_error = total_relative_error / count
            return f"(Avg. Relative Error: {avg_relative_error * 100:.4f}%)"
        
        elif isinstance(exact, (int, float)):
            # --- Logic for single numbers (COUNT DISTINCT, MEDIAN, etc.) ---
            if exact == 0:
                if approx == 0:
                    return "100.0000% (Error: 0.0000%)"
                return f"N/A (Exact result is 0)"
                
            error_frac = abs(approx - exact) / abs(exact)
            accuracy_pct = 100.0 * (1.0 - error_frac)
            return f"{accuracy_pct:.4f}% (Error: {error_frac * 100:.4f}%)"
            
    except Exception as e:
        return f"(Calculation Failed: {e})"
    
    return "(Unsupported data type for comparison)"


class FastAQE:
    """
    An Approximate Query Engine that works by pre-computing summaries (sketches
    and samples) offline during a .fit() step, and answering queries instantly
    by reading those summaries at .query() time.
    """
    def __init__(self, sample_fraction: float = 0.01, hll_precision: int = 14):
        self.sample_frac = sample_fraction
        self.hll_p = hll_precision
        
        # Data Stores
        self.sample_df = pd.DataFrame()
        self.total_rows = 0
        self.hll_sketches = defaultdict(lambda: hll_sketch(self.hll_p))
        self.kll_k = 256  # Store k so we can access it for the static error method
        self.kll_sketches = defaultdict(lambda: kll_floats_sketch(k=self.kll_k))

    def fit(self, df: pd.DataFrame, dim_cols: list, numeric_cols: list, distinct_cols: list):
        """
        The OFFLINE ingestion step. Scans the full dataset ONCE to build summaries.
        """
        print("Starting offline ingestion (fit)... This is the one-time preprocessing cost.")
        self.total_rows = len(df)
        if self.total_rows == 0:
            raise ValueError("Input DataFrame is empty")

        # --- Build Stratified Sample ---
        print(f"  Building {self.sample_frac*100:.0f}% stratified sample for SUM/AVG queries...")
        if dim_cols:
            # This is the modern, correct, and faster way to do stratified sampling.
            self.sample_df = df.groupby(dim_cols).sample(frac=self.sample_frac, replace=True)
        else:
            self.sample_df = df.sample(frac=self.sample_frac, replace=True)

        # --- Build HLL Sketches ---
        print("  Building HLL sketches for COUNT DISTINCT queries...")
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
        """
        The ONLINE query step. Reads only the small summaries.
        """
        start_time = time.perf_counter()
        parts = q_str.strip().upper().split()
        q_type = parts[0]
        
        result = None
        error_bound = None
        explanation = "Query not supported or did not match any execution path." # Default explanation
        
        try:
            if q_type == 'COUNT' and len(parts) > 1 and parts[1] == 'DISTINCT':
                # --- Query Path 1: COUNT DISTINCT ---
                col = parts[2].lower()
                if col not in self.hll_sketches:
                    raise ValueError(f"No HLL sketch was built for column: {col}")
                
                sketch = self.hll_sketches[col]
                result = sketch.get_estimate()
                error_bound = sketch.get_upper_bound(1) - result 
                
                # Generate explanation
                explanation = (
                    f"Query Parsed: COUNT DISTINCT on column '{col}'.\n"
                    f"Routing Decision: Query routed to the pre-built HyperLogLog (HLL) sketch.\n"
                    f"Reason: HLL is the optimal structure for high-speed, low-memory unique counts. "
                    f"This avoids a full scan of the raw data."
                )
                
            elif q_type == 'SUM' and 'GROUP' in parts and 'BY' in parts:
                # --- Query Path 2: SUM... GROUP BY ---
                col_to_sum = parts[1].lower()
                group_col = parts[4].lower()
                
                sample_agg = self.sample_df.groupby(group_col)[col_to_sum].sum()
                result = (sample_agg / self.sample_frac).to_dict()
                error_bound = f"Error proportional to 1/sqrt(sample_size_per_group)"
                
                # Generate explanation
                explanation = (
                    f"Query Parsed: SUM({col_to_sum}) GROUP BY {group_col}.\n"
                    f"Routing Decision: Query routed to the {self.sample_frac*100:.0f}% Stratified Sample Table (n={len(self.sample_df)} rows).\n"
                    f"Reason: This sample is statistically representative and guaranteed to contain all groups, "
                    f"allowing fast aggregation. The result is extrapolated to estimate the full dataset."
                )
                
            elif q_type == 'MEDIAN':
                # --- Query Path 3: MEDIAN ---
                col = parts[1].lower()
                if col not in self.kll_sketches:
                    raise ValueError(f"No KLL sketch was built for numeric column: {col}")
                
                sketch = self.kll_sketches[col]
                result = sketch.get_quantile(0.5) 
                error_bound = f"Approx. {kll_floats_sketch.get_normalized_rank_error(self.kll_k, False)*100:.2f}% rank error"

                # Generate explanation
                explanation = (
                    f"Query Parsed: MEDIAN (50th percentile) on column '{col}'.\n"
                    f"Routing Decision: Query routed to the pre-built KLL (Quantile) sketch.\n"
                    f"Reason: The KLL sketch stores the data's statistical distribution. "
                    f"This allows for instant calculation of any quantile without sorting the raw data."
                )

            elif q_type == 'QUANTILE':
                 # --- Query Path 4: QUANTILE ---
                if len(parts) < 3:
                    raise ValueError("QUANTILE query missing value. Must be 'QUANTILE col 0.xx'")
                
                col = parts[1].lower()
                quantile = float(parts[2])
                
                if col not in self.kll_sketches:
                    raise ValueError(f"No KLL sketch was built for numeric column: {col}")

                sketch = self.kll_sketches[col]
                result = sketch.get_quantile(quantile)
                error_bound = f"Approx. {kll_floats_sketch.get_normalized_rank_error(self.kll_k, False)*100:.2f}% rank error"

                # Generate explanation
                explanation = (
                    f"Query Parsed: QUANTILE ({(quantile * 100):.0f}th percentile) on column '{col}'.\n"
                    f"Routing Decision: Query routed to the pre-built KLL (Quantile) sketch.\n"
                    f"Reason: The KLL sketch stores the data's statistical distribution. "
                    f"This allows for instant calculation of any quantile without sorting the raw data."
                )

            else:
                 raise ValueError(f"Unsupported query type: {q_type}")

            end_time = time.perf_counter()
            return {
                "query": q_str,
                "approx_result": result,
                "estimated_error": error_bound,
                "query_time_sec": (end_time - start_time),
                "explanation": explanation
            }
            
        except Exception as e:
            # Also return an explanation on failure
            explanation = (
                f"Query Failed: The query '{q_str}' could not be executed.\n"
                f"Error: {str(e)}"
            )
            return {"error": str(e), "explanation": explanation}

    def exact_query(self, df: pd.DataFrame, q_str: str):
        """Helper to run the equivalent EXACT query for speed comparison."""
        start_time = time.perf_counter()
        parts = q_str.strip().upper().split()
        q_type = parts[0]
        result = None

        if q_type == 'COUNT' and parts[1] == 'DISTINCT':
            col = parts[2].lower()
            result = df[col].nunique()
        elif q_type == 'SUM' and 'GROUP' in parts:
            col_to_sum = parts[1].lower()
            group_col = parts[4].lower()
            result = df.groupby(group_col)[col_to_sum].sum().to_dict()
        elif q_type == 'QUANTILE':
            col = parts[1].lower()
            quantile = float(parts[2])
            result = df[col].quantile(quantile)
        elif q_type == 'MEDIAN':
            col = parts[1].lower()
            result = df[col].median()
        else:
            raise ValueError("Unsupported exact query")
            
        end_time = time.perf_counter()
        return {
            "query": q_str,
            "exact_result": result,
            "query_time_sec": (end_time - start_time)
        }