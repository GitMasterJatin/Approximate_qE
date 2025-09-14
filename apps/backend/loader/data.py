# File: generate_data.py
import pandas as pd
import numpy as np
import random
import os

NUM_ROWS = 5_000_000
DATA_FILE = "large_dataset.parquet" # We will save to Parquet for speed

def generate_and_save():
    if os.path.exists(DATA_FILE):
        print(f"Data file '{DATA_FILE}' already exists. Skipping generation.")
        return

    print(f"Generating dummy data ({NUM_ROWS} rows)... This will take a moment.")
    
    # This is the same logic from your main script
    data = {
        'amount': np.random.lognormal(mean=3.0, sigma=1.0, size=NUM_ROWS),
        'value': np.random.normal(loc=100, scale=25, size=NUM_ROWS),
        'category': [random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G']) for _ in range(NUM_ROWS)],
        'user_id': [f"user_{random.randint(1, NUM_ROWS // 10)}" for _ in range(NUM_ROWS)]
    }
    
    raw_df = pd.DataFrame(data)
    
    print(f"Generation complete. Saving to '{DATA_FILE}'...")
    
    # Save to Parquet. This is much faster than CSV.
    raw_df.to_parquet(DATA_FILE, index=False)
    
    print("Save complete.")

if __name__ == "__main__":
    generate_and_save()