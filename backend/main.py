from fastapi import FastAPI, HTTPException
from simulation import GeoSimulator
from analysis import calculate_did
import pandas as pd
import numpy as np
import math

app = FastAPI()
simulator = GeoSimulator()

# Helper function to sanitize JSON (Convert NaN/Infinity to None)
def sanitize_floats(data):
    if isinstance(data, dict):
        return {k: sanitize_floats(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_floats(v) for v in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
    return data

@app.post("/run-geo-experiment")
def run_geo_experiment(uplift: float = 0.15):
    """
    Runs the simulation and returns Advanced DiD analysis (OLS Regression).
    Includes safety handling for Regression outputs (NaNs).
    """
    try:
        # 1. Simulate
        # We use a default seed for consistency, but you can random.randint() it if you want dynamic demos
        df = simulator.generate_city_data(uplift_percent=uplift, random_seed=42)
        
        # 2. Analyze (Using the Advanced OLS version)
        try:
            results = calculate_did(df)
        except Exception as e:
            # Catch regression errors (e.g., if data variance is 0)
            raise HTTPException(status_code=500, detail=f"Regression Analysis Failed: {str(e)}")
        
        # 3. Format for Frontend
        # Convert dates to string format for JSON
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        
        # 4. Sanitize Results
        # Statsmodels often returns NaN p-values if the fit is perfect. 
        # We convert them to None so the JSON doesn't crash.
        clean_results = sanitize_floats(results)
        
        return {
            "results": clean_results,
            "raw_data": df.to_dict(orient='records')
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Using Port 8001 to distinguish from Project 1
    uvicorn.run(app, host="0.0.0.0", port=8001)