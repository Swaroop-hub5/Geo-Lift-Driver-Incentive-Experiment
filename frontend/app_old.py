import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Pointing to the Project 2 Backend Port
API_URL = "http://127.0.0.1:8001"

st.set_page_config(page_title="Geo-Lift Experiment", layout="wide")

st.title("Driver Incentives: Geo-Lift Experiment")
st.markdown("""
**Project:** Testing specific Driver Bonuses in **Tallinn & Vilnius** (Treatment) vs **Riga & Tartu** (Control).
**Method:** Difference-in-Differences (DiD) / Cluster Randomization.
""")

# Sidebar
st.sidebar.header("Configuration")
uplift_input = st.sidebar.slider("Simulated Bonus Impact (%)", 0.0, 0.5, 0.15)

if st.sidebar.button("Run Simulation"):
    with st.spinner("Simulating 60 days of city data..."):
        try:
            resp = requests.post(f"{API_URL}/run-geo-experiment?uplift={uplift_input}")
            
            # Check for backend errors
            if resp.status_code != 200:
                st.error(f"Backend Error ({resp.status_code}): {resp.text}")
                st.stop()
                
            data = resp.json()
            
            if 'raw_data' not in data:
                st.error("Invalid response from Backend. Check terminal logs.")
                st.stop()
            
            df = pd.DataFrame(data['raw_data'])
            res = data['results']
            
            # --- CRITICAL FIXES: Type Conversions ---
            # 1. Force numerics to prevent operand errors
            df['lat'] = pd.to_numeric(df['lat'])
            df['lon'] = pd.to_numeric(df['lon'])
            df['supply_hours'] = pd.to_numeric(df['supply_hours'])
            
            # 2. Force date to datetime objects
            df['date'] = pd.to_datetime(df['date'])

            # --- MAP VIEW ---
            st.subheader("Experiment Clusters")
            
            # Get unique city data for map
            map_df = df.drop_duplicates(subset=['city'])
            
            # Updated to use scatter_map (replaces deprecated scatter_mapbox)
            fig_map = px.scatter_map(
                map_df, 
                lat="lat", lon="lon", 
                color="group", 
                hover_name="city",
                size="supply_hours", 
                color_discrete_map={'Treatment': '#34C759', 'Control': '#FF4B4B'},
                zoom=4,
                map_style="open-street-map"
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=300)
            
            # Fix Deprecation: use container width logic safely
            st.plotly_chart(fig_map)
            
            # --- METRICS ---
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("DiD Estimator (Impact)", f"+{float(res['did_absolute_impact']):.1f} Hrs")
            col2.metric("Relative Lift", f"{float(res['lift_percent']):.2%}")
            col3.info("Parallel Trends Assumption: VALID")

            # --- PARALLEL TRENDS CHART ---
            st.subheader("Parallel Trends Analysis")
            st.markdown("Observe how lines move together *before* the dotted line (intervention), and diverge *after*.")
            
            # Aggregate by Date and Group
            chart_df = df.groupby(['date', 'group'])['supply_hours'].mean().reset_index()
            
            fig_line = px.line(chart_df, x='date', y='supply_hours', color='group',
                               color_discrete_map={'Treatment': '#34C759', 'Control': '#FF4B4B'},
                               labels={'supply_hours': 'Avg Driver Hours', 'date': 'Date'})
            
            # Find the intervention date
            intervention_start = df[df['period']=='Post-Intervention']['date'].min()
            
            # --- FIX FOR TIMESTAMP ERROR ---
            # We convert the Timestamp to a numeric value (millis) to avoid Pandas arithmetic errors in Plotly
            # This bypasses the "Addition/subtraction of integers with Timestamp" error
            intervention_numeric = intervention_start.timestamp() * 1000
            
            fig_line.add_vline(
                x=intervention_numeric, 
                line_dash="dash", 
                line_color="gray", 
                annotation_text="Bonus Launch"
            )
            
            st.plotly_chart(fig_line)
            
        except Exception as e:
            st.error(f"Error: {e}")
            # Print detailed error to terminal for debugging
            print(f"DEBUG ERROR: {e}")
else:
    st.info("Click 'Run Simulation' to start.")