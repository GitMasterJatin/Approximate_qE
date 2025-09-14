from flask import Flask, request, jsonify
import pandas as pd
import os
from werkzeug.utils import secure_filename
from engine import FastAQE, calculate_accuracy

# --- 1. Initialize Flask App & Config ---
UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'csv', 'parquet'}
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Global "Singleton" Variables ---
aqe_engine = None
raw_df = None
# --- We store the high-level error tolerance ---
engine_params = {"error_tolerance_percent": 1.0}

# --- Centralize the column schema the engine requires ---
ENGINE_COLUMN_CONFIG = {
    "dim_cols": ['category'], "numeric_cols": ['amount', 'value'],
    "distinct_cols": ['user_id', 'category']
}

def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 2. Helper Function to Load/Reload the Engine ---
def load_and_fit_engine(params, dataframe):
    """
    Fits a new engine instance based on the provided error tolerance.
    This is the expensive, multi-second operation.
    """
    print(f"Fitting new engine with params: {params}...")
    # The engine now takes the high-level error percentage directly
    engine = FastAQE(error_tolerance_percent=params['error_tolerance_percent'])
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
    """Endpoint to check engine status and current error tolerance."""
    if aqe_engine:
        return jsonify({
            "status": "ready",
            "total_rows_in_source": aqe_engine.total_rows,
            "sample_table_size": len(aqe_engine.sample_df),
            "current_error_target": f"{engine_params['error_tolerance_percent']}%"
        })
    else:
        return jsonify({"status": "loading or not initialized"}), 503

@app.route('/upload', methods=['POST'])
def upload_file():
    """Allows uploading a new dataset (CSV or Parquet) to re-fit the engine."""
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
            print(f"\n--- Loading new dataset from '{filename}' ---")
            new_df = pd.read_csv(filepath) if filename.endswith('.csv') else pd.read_parquet(filepath)

            # Validate that the new file has the required columns
            required_cols = set(ENGINE_COLUMN_CONFIG['dim_cols'] + ENGINE_COLUMN_CONFIG['numeric_cols'] + ENGINE_COLUMN_CONFIG['distinct_cols'])
            if not required_cols.issubset(new_df.columns):
                missing = list(required_cols - set(new_df.columns))
                return jsonify({"error": f"Uploaded file is missing required columns: {missing}"}), 400
            
            # Re-fit the engine on the new data using the CURRENT error tolerance
            new_engine = load_and_fit_engine(engine_params, new_df)
            aqe_engine, raw_df = new_engine, new_df # Hot-swap the global engine and dataframe
            
            print("--- Engine successfully re-fitted on new dataset. ---")
            return jsonify({
                "message": f"Engine reloaded with data from '{filename}'.",
                "current_error_target": f"{engine_params['error_tolerance_percent']}%"
            })
        except Exception as e:
            return jsonify({"error": f"Failed to process file: {str(e)}"}), 500
    return jsonify({"error": "File type not allowed. Please upload a .csv or .parquet file."}), 400

@app.route('/reload', methods=['POST'])
def reload_engine():
    """Reloads the engine with a new error tolerance on the CURRENT dataset."""
    global aqe_engine, engine_params
    data = request.get_json()
    if not data or 'error_tolerance_percent' not in data:
        return jsonify({"error": "Missing 'error_tolerance_percent' in request body"}), 400
    
    new_error_target = data['error_tolerance_percent']
    
    try:
        if not (0.1 <= new_error_target <= 10.0):
            return jsonify({"error": "error_tolerance_percent must be between 0.1 and 10.0"}), 400
        
        new_params = {"error_tolerance_percent": new_error_target}
        print(f"\n--- Received request to reload engine with new error target: {new_params} ---")
        
        # This is the slow part: re-fit the engine with the new tolerance
        new_engine = load_and_fit_engine(new_params, raw_df)
        aqe_engine, engine_params = new_engine, new_params # Hot-swap
        
        print("--- Engine reload complete. ---")
        return jsonify({"message": "Engine reloaded successfully.", "new_error_target": f"{new_error_target}%"})
    except Exception as e:
        return jsonify({"error": f"Failed to reload engine: {str(e)}"}), 500

@app.route('/query', methods=['POST'])
def handle_query():
    """The main endpoint to process an approximate query."""
    if not aqe_engine:
        return jsonify({"error": "Engine not ready"}), 503
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' key in request body"}), 400
    
    query_str = data['query']
    approx_response = aqe_engine.query(query_str)
    if 'error' in approx_response:
        return jsonify(approx_response), 400
    try:
        exact_response = aqe_engine.exact_query(raw_df, query_str)
        final_response = {
            "query": query_str,
            "explanation": approx_response.get('explanation'),
            "approximate_result": {
                "result": approx_response.get('approx_result'),
                "time_sec": approx_response.get('query_time_sec')
            },
            "exact_result": {
                "result": exact_response.get('exact_result'),
                "time_sec": exact_response.get('query_time_sec')
            },
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
    print("--- Approximate Query Engine API (Accuracy-Driven) ---")
    DATA_FILE = "large_dataset.parquet"
    try:
        print(f"Loading initial dataset from {DATA_FILE}...")
        raw_df = pd.read_parquet(DATA_FILE)
        print("Initial dataset loaded.")
        
        # Fit the engine ONCE at startup with the default error tolerance
        aqe_engine = load_and_fit_engine(engine_params, raw_df)
        print("\n--- Engine is ready. Starting API server. ---")
    except FileNotFoundError:
        print(f"\nFATAL ERROR: Default data file '{DATA_FILE}' not found. Please run 'generate_data.py' first.")
        exit()
    except Exception as e:
        print(f"\nFATAL ERROR: Could not initialize engine. {e}")
        exit()
        
    app.run(debug=True, host='0.0.0.0', port=5000)

