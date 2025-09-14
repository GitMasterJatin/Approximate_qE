from flask import Flask, request, jsonify
import pandas as pd
import os
from werkzeug.utils import secure_filename
from engine import FastAQE, calculate_accuracy
from flask_cors import CORS
# --- 1. Initialize Flask App & Config ---
UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'csv', 'parquet'}
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
CORS(app)
# --- Global "Singleton" Variables ---
aqe_engine = None
raw_df = None
engine_params = {"error_tolerance_percent": 1.0}
active_column_config = None

def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 2. Helper Function to Load/Reload the Engine ---
def load_and_fit_engine(params, dataframe, column_config):
    """Fits a new engine instance with dynamic parameters AND column configuration."""
    print(f"Fitting new engine with params: {params} and column config...")
    engine = FastAQE(error_tolerance_percent=params['error_tolerance_percent'])
    engine.fit(dataframe, column_config)
    return engine

# --- 3. Define API Endpoints ---
@app.route('/status', methods=['GET'])
def status():
    """Endpoint to check engine status and current configurations."""
    if aqe_engine:
        return jsonify({
            "status": "ready",
            "total_rows_in_source": aqe_engine.total_rows,
            "current_error_target": f"{engine_params['error_tolerance_percent']}%",
            "active_column_config": active_column_config
        })
    else:
        return jsonify({"status": "Engine not initialized. Please upload a file."}), 503

@app.route('/upload', methods=['POST'])
def upload_and_configure():
    """
    Uploads a new dataset and configures the engine based on form data.
    This is now the main entry point for fitting the engine.
    """
    global aqe_engine, raw_df, active_column_config
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        # Extract column configuration from form fields
        new_config = {
            "dim_cols": [col.strip() for col in request.form.get('dim_cols', '').split(',') if col.strip()],
            "numeric_cols": [col.strip() for col in request.form.get('numeric_cols', '').split(',') if col.strip()],
            "distinct_cols": [col.strip() for col in request.form.get('distinct_cols', '').split(',') if col.strip()]
        }
        if not any(new_config.values()):
             return jsonify({"error": "Form fields 'dim_cols', 'numeric_cols', or 'distinct_cols' must be provided."}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            print(f"\n--- Loading new dataset from '{filename}' with config: {new_config} ---")
            new_df = pd.read_csv(filepath) if filename.endswith('.csv') else pd.read_parquet(filepath)

            # Validate that all configured columns actually exist in the dataframe
            all_config_cols = set(new_config['dim_cols'] + new_config['numeric_cols'] + new_config['distinct_cols'])
            if not all_config_cols.issubset(new_df.columns):
                missing = list(all_config_cols - set(new_df.columns))
                return jsonify({"error": f"Configured columns not found in file: {missing}"}), 400

            # Re-fit the engine with the new data and new configuration
            new_engine = load_and_fit_engine(engine_params, new_df, new_config)
            
            # Hot-swap all global state
            aqe_engine, raw_df, active_column_config = new_engine, new_df, new_config
            
            print("--- Engine successfully configured and fitted on new dataset. ---")
            return jsonify({
                "message": f"Engine configured and loaded with data from '{filename}'.",
                "active_column_config": active_column_config
            })
    except Exception as e:
        return jsonify({"error": f"Failed to process file and configuration: {str(e)}"}), 500
    return jsonify({"error": "Invalid file type."}), 400

@app.route('/reload', methods=['POST'])
def reload_engine():
    """Reloads the engine with a new error tolerance on the CURRENT dataset and config."""
    global aqe_engine, engine_params
    
    # --- THIS IS THE FIX ---
    # The old code `if not raw_df:` caused the crash.
    # The new code `if raw_df is None:` is the correct, unambiguous way to check.
    if raw_df is None or active_column_config is None:
        return jsonify({"error": "No dataset is loaded. Please use /upload first."}), 400
    
    data = request.get_json()
    if not data or 'error_tolerance_percent' not in data:
        return jsonify({"error": "Missing 'error_tolerance_percent' in request body"}), 400
    
    new_error_target = data['error_tolerance_percent']
    if not (0.1 <= new_error_target <= 10.0):
        return jsonify({"error": "error_tolerance_percent must be between 0.1 and 10.0"}), 400
    
    try:
        new_params = {"error_tolerance_percent": new_error_target}
        print(f"\n--- Reloading engine with new error target: {new_params} ---")
        
        # Re-fit using the current dataset and config
        new_engine = load_and_fit_engine(new_params, raw_df, active_column_config)
        aqe_engine, engine_params = new_engine, new_params
        
        print("--- Engine reload complete. ---")
        return jsonify({"message": "Engine reloaded successfully.", "new_error_target": f"{new_error_target}%"})
    except Exception as e:
        return jsonify({"error": f"Failed to reload engine: {str(e)}"}), 500

@app.route('/query', methods=['POST'])
def handle_query():
    """The main endpoint to process an approximate query."""
    if not aqe_engine:
        return jsonify({"error": "Engine not ready. Please use /upload to configure it."}), 503
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' key"}), 400
    
    query_str = data['query']
    approx_response = aqe_engine.query(query_str)
    if 'error' in approx_response:
        return jsonify(approx_response), 400
    
    try:
        exact_response = aqe_engine.exact_query(raw_df, query_str)
    except Exception as e:
        # If exact fails, return approx only, which is still useful
        return jsonify({
            "warning": f"Could not compute exact result for comparison: {str(e)}",
            "query": query_str,
            "explanation": approx_response.get('explanation'),
            "approximate_result": {
                "result": approx_response.get('approx_result'),
                "time_sec": approx_response.get('query_time_sec')
            }
        })

    final_response = {
        "query": query_str, "explanation": approx_response.get('explanation'),
        "approximate_result": {"result": approx_response.get('approx_result'), "time_sec": approx_response.get('query_time_sec')},
        "exact_result": {"result": exact_response.get('exact_result'), "time_sec": exact_response.get('query_time_sec')},
        "comparison": {
            "accuracy": calculate_accuracy(approx_response.get('approx_result'), exact_response.get('exact_result')),
            "speedup_factor": f"{exact_response.get('query_time_sec', 0) / (approx_response.get('query_time_sec', 1) or 1):.2f}x"
        }
    }
    return jsonify(final_response)

# --- 4. Main execution block (starts in an un-configured state) ---
if __name__ == '__main__':
    print("--- Approximate Query Engine API (Dynamic Configuration) ---")
    print("Server is starting in an un-configured state.")
    print("Please use the /upload endpoint to load a dataset and provide column configuration.")
    print("API is ready and listening...")
    app.run(debug=True, host='0.0.0.0', port=5000)

