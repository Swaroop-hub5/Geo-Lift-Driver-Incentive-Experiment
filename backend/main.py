from fastapi import FastAPI
from .simulation import GeoSimulator
from .analysis import calculate_did
import pandas as pd

app = FastAPI()
simulator = GeoSimulator()

@app.post("/run-geo-experiment")
def run_geo_experiment(uplift: float = 0.15):
    # 1. Simulate
    df = simulator.generate_city_data(uplift_percent=uplift)
    
    # 2. Analyze
    results = calculate_did(df)
    
    # 3. Format for Frontend
    # Convert dates to string format for JSON
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    
    return {
        "results": results,
        "raw_data": df.to_dict(orient='records')
    }

if __name__ == "__main__":
    import uvicorn
    # Using Port 8001 to avoid conflict with Project 1
    uvicorn.run(app, host="0.0.0.0", port=8001)