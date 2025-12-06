import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

# --- PATH SETUP (CRITICAL FIX) ---
# 1. Get the folder where this app.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Get the parent folder (The project root)
parent_dir = os.path.dirname(current_dir)
# 3. Add parent folder to Python's search path so it can find 'backend'
sys.path.insert(0, parent_dir)
# 4. Also add the current folder for safety
sys.path.insert(0, current_dir)

# --- IMPORTS ---
try:
    # Try importing assuming 'backend' is a sibling folder
    from backend.simulation import GeoSimulator
    from backend.analysis import calculate_did
except ImportError:
    try:
        # Fallback: Try importing assuming flat structure (all files in same folder)
        from backend.simulation import GeoSimulator
        from backend.analysis import calculate_did
    except ImportError as e:
        st.error(f"⚠️ Import Error: {e}")
        st.stop()

st.set_page_config(page_title="Geo-Lift Experiment", layout="wide")

# --- HEADER ---
st.title("🚗 Driver Incentives: Geo-Lift Experiment")
st.markdown("""
This tool simulates a **Difference-in-Differences (DiD)** experiment to measure the impact of driver bonuses.
It includes a **Placebo Test** to validate model robustness against supply shocks, based on industry best practices.
""")

# --- SIDEBAR ---
st.sidebar.header("Configuration")
uplift_input = st.sidebar.slider("Simulated Bonus Impact (%)", 0.0, 0.5, 0.15, help="True lift injected into the Treatment cities.")
random_seed = st.sidebar.number_input("Random Seed", value=42, help="Change this to generate different market noise patterns.")

