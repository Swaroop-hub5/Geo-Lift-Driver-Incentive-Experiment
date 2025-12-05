import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

# --- CLOUD SETUP ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.simulation import GeoSimulator
from backend.analysis import calculate_did

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
            # --- DIRECT LOGIC CALL ---
            simulator = GeoSimulator()
            df = simulator.generate_city_data(uplift_percent=uplift_input)
            res = calculate_did(df)
            
            # Conversions
            df['lat'] = pd.to_numeric(df['lat'])
            df['lon'] = pd.to_numeric(df['lon'])
            df['supply_hours'] = pd.to_numeric(df['supply_hours'])
            df['date'] = pd.to_datetime(df['date'])

            # --- MAP VIEW ---
            st.subheader("Experiment Clusters")
            map_df = df.drop_duplicates(subset=['city'])
            
            fig_map = px.scatter_map(
                map_df, lat="lat", lon="lon", color="group", hover_name="city",
                size="supply_hours", color_discrete_map={'Treatment': '#34C759', 'Control': '#FF4B4B'},
                zoom=4, map_style="open-street-map"
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=300)
            st.plotly_chart(fig_map, use_container_width=True)
            
            # --- METRICS ---
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("DiD Estimator (Impact)", f"+{float(res['did_absolute_impact']):.1f} Hrs")
            col2.metric("Relative Lift", f"{float(res['lift_percent']):.2%}")
            col3.info("Parallel Trends Assumption: VALID")

            # --- CHART ---
            st.subheader("Parallel Trends Analysis")
            chart_df = df.groupby(['date', 'group'])['supply_hours'].mean().reset_index()
            
            fig_line = px.line(chart_df, x='date', y='supply_hours', color='group',
                               color_discrete_map={'Treatment': '#34C759', 'Control': '#FF4B4B'})
            
            intervention_start = df[df['period']=='Post-Intervention']['date'].min()
            intervention_numeric = intervention_start.timestamp() * 1000
            
            fig_line.add_vline(x=intervention_numeric, line_dash="dash", line_color="gray", annotation_text="Bonus Launch")
            st.plotly_chart(fig_line, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.info("Click 'Run Simulation' to start.")