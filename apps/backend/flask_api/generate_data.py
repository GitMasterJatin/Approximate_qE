import pandas as pd
import numpy as np
import random
import os
import argparse  # Import the library for command-line arguments

# --- Configuration ---
# The default file name the API server looks for on startup.
DEFAULT_DATA_FILE = "large_dataset51.csv"

def generate_and_save(num_rows, output_file):
    """
    Generates a dummy dataset with a specified number of rows and saves it to a CSV file.
    """
    if os.path.exists(output_file):
        print(f"Data file '{output_file}' already exists. Skipping generation.")
        return

    print(f"Generating dummy data ({num_rows:,} rows)... This will take a moment.")
    
    # The data generation logic remains the same
    data = {
        'amount': np.random.lognormal(mean=2.5, sigma=1.3, size=num_rows),
        'value': np.random.normal(loc=140, scale=42, size=num_rows),
        'category': [random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G']) for _ in range(num_rows)],
        'user_id': [f"user_{random.randint(1, num_rows // 10 if num_rows > 10 else num_rows)}" for _ in range(num_rows)]
    }
    
    raw_df = pd.DataFrame(data)
    
    print(f"Generation complete. Saving to '{output_file}'...")
    
    # Save to CSV
    raw_df.to_csv(output_file, index=False)
    
    print("Save complete.")

if __name__ == "__main__":
    # --- 1. Set up Argument Parser ---
    # This allows us to read arguments from the command line.
    parser = argparse.ArgumentParser(
        description="Generate a dummy dataset for the Approximate Query Engine."
    )
    
    # --- 2. Define the '--rows' argument ---
    # It's an integer, and it has a default value if the user provides nothing.
    parser.add_argument(
        "--rows",
        type=int,
        default=5_000_000,
        help="The number of rows to generate in the dataset. (Default: 5,000,000)"
    )
    
    args = parser.parse_args()

    # --- 3. Run the generation function with the user-provided (or default) number of rows ---
    generate_and_save(num_rows=args.rows, output_file=DEFAULT_DATA_FILE)

