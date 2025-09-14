from flask import Flask, request, jsonify
import pandas as pd
import os
from werkzeug.utils import secure_filename
from engine import FastAQE, calculate_accuracy # Import our engine logic

# --- 1. Initialize Flask App and Configuration ---
UPLOAD_FOLDER = './uploads' # Folder to store user-uploaded files
ALLOWED_EXTENSIONS = {'csv', 'parquet'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Global Variables ---
# These are our "singletons" that can be replaced by the /reload and /upload endpoints.
aqe_engine = None
raw_df = None # Keep the raw df in memory for all operations

# Store the current parameters globally so they can be reused.
engine_params = {
    "sample_fraction": 0.01,
    "hll_precision": 14
}

# Centralize the column schema the engine expects to use.
# Any uploaded file MUST contain these columns.
ENGINE_COLUMN_CONFIG = {
    "dim_cols": ['category'],
    "numeric_cols": ['amount', 'value'],
    "distinct_cols": ['user_id', 'category']
}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 2. Helper Function to Load/Reload the Engine ---
def load_and_fit_engine(params, dataframe):
    """
    Fits a new engine instance based on the provided parameters and dataframe.
    This is the expensive, multi-second operation.
    """
    print("Fitting new engine instance...")
    engine = FastAQE(
        sample_fraction=params['sample_fraction'],
        hll_precision=params['hll_precision']
    )
    engine.fit(
        dataframe,
        dim_cols=ENGINE_COLUMN_CONFIG['dim_cols'],
        numeric_cols=ENGINE_COLUMN_CONFIG['numeric_cols'],
        distinct_cols=ENGINE_COLUMN_CONFIG['distinct_cols']
    )
    return engine

# --- 3. Define API Endpoints ---
@app.route('/status', methods=['GET'])
def status():
    """A simple endpoint to check if the engine is loaded and ready."""
    if aqe_engine and not aqe_engine.sample_df.empty:
        return jsonify({
            "status": "ready",
            "total_rows_in_source": aqe_engine.total_rows,
            "sample_table_size": len(aqe_engine.sample_df),
            "tunable_parameters": engine_params # Return the current parameters
        })
    else:
        return jsonify({"status": "loading or not initialized"}), 503

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Allows uploading a new dataset (CSV or Parquet) to re-fit the engine.
    This will replace the current dataset for all subsequent queries.
    """
    global aqe_engine, raw_df
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            print(f"\n--- Received request to load new dataset from '{filename}' ---")
            # Load the new dataframe
            if filename.endswith('.csv'):
                new_df = pd.read_csv(filepath)
            else:
                new_df = pd.read_parquet(filepath)

            # --- Critical Validation Step ---
            required_cols = set(ENGINE_COLUMN_CONFIG['dim_cols'] + ENGINE_COLUMN_CONFIG['numeric_cols'] + ENGINE_COLUMN_CONFIG['distinct_cols'])
            if not required_.issubset(new_df.columns):
                missing = required_cols - set(new_df.columns)
                return jsonify({"error": f"Uploaded file is missing required columns: {list(missing)}"}), 400

            # This is the slow part: create and fit a new engine on the new data
            # It uses the currently active global engine_params
            new_engine = load_and_fit_engine(engine_params, new_df)
            
            # Hot-swap the global engine and dataframe
            aqe_engine = new_engine
            raw_df = new_df
            
            print("--- Engine successfully re-fitted on new dataset. ---")
            return jsonify({
                "message": f"Engine successfully reloaded with data from '{filename}'.",
                "new_dataset_shape": {"rows": len(raw_df), "columns": len(raw_df.columns)},
                "current_parameters": engine_params
            })

        except Exception as e:
            print(f"ERROR during file upload processing: {e}")
            return jsonify({"error": f"Failed to process file: {str(e)}"}), 500
    else:
        return jsonify({"error": "File type not allowed. Please upload a .csv or .parquet file."}), 400


@app.route('/reload', methods=['POST'])
def reload_engine():
    """
    Reloads and re-fits the engine with new tunable parameters using the CURRENT dataset.
    This is a slow endpoint and will take several seconds to complete.
    """
    global aqe_engine, engine_params
    
    data = request.get_json()
    if not data: return jsonify({"error": "Missing request body"}), 400

    # Get new parameters, using current ones as default
    new_params = {
        "sample_fraction": data.get("sample_fraction", engine_params["sample_fraction"]),
        "hll_precision": data.get("hll_precision", engine_params["hll_precision"])
    }
    
    try:
        # Validation
        if not (0.001 <= new_params["sample_fraction"] <= 1.0): return jsonify({"error": "sample_fraction must be between 0.001 and 1.0"}), 400
        if not (4 <= new_params["hll_precision"] <= 18): return jsonify({"error": "hll_precision must be between 4 and 18"}), 400

        print(f"\n--- Received request to reload engine with new params: {new_params} ---")
        
        # Re-fit the engine on the current raw_df
        new_engine = load_and_fit_engine(new_params, raw_df)
        
        # Hot-swap the engine and params
        aqe_engine = new_engine
        engine_params = new_params
        
        print("--- Engine reload complete. API is ready with new configuration. ---")
        return jsonify({"message": "Engine reloaded successfully.", "new_parameters": engine_params})

    except Exception as e:
        print(f"ERROR during engine reload: {e}")
        return jsonify({"error": f"Failed to reload engine: {str(e)}"}), 500


@app.route('/query', methods=['POST'])
def handle_query():
    """The main endpoint to process an approximate query."""
    if not aqe_engine: return jsonify({"error": "Engine not ready"}), 503

    data = request.get_json()
    if not data or 'query' not in data: return jsonify({"error": "Missing 'query' key in request body"}), 400
    
    query_str = data['query']
    approx_response = aqe_engine.query(query_str)
    if 'error' in approx_response: return jsonify(approx_response), 400

    try:
        # Run exact query on the currently loaded raw_df
        exact_response = aqe_engine.exact_query(raw_df, query_str)
        
        final_response = {
            "query": query_str, "explanation": approx_response.get('explanation'),
            "approximate_result": {"result": approx_response.get('approx_result'), "execution_time_sec": approx_response.get('query_time_sec')},
            "exact_result": {"result": exact_response.get('exact_result'), "execution_time_sec": exact_response.get('query_time_sec')},
            "comparison": {
                "accuracy": calculate_accuracy(approx_response.get('approx_result'), exact_response.get('exact_result')),
                "speedup_factor": f"{exact_response.get('query_time_sec', 0) / (approx_response.get('query_time_sec', 1) or 1):.2f}x"
            }
        }
        return jsonify(final_response)
    except Exception as e:
        return jsonify({"error": f"Failed to run exact query for comparison: {str(e)}"}), 500


# --- 4. Main execution block to load the engine and run the server ---
if __name__ == '__main__':
    print("--- Approximate Query Engine API ---")
    DATA_FILE = "large_dataset.parquet"
    
    try:
        # Load the initial default dataset
        print(f"Loading initial dataset from {DATA_FILE}...")
        raw_df = pd.read_parquet(DATA_FILE)
        print("Initial dataset loaded.")

        # Fit the engine ONCE at startup with default params and data
        aqe_engine = load_and_fit_engine(engine_params, raw_df)
        print("\n--- Engine is ready. Starting API server. ---")

    except FileNotFoundError:
        print(f"\nFATAL ERROR: Default data file '{DATA_FILE}' not found.")
        print("Please run 'python generate_data.py' first to create it.")
        exit()
    except Exception as e:
        print(f"\nFATAL ERROR: Could not initialize engine. {e}")
        exit()
        
    # Run the Flask server
    app.run(debug=True, host='0.0.0.0', port=5000)