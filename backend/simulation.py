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
        self.start_date = datetime.now() - timedelta(days=60)

    def generate_city_data(self, uplift_percent=0.15, random_seed=42):
        """
        Generates daily 'Supply Hours' with Day-of-Week seasonality.
        """
        np.random.seed(random_seed) 
        
        data = []
        dates = pd.date_range(start=self.start_date, periods=60, freq='D')
        
        # Dynamic Cutoff: Experiment starts at the 66% mark (approx Day 40)
        cutoff_index = int(len(dates) * 0.66)
        experiment_start_date = dates[cutoff_index]

        for city_name, props in self.cities.items():
            base = props['base_supply']
            is_treatment = props['type'] == 'Treatment'
            
            for date in dates:
                # --- IMPROVEMENT: REALISTIC SEASONALITY ---
                # Logic: Ride-hailing is busiest on Fri/Sat nights.
                day_of_week = date.weekday() # 0=Monday, 6=Sunday
                
                if day_of_week in [4, 5]: # Friday & Saturday
                    dow_factor = 1.30 # 30% Supply Surge needed/available
                elif day_of_week == 6:    # Sunday
                    dow_factor = 1.10 # 10% higher than weekday
                else:                     # Mon-Thu
                    dow_factor = 1.00 # Baseline
                
                # Add random daily noise (Volatility)
                noise = np.random.normal(0, 15)
                
                # Calculate Base Value: Base * Seasonality + Noise
                value = (base * dow_factor) + noise
                # ------------------------------------------
                
                # Apply TREATMENT EFFECT (The Driver Bonus)
                is_post_period = date >= experiment_start_date
                
                if is_treatment and is_post_period:
                    # The Bonus increases supply by uplift_percent
                    value *= (1 + uplift_percent)
                
                # Explicit Type Casting
                data.append({
                    'date': date,
                    'city': str(city_name),
                    'group': str(props['type']),
                    'lat': float(props['lat']),
                    'lon': float(props['lon']),
                    'supply_hours': int(value),
                    'period': 'Post-Intervention' if is_post_period else 'Pre-Intervention'
                })
                
        return pd.DataFrame(data)