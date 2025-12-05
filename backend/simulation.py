import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class GeoSimulator:
    def __init__(self):
        # 4 Cities: 2 Treatment (Get Bonus), 2 Control (No Bonus)
        self.cities = {
            'Tallinn': {'type': 'Treatment', 'lat': 59.4370, 'lon': 24.7536, 'base_supply': 500},
            'Vilnius': {'type': 'Treatment', 'lat': 54.6872, 'lon': 25.2797, 'base_supply': 520},
            'Riga':    {'type': 'Control',   'lat': 56.9496, 'lon': 24.1052, 'base_supply': 480},
            'Tartu':   {'type': 'Control',   'lat': 58.3780, 'lon': 26.7290, 'base_supply': 490}
        }
        self.start_date = datetime.now() - timedelta(days=60) # 60 days of data

    def generate_city_data(self, uplift_percent=0.15, random_seed=42):
        """
        Generates daily 'Supply Hours' for each city.
        uplift_percent: The effect of the bonus (e.g., 0.15 for 15% increase).
        """
        np.random.seed(random_seed) # CRITICAL: Ensures the 'noise' is consistent for the demo
        
        data = []
        dates = pd.date_range(start=self.start_date, periods=60, freq='D')
        
        # Experiment starts on Day 40 (last 20 days are the test)
        experiment_start_date = dates[40]

        for city_name, props in self.cities.items():
            base = props['base_supply']
            is_treatment = props['type'] == 'Treatment'
            
            # Common Trend (Seasonality affecting ALL cities equally)
            # E.g., Weekends are busier (Sine wave simulation)
            seasonality = np.sin(np.linspace(0, 8*np.pi, 60)) * 20 

            for date in dates:
                # Random daily noise unique to each city
                # We add some volatility to make the Placebo test meaningful
                noise = np.random.normal(0, 15)
                
                # Calculate metric: Driver Online Hours
                value = base + seasonality[dates.get_loc(date)] + noise
                
                # Apply TREATMENT EFFECT only after start date and only for Treatment cities
                is_post_period = date >= experiment_start_date
                if is_treatment and is_post_period:
                    # The Bonus increases supply by uplift_percent
                    value *= (1 + uplift_percent)
                
                # Explicit Type Casting for JSON Serialization Safety
                data.append({
                    'date': date,
                    'city': str(city_name),
                    'group': str(props['type']),
                    'lat': float(props['lat']),
                    'lon': float(props['lon']),
                    'supply_hours': int(value), # Convert numpy int to python int
                    'period': 'Post-Intervention' if is_post_period else 'Pre-Intervention'
                })
                
        return pd.DataFrame(data)