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
            total_relative_error, count = 0, 0
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
    
    def __init__(self, error_tolerance_percent: float = 1.0):
        if not (0.1 <= error_tolerance_percent <= 10.0):
            raise ValueError("Error tolerance must be between 0.1% and 10.0%")
        self.error_tolerance = error_tolerance_percent / 100.0
        
        # Internal parameters will be CALCULATED in the fit() method
        self.sample_frac, self.hll_p = None, None
        self.active_column_config = {}
        
        # Data Stores
        self.sample_df, self.total_rows = pd.DataFrame(), 0
        self.hll_sketches = defaultdict(lambda: hll_sketch(self.hll_p))
        self.kll_k = 256
        self.kll_sketches = defaultdict(lambda: kll_floats_sketch(k=self.kll_k))

    def fit(self, df: pd.DataFrame, column_config: dict):
        """The OFFLINE ingestion step. It now accepts a dynamic column configuration."""
        print("Starting offline ingestion (fit)... This is the one-time preprocessing cost.")
        self.total_rows = len(df)
        self.active_column_config = column_config # Store the config
        if self.total_rows == 0: raise ValueError("Input DataFrame is empty")

        # --- Calculate internal parameters based on error tolerance ---
        self.hll_p = math.ceil(math.log2((1.04 / self.error_tolerance)**2))
        self.hll_p = max(4, min(18, self.hll_p))
        
        required_sample_size = 1.5 / (self.error_tolerance**2)
        self.sample_frac = max(0.001, min(1.0, required_sample_size / self.total_rows))
        print(f"  Target Error: {self.error_tolerance*100:.2f}% -> HLL Precision(p): {self.hll_p}, Sample Fraction: {self.sample_frac:.4f}")

        # --- Build Summaries using the provided column config ---
        dim_cols = column_config.get('dim_cols', [])
        numeric_cols = column_config.get('numeric_cols', [])
        distinct_cols = column_config.get('distinct_cols', [])

        print(f"  Building {self.sample_frac*100:.2f}% stratified sample...")
        if dim_cols:
            self.sample_df = df.groupby(dim_cols).sample(frac=self.sample_frac, replace=True)
        else:
            self.sample_df = df.sample(frac=self.sample_frac, replace=True)

        print("  Building HLL sketches for COUNT DISTINCT...")
        self.hll_sketches = defaultdict(lambda: hll_sketch(self.hll_p))
        for col in distinct_cols:
            sketch = self.hll_sketches[col] 
            for val in df[col].dropna(): sketch.update(str(val))

        print("  Building KLL sketches for Quantile queries...")
        self.kll_sketches = defaultdict(lambda: kll_floats_sketch(k=self.kll_k))
        for col in numeric_cols:
             sketch = self.kll_sketches[col]
             for val in df[col].dropna(): sketch.update(val)
        
        print(f"Fit complete. Engine is ready. Summary size: {len(self.sample_df)} sample rows.")

    def query(self, q_str: str):
        """The ONLINE query step. It now uses a more flexible parser."""
        start_time = time.perf_counter()
        parts = q_str.strip().upper().split()
        q_type = parts[0]
        
        try:
            # --- NEW: More flexible query parsing and validation ---
            if q_type == 'COUNT' and len(parts) > 2 and parts[1] == 'DISTINCT':
                col = parts[2].lower()
                if col not in self.active_column_config.get('distinct_cols', []):
                    raise ValueError(f"Column '{col}' is not configured for DISTINCT COUNTs. Configured columns: {self.active_column_config.get('distinct_cols')}")
                return self._run_hll_query(q_str, col, start_time)
                
            elif q_type == 'SUM' and 'GROUP' in parts and 'BY' in parts:
                col_to_sum = parts[1].lower()
                group_col = parts[4].lower()
                if col_to_sum not in self.active_column_config.get('numeric_cols', []):
                    raise ValueError(f"Column '{col_to_sum}' is not configured as numeric. Configured columns: {self.active_column_config.get('numeric_cols')}")
                if group_col not in self.active_column_config.get('dim_cols', []):
                    raise ValueError(f"Column '{group_col}' is not configured as a dimension for grouping. Configured columns: {self.active_column_config.get('dim_cols')}")
                return self._run_sample_query(q_str, col_to_sum, group_col, start_time)
                
            elif q_type in ['MEDIAN', 'QUANTILE']:
                col = parts[1].lower()
                if col not in self.active_column_config.get('numeric_cols', []):
                    raise ValueError(f"Column '{col}' is not configured as numeric for quantiles. Configured columns: {self.active_column_config.get('numeric_cols')}")
                return self._run_kll_query(q_str, col, start_time)
            
            else:
                 raise ValueError(f"Unsupported query structure: '{q_str}'")

        except (IndexError, ValueError) as e:
            return {"error": str(e), "explanation": f"Query Parsing Failed: {e}"}

    # --- Private helper methods for cleaner execution paths ---
    def _run_hll_query(self, q_str, col, start_time):
        sketch = self.hll_sketches[col]
        result = sketch.get_estimate()
        explanation = f"Query routed to HLL sketch (p={self.hll_p}) for '{col}' to meet the {self.error_tolerance*100:.2f}% error target."
        end_time = time.perf_counter()
        return {"query": q_str, "approx_result": result, "query_time_sec": end_time - start_time, "explanation": explanation}

    def _run_sample_query(self, q_str, col_to_sum, group_col, start_time):
        sample_agg = self.sample_df.groupby(group_col)[col_to_sum].sum()
        result = (sample_agg / self.sample_frac).to_dict()
        explanation = f"Query routed to the Stratified Sample Table (frac={self.sample_frac:.4f}) built to meet the {self.error_tolerance*100:.2f}% error target."
        end_time = time.perf_counter()
        return {"query": q_str, "approx_result": result, "query_time_sec": end_time - start_time, "explanation": explanation}

    def _run_kll_query(self, q_str, col, start_time):
        parts = q_str.strip().upper().split()
        q_type = parts[0]
        quantile = 0.5 if q_type == 'MEDIAN' else float(parts[2])
        sketch = self.kll_sketches[col]
        result = sketch.get_quantile(quantile)
        explanation = f"Query routed to KLL sketch for '{col}'. Note: KLL sketch accuracy is fixed by its 'k' parameter, not the global error tolerance."
        end_time = time.perf_counter()
        return {"query": q_str, "approx_result": result, "query_time_sec": end_time - start_time, "explanation": explanation}

    def exact_query(self, df: pd.DataFrame, q_str: str):
        """Helper to run the equivalent EXACT query for speed comparison."""
        start_time = time.perf_counter()
        parts = q_str.strip().upper().split()
        q_type = parts[0]
        try:
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
            return {"query": q_str, "exact_result": result, "query_time_sec": end_time - start_time}
        except (IndexError, KeyError) as e:
            return {"error": f"Exact query failed: Column not found or invalid query structure. Details: {e}"}