if st.sidebar.button("Run Simulation", type="primary"):
    with st.spinner("Simulating city data & running inference..."):
        
        # 1. GENERATE DATA
        simulator = GeoSimulator()
        full_df = simulator.generate_city_data(uplift_percent=uplift_input, random_seed=random_seed)
        
        # Conversions for plotting
        full_df['date'] = pd.to_datetime(full_df['date'])

        # --- TABS STRATEGY ---
        tab1, tab2 = st.tabs(["📊 Main Experiment", "🛡️ Placebo Validation"])

        # ==========================================
        # TAB 1: THE MAIN EXPERIMENT
        # ==========================================
        with tab1:
            st.subheader("Experiment Clusters")
            
            # --- MAP VIEW (RESTORED) ---
            # Create a unique dataframe for the map (one row per city)
            map_df = full_df.drop_duplicates(subset=['city'])
            
            fig_map = px.scatter_map(
                map_df, lat="lat", lon="lon", color="group", hover_name="city",
                size="supply_hours", color_discrete_map={'Treatment': '#34C759', 'Control': '#FF4B4B'},
                zoom=4, map_style="open-street-map"
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=300)
            st.plotly_chart(fig_map, width='stretch')

            st.divider()

            st.subheader("Experiment Results: Tallinn/Vilnius (Bonus) vs. Riga/Tartu (No Bonus)")
            
            # Calculate Real DiD
            main_res = calculate_did(full_df, treatment_group='Treatment', control_group='Control')
            
            # --- UPDATE START: ADVANCED METRICS ---
            # Row 1: The Business Numbers
            m1, m2, m3 = st.columns(3)
            m1.metric("DiD Estimator (Impact)", f"+{main_res['did_absolute_impact']:.1f} Hrs", 
                      help="Net increase in supply hours attributable to the bonus.")
            m2.metric("Relative Lift", f"{main_res['lift_percent']:.2%}", 
                      delta_color="normal" if main_res['lift_percent'] > 0 else "inverse")
            
            # Row 2: The Statistical Rigor (New!)
            if 'p_value' in main_res:
                p_val = main_res['p_value']
                is_sig = main_res['is_significant']
                
                # Dynamic P-Value Display
                m3.metric("P-Value", f"{p_val:.4f}", 
                          delta="Significant (p < 0.05)" if is_sig else "Not Significant",
                          delta_color="normal" if is_sig else "inverse") # Invert logic: Red if NOT significant
                
                # Confidence Interval Display
                st.caption(f"**95% Confidence Interval:** [{main_res['conf_int_lower']:.1f}, {main_res['conf_int_upper']:.1f}]")
                
                # Explain what this means
                if is_sig:
                    st.success("✅ Result is Statistically Significant. We can trust this lift.")
                else:
                    st.warning("⚠️ Result is NOT Statistically Significant. The lift might be random noise.")
                
                # Full Regression Report (For the 'Data Scientist' persona)
                with st.expander("See OLS Regression Details"):
                    st.code(main_res.get('model_summary', 'No summary available'))
            else:
                m3.info("Parallel Trends: VISIBLE")
            # --- UPDATE END ---
            
            # Metrics Row
            # c1, c2, c3 = st.columns(3)
            # c1.metric("DiD Estimator (Impact)", f"+{main_res['did_absolute_impact']:.1f} Hrs", 
                    #  help="Net increase in supply hours attributable to the bonus.")
            # c2.metric("Relative Lift", f"{main_res['lift_percent']:.2%}", 
                    #  delta_color="normal" if main_res['lift_percent'] > 0 else "inverse")
            # c3.success("Parallel Trends: VISIBLE")

            # Chart
            chart_df = full_df.groupby(['date', 'group'])['supply_hours'].mean().reset_index()
            fig = px.line(chart_df, x='date', y='supply_hours', color='group',
                          color_discrete_map={'Treatment': '#00C853', 'Control': '#D50000'},
                          title="Supply Hours: Treatment vs Control")
            
            # Add Intervention Line
            intervention_date = full_df[full_df['period']=='Post-Intervention']['date'].min()
            fig.add_vline(x=intervention_date.timestamp() * 1000, line_dash="dash", line_color="orange", annotation_text="Bonus Launch")
            st.plotly_chart(fig, width='stretch')

        # ==========================================
        # TAB 2: THE PLACEBO TEST (THE "ANTON" FEATURE)
        # ==========================================
        with tab2:
            st.markdown("""
            ### 🛡️ Placebo Test (A/A Test)
            **Why this matters:** In small markets, "Synthetic Control" models can overfit noise. 
            To validate our lift, we run a **Placebo Test** on the Control cities (Riga vs Tartu). 
            
            **The Logic:**
            1. We take **Riga** (which got NO bonus).
            2. We pretend it was the **Treatment** city.
            3. We compare it to **Tartu** (Control).
            4. **Success Criteria:** The Lift should be **~0%**. If it shows high lift, our model is broken.
            """)
            
            # 1. Filter Data: Keep ONLY Control cities (Riga & Tartu)
            placebo_df = full_df[full_df['city'].isin(['Riga', 'Tartu'])].copy()
            
            # 2. Fake the Groups: Riga becomes "Fake Treatment", Tartu remains "Control"
            placebo_df['group'] = placebo_df['city'].apply(lambda x: 'Fake Treatment (Riga)' if x == 'Riga' else 'Control (Tartu)')
            
            # 3. Run Analysis
            placebo_res = calculate_did(placebo_df, treatment_group='Fake Treatment (Riga)', control_group='Control (Tartu)')
            
            # Metrics
            pc1, pc2, pc3 = st.columns(3)
            pc1.metric("Placebo Impact", f"{placebo_res['did_absolute_impact']:.1f} Hrs", 
                       help="Ideally this should be close to 0.")
            
            
            # --- UPDATE START: PLACEBO LOGIC ---
            # 1. Check Magnitude (Should be small)
            is_magnitude_small = abs(placebo_res['lift_percent']) < 0.05
            
            # 2. Check Significance (Should be NOT Significant, i.e., P-Value > 0.05)
            # If P-Value is LOW (e.g. 0.01), it means we found a significant difference between two identical cities. That's bad!
            is_not_significant = True 
            if 'p_value' in placebo_res:
                is_not_significant = placebo_res['p_value'] > 0.05

            # Combined Pass/Fail Logic
            placebo_passed = is_magnitude_small and is_not_significant
            
            pc2.metric("Placebo Lift %", f"{placebo_res['lift_percent']:.2%}", 
                       delta="Pass" if placebo_passed else "Fail",
                       delta_color="normal" if placebo_passed else "inverse")
            
            if placebo_passed:
                pc3.success("✅ Robustness Check PASSED (Noise is random)")
            else:
                pc3.error("⚠️ Robustness Check FAILED (Found significant fake lift)")
                if not is_not_significant:
                    st.caption("Failure Reason: The model found a 'Statistically Significant' difference between two control cities.")
            # --- UPDATE END ---
            
            # Dynamic Color Logic: Green if low noise, Red if high noise (False Positive)
            # is_noise_low = abs(placebo_res['lift_percent']) < 0.05
            # pc2.metric("Placebo Lift %", f"{placebo_res['lift_percent']:.2%}", 
              #         delta="Pass" if is_noise_low else "Fail - High Noise",
              #         delta_color="normal" if is_noise_low else "inverse")
            
            # if is_noise_low:
              #  pc3.success("✅ Robustness Check PASSED")
            # else:
              #  pc3.error("⚠️ Robustness Check FAILED (High Volatility)")

            # Chart
            p_chart_df = placebo_df.groupby(['date', 'group'])['supply_hours'].mean().reset_index()
            p_fig = px.line(p_chart_df, x='date', y='supply_hours', color='group',
                          color_discrete_map={'Fake Treatment (Riga)': '#FFAB00', 'Control (Tartu)': '#607D8B'},
                          title="Placebo Validation: Riga (Fake Treatment) vs Tartu")
            p_fig.add_vline(x=intervention_date.timestamp() * 1000, line_dash="dash", annotation_text="Fake Intervention")
            st.plotly_chart(p_fig, width='stretch')

else:
    st.info("👈 Click 'Run Simulation' in the sidebar to start the experiment.")